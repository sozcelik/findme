import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.campaign import Campaign
from app.db.models.project import Project

router = APIRouter()

ORG_ID = "org-dev-1"


@router.get("")
async def list_campaigns(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Campaign).where(Campaign.org_id == ORG_ID)
    if project_id:
        query = query.where(Campaign.project_id == project_id)
    query = query.order_by(Campaign.created_at.desc())
    result = await db.execute(query)
    return [_serialize(c) for c in result.scalars().all()]


class CreateCampaignRequest(BaseModel):
    projectId: str
    name: str
    scheduleCron: str | None = None
    targetKeywords: list[str] = []
    contentTypes: list[str] = []
    publishToCms: bool = False
    distributeSocial: bool = False


@router.post("")
async def create_campaign(body: CreateCampaignRequest, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, body.projectId)
    if not project or project.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Project not found")

    campaign = Campaign(
        id=str(uuid.uuid4()),
        project_id=body.projectId,
        org_id=ORG_ID,
        name=body.name,
        status="draft",
        schedule_cron=body.scheduleCron,
        target_keywords=body.targetKeywords or None,
        content_types=body.contentTypes or None,
        publish_to_cms=body.publishToCms,
        distribute_social=body.distributeSocial,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    # Register with celery-redbeat if a cron schedule is given
    if body.scheduleCron:
        try:
            from app.tasks.campaign_tasks import register_campaign_schedule
            register_campaign_schedule(campaign.id, body.scheduleCron, ORG_ID)
            campaign.status = "running"
            await db.commit()
        except Exception:
            pass

    return _serialize(campaign)


class UpdateCampaignRequest(BaseModel):
    name: str | None = None
    status: str | None = None
    scheduleCron: str | None = None
    publishToCms: bool | None = None
    distributeSocial: bool | None = None


@router.patch("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    body: UpdateCampaignRequest,
    db: AsyncSession = Depends(get_db),
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign or campaign.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Not found")

    if body.name is not None:
        campaign.name = body.name
    if body.publishToCms is not None:
        campaign.publish_to_cms = body.publishToCms
    if body.distributeSocial is not None:
        campaign.distribute_social = body.distributeSocial

    if body.scheduleCron is not None and body.scheduleCron != campaign.schedule_cron:
        campaign.schedule_cron = body.scheduleCron
        try:
            from app.tasks.campaign_tasks import register_campaign_schedule
            register_campaign_schedule(campaign.id, body.scheduleCron, ORG_ID)
        except Exception:
            pass

    if body.status is not None:
        if body.status == "paused" and campaign.status != "paused":
            try:
                from app.tasks.campaign_tasks import unregister_campaign_schedule
                unregister_campaign_schedule(campaign.id)
            except Exception:
                pass
        campaign.status = body.status

    await db.commit()
    await db.refresh(campaign)
    return _serialize(campaign)


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign or campaign.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        from app.tasks.campaign_tasks import unregister_campaign_schedule
        unregister_campaign_schedule(campaign_id)
    except Exception:
        pass

    await db.delete(campaign)
    await db.commit()


@router.post("/{campaign_id}/run")
async def run_campaign_now(campaign_id: str, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign or campaign.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Not found")

    from app.tasks.campaign_tasks import run_campaign
    task = run_campaign.delay(campaign_id)
    return {"taskId": task.id, "status": "queued"}


def _serialize(c: Campaign) -> dict:
    return {
        "id": c.id,
        "projectId": c.project_id,
        "name": c.name,
        "status": c.status,
        "scheduleCron": c.schedule_cron,
        "targetKeywords": c.target_keywords or [],
        "contentTypes": c.content_types or [],
        "publishToCms": c.publish_to_cms,
        "distributeSocial": c.distribute_social,
        "lastRunAt": c.last_run_at.isoformat() if c.last_run_at else None,
        "nextRunAt": c.next_run_at.isoformat() if c.next_run_at else None,
        "createdAt": c.created_at.isoformat(),
    }
