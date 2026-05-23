from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models.org import Organization
from app.db.session import get_db
from app.services import stripe_service

router = APIRouter()

ORG_ID = "org-dev-1"
FRONTEND_URL = "http://localhost:3000"


@router.get("/subscription")
async def get_subscription(db: AsyncSession = Depends(get_db)):
    org = await db.get(Organization, ORG_ID)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {
        "plan": org.plan,
        "monthlyCreditsUsed": org.credits_used_this_month,
        "monthlyCreditsLimit": org.monthly_credit_limit,
        "stripeCustomerId": org.stripe_customer_id,
        "stripeSubscriptionId": org.stripe_subscription_id,
    }


class CreateCheckoutRequest(BaseModel):
    priceId: str
    userEmail: str


@router.post("/create-checkout")
async def create_checkout(body: CreateCheckoutRequest, db: AsyncSession = Depends(get_db)):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured")

    valid_price_ids = {settings.stripe_growth_price_id, settings.stripe_pro_price_id}
    valid_price_ids.discard("")
    if body.priceId not in valid_price_ids:
        raise HTTPException(status_code=400, detail="Invalid price ID")

    url = stripe_service.create_checkout_session(
        org_id=ORG_ID,
        user_email=body.userEmail,
        price_id=body.priceId,
        success_url=f"{FRONTEND_URL}/settings/billing?session=success",
        cancel_url=f"{FRONTEND_URL}/settings/billing",
    )
    return {"url": url}


class PortalRequest(BaseModel):
    customerId: str


@router.post("/portal")
async def billing_portal(body: PortalRequest):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured")

    url = stripe_service.create_billing_portal(
        customer_id=body.customerId,
        return_url=f"{FRONTEND_URL}/settings/billing",
    )
    return {"url": url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe_service.handle_webhook(payload, sig)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not event:
        return {"received": True}

    org_id = event.get("org_id")
    if not org_id:
        return {"received": True}

    org = await db.get(Organization, org_id)
    if not org:
        return {"received": True}

    if event["event"] == "checkout_completed":
        org.stripe_customer_id = event.get("customer_id")
        org.stripe_subscription_id = event.get("subscription_id")

    elif event["event"] == "subscription_updated":
        org.stripe_customer_id = event.get("customer_id")
        org.stripe_subscription_id = event.get("subscription_id")
        org.plan = event.get("plan", "free")
        org.monthly_credit_limit = event.get("monthly_credit_limit", 5)

    elif event["event"] == "subscription_deleted":
        org.plan = "free"
        org.monthly_credit_limit = stripe_service.PLAN_CREDITS["free"]
        org.stripe_subscription_id = None

    await db.commit()
    return {"received": True}
