import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.agent_job import AgentJob
from app.db.models.citation_result import CitationResult

router = APIRouter()
ORG_ID = "org-dev-1"


@router.post("/projects/{project_id}/run-citation-check")
async def run_citation_check(project_id: str, db: AsyncSession = Depends(get_db)):
    from app.tasks.citation_tasks import run_citation_check as task

    job = AgentJob(
        id=str(uuid.uuid4()),
        org_id=ORG_ID,
        project_id=project_id,
        type="citation_check",
        status="queued",
        input_data={},
        progress=0,
        progress_steps=[],
    )
    db.add(job)
    await db.commit()

    task.delay(job.id, project_id, ORG_ID)
    return {"jobId": job.id}


@router.get("/projects/{project_id}/citation-history")
async def get_citation_history(project_id: str, db: AsyncSession = Depends(get_db)):
    # Return the last 10 citation_check jobs with their output_data
    result = await db.execute(
        select(AgentJob)
        .where(
            AgentJob.project_id == project_id,
            AgentJob.org_id == ORG_ID,
            AgentJob.type == "citation_check",
            AgentJob.status == "completed",
        )
        .order_by(AgentJob.completed_at.desc())
        .limit(10)
    )
    jobs = result.scalars().all()

    return [
        {
            "jobId": j.id,
            "checkedAt": j.completed_at.isoformat() if j.completed_at else None,
            "summary": (j.output_data or {}).get("summary", {}),
            "queriesRun": (j.output_data or {}).get("queries_run", 0),
            "modelsChecked": (j.output_data or {}).get("models_checked", []),
        }
        for j in jobs
    ]


@router.get("/projects/{project_id}/citation-results")
async def get_citation_results(
    project_id: str,
    job_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(CitationResult).where(
        CitationResult.project_id == project_id,
        CitationResult.org_id == ORG_ID,
    )
    if job_id:
        query = query.where(CitationResult.job_id == job_id)
    query = query.order_by(CitationResult.checked_at.desc()).limit(100)
    result = await db.execute(query)
    rows = result.scalars().all()

    return [
        {
            "id": r.id,
            "query": r.query,
            "model": r.model,
            "mentioned": r.mentioned,
            "position": r.mention_position,
            "sentiment": r.sentiment,
            "excerpt": r.excerpt,
            "checkedAt": r.checked_at.isoformat(),
        }
        for r in rows
    ]
