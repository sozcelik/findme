import stripe
from app.config import settings

stripe.api_key = settings.stripe_secret_key

PLAN_CREDITS: dict[str, int] = {
    "growth": 50,
    "pro": 200,
    "free": 5,
}

PRICE_TO_PLAN: dict[str, str] = {}


def _price_to_plan() -> dict[str, str]:
    if not PRICE_TO_PLAN:
        if settings.stripe_growth_price_id:
            PRICE_TO_PLAN[settings.stripe_growth_price_id] = "growth"
        if settings.stripe_pro_price_id:
            PRICE_TO_PLAN[settings.stripe_pro_price_id] = "pro"
    return PRICE_TO_PLAN


def create_checkout_session(
    org_id: str,
    user_email: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    session = stripe.checkout.Session.create(
        customer_email=user_email,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"org_id": org_id},
        subscription_data={"metadata": {"org_id": org_id}},
    )
    return session.url


def create_billing_portal(customer_id: str, return_url: str) -> str:
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


def handle_webhook(payload: bytes, sig_header: str) -> dict | None:
    """
    Verify Stripe signature, return parsed event or None if unhandled.
    Raises ValueError on bad signature.
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError as e:
        raise ValueError(f"Invalid Stripe signature: {e}") from e

    event_type = event["type"]

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        return {
            "event": "checkout_completed",
            "org_id": session.get("metadata", {}).get("org_id"),
            "customer_id": session.get("customer"),
            "subscription_id": session.get("subscription"),
        }

    if event_type in ("customer.subscription.updated", "customer.subscription.created"):
        sub = event["data"]["object"]
        price_id = sub["items"]["data"][0]["price"]["id"] if sub["items"]["data"] else ""
        plan = _price_to_plan().get(price_id, "free")
        return {
            "event": "subscription_updated",
            "org_id": sub.get("metadata", {}).get("org_id"),
            "customer_id": sub.get("customer"),
            "subscription_id": sub["id"],
            "status": sub["status"],
            "plan": plan,
            "monthly_credit_limit": PLAN_CREDITS.get(plan, 5),
        }

    if event_type == "customer.subscription.deleted":
        sub = event["data"]["object"]
        return {
            "event": "subscription_deleted",
            "org_id": sub.get("metadata", {}).get("org_id"),
            "subscription_id": sub["id"],
        }

    return None
