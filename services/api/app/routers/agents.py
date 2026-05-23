import asyncio
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from app.db.session import get_db
from app.db.models.agent_job import AgentJob
from app.config import settings

router = APIRouter()

ORG_ID = "org-dev-1"


class RunPipelineRequest(BaseModel):
    keywordIds: list[str] | None = None
    contentTypes: list[str] | None = None


@router.post("/projects/{project_id}/run-pipeline")
async def run_pipeline(
    project_id: str,
    body: RunPipelineRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.tasks.agent_tasks import run_full_pipeline

    job = AgentJob(
        id=str(uuid.uuid4()),
        org_id=ORG_ID,
        project_id=project_id,
        type="full_pipeline",
        status="queued",
        input_data=body.model_dump(),
        progress=0,
        progress_steps=[],
    )
    db.add(job)
    await db.commit()

    run_full_pipeline.delay(job.id, project_id, ORG_ID)

    return {"jobId": job.id}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(AgentJob, job_id)
    if not job or job.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "progress": job.progress,
        "progressSteps": job.progress_steps or [],
        "outputData": job.output_data,
        "errorMessage": job.error_message,
        "creditsUsed": job.credits_used,
        "startedAt": job.started_at.isoformat() if job.started_at else None,
        "completedAt": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    async def event_generator():
        redis = aioredis.from_url(settings.redis_url)
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"job:progress:{job_id}")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield f"data: {message['data'].decode()}\n\n"
                    data = json.loads(message["data"])
                    if data.get("status") in ("completed", "failed"):
                        yield "event: done\ndata: {}\n\n"
                        break
        finally:
            await pubsub.unsubscribe(f"job:progress:{job_id}")
            await redis.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
