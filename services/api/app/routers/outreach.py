from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.outreach_opportunity import OutreachOpportunity
from app.db.models.project import Project

router = APIRouter()

ORG_ID = "org-dev-1"


@router.get("")
async def list_opportunities(
    project_id: str,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Project not found")

    query = select(OutreachOpportunity).where(
        OutreachOpportunity.project_id == project_id
    )
    if status:
        query = query.where(OutreachOpportunity.status == status)
    query = query.order_by(
        OutreachOpportunity.domain_authority.desc().nullslast(),
        OutreachOpportunity.created_at.desc(),
    )

    result = await db.execute(query)
    return [_serialize(o) for o in result.scalars().all()]


class UpdateOpportunityRequest(BaseModel):
    status: str | None = None
    contactEmail: str | None = None
    outreachDraft: str | None = None


@router.patch("/{opportunity_id}")
async def update_opportunity(
    opportunity_id: str,
    body: UpdateOpportunityRequest,
    db: AsyncSession = Depends(get_db),
):
    opp = await db.get(OutreachOpportunity, opportunity_id)
    if not opp or opp.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Not found")

    if body.status is not None:
        opp.status = body.status
        if body.status == "sent":
            from datetime import datetime, timezone
            opp.sent_at = datetime.now(timezone.utc)
    if body.contactEmail is not None:
        opp.contact_email = body.contactEmail
    if body.outreachDraft is not None:
        opp.outreach_draft = body.outreachDraft

    await db.commit()
    await db.refresh(opp)
    return _serialize(opp)


@router.post("/run")
async def run_outreach_agent(project_id: str, db: AsyncSession = Depends(get_db)):
    """Trigger OutreachAgent for a project as a background Celery task."""
    project = await db.get(Project, project_id)
    if not project or project.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Project not found")

    import uuid
    from datetime import datetime, timezone
    from app.db.models.agent_job import AgentJob

    job = AgentJob(
        id=str(uuid.uuid4()),
        org_id=ORG_ID,
        project_id=project_id,
        type="outreach",
        status="queued",
        triggered_by="manual",
    )
    db.add(job)
    await db.commit()

    from app.tasks.agent_tasks import run_outreach_pipeline
    run_outreach_pipeline.delay(job.id, project_id, ORG_ID)

    return {"jobId": job.id, "status": "queued"}


def _serialize(o: OutreachOpportunity) -> dict:
    return {
        "id": o.id,
        "type": o.type,
        "targetDomain": o.target_domain,
        "contactEmail": o.contact_email,
        "domainAuthority": o.domain_authority,
        "relevanceScore": o.relevance_score,
        "status": o.status,
        "outreachDraft": o.outreach_draft,
        "sentAt": o.sent_at.isoformat() if o.sent_at else None,
        "repliedAt": o.replied_at.isoformat() if o.replied_at else None,
        "createdAt": o.created_at.isoformat(),
    }
