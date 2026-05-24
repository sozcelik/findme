import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.project import Project
from app.db.models.agent_job import AgentJob

router = APIRouter()

ORG_ID = "org-dev-1"  # replaced with JWT-extracted org_id once auth is wired up


class CreateProjectRequest(BaseModel):
    name: str
    websiteUrl: str
    businessDescription: str | None = None
    targetAudience: str | None = None
    industry: str | None = None
    language: str = "en"


@router.get("")
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).where(Project.org_id == ORG_ID).order_by(Project.created_at.desc())
    )
    return [_serialize(p) for p in result.scalars().all()]


@router.post("", status_code=201)
async def create_project(body: CreateProjectRequest, db: AsyncSession = Depends(get_db)):
    project = Project(
        id=str(uuid.uuid4()),
        org_id=ORG_ID,
        name=body.name,
        website_url=body.websiteUrl,
        business_description=body.businessDescription,
        target_audience=body.targetAudience,
        industry=body.industry,
        language=body.language,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return _serialize(project)


@router.get("/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project or project.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Project not found")
    return _serialize(project)


@router.get("/{project_id}/llms.txt", response_class=PlainTextResponse)
async def get_llms_txt(project_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import Session
    from app.services.llms_txt import generate_llms_txt
    project = await db.get(Project, project_id)
    if not project or project.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Project not found")
    # llms_txt generator uses sync session — run inline with sync wrapper
    from sqlalchemy import create_engine
    from app.config import settings
    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True)
    with Session(engine) as sync_db:
        sync_project = sync_db.get(Project, project_id)
        content = generate_llms_txt(sync_project, sync_db)
    engine.dispose()
    return content


@router.get("/{project_id}/robots-snippet", response_class=PlainTextResponse)
async def get_robots_snippet(project_id: str, db: AsyncSession = Depends(get_db)):
    from app.services.llms_txt import generate_robots_txt_snippet
    project = await db.get(Project, project_id)
    if not project or project.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Project not found")
    return generate_robots_txt_snippet()


@router.get("/{project_id}/jobs")
async def list_project_jobs(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentJob)
        .where(AgentJob.project_id == project_id, AgentJob.org_id == ORG_ID)
        .order_by(AgentJob.created_at.desc())
    )
    return [_serialize_job(j) for j in result.scalars().all()]


def _serialize(p: Project) -> dict:
    return {
        "id": p.id,
        "orgId": p.org_id,
        "name": p.name,
        "websiteUrl": p.website_url,
        "businessDescription": p.business_description,
        "targetAudience": p.target_audience,
        "industry": p.industry,
        "language": p.language,
        "visibilityScore": p.visibility_score,
        "visibilityUpdatedAt": p.visibility_updated_at.isoformat() if p.visibility_updated_at else None,
        "status": p.status,
        "createdAt": p.created_at.isoformat(),
    }


def _serialize_job(j: AgentJob) -> dict:
    return {
        "id": j.id,
        "type": j.type,
        "status": j.status,
        "progress": j.progress,
        "progressSteps": j.progress_steps or [],
        "outputData": j.output_data,
        "errorMessage": j.error_message,
        "creditsUsed": j.credits_used,
        "startedAt": j.started_at.isoformat() if j.started_at else None,
        "completedAt": j.completed_at.isoformat() if j.completed_at else None,
    }
