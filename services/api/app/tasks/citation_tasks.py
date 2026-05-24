from datetime import datetime, timezone
from app.celery_app import celery_app


@celery_app.task(
    name="app.tasks.citation_tasks.run_citation_check",
    bind=True,
    max_retries=1,
    default_retry_delay=30,
)
def run_citation_check(self, job_id: str, project_id: str, org_id: str):
    import redis as sync_redis
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from app.config import settings
    from app.db.models.agent_job import AgentJob
    from app.db.models.project import Project
    from app.db.models.keyword import Keyword
    from app.services.citation_simulator import run_simulation

    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True)
    r = sync_redis.from_url(settings.redis_url)

    def emit(message: str):
        import json
        r.publish(f"job:progress:{job_id}", json.dumps({
            "name": "citation_check",
            "status": "running",
            "message": message,
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "completedAt": None,
        }))

    try:
        with Session(engine) as db:
            job = db.get(AgentJob, job_id)
            if not job:
                return
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            db.commit()

            project = db.get(Project, project_id)
            if not project:
                job.status = "failed"
                job.error_message = "Project not found"
                db.commit()
                return

            keywords = db.execute(
                select(Keyword)
                .where(Keyword.project_id == project_id, Keyword.org_id == org_id)
                .order_by(Keyword.search_volume.desc().nullslast())
                .limit(3)
            ).scalars().all()

            emit(f"Running queries against AI models ({len(keywords)} keywords)...")

            output = run_simulation(
                project=project,
                keywords=keywords,
                job_id=job_id,
                db=db,
            )

            job.status = "completed"
            job.progress = 100
            job.completed_at = datetime.now(timezone.utc)
            job.output_data = output
            db.commit()

        import json
        r.publish(f"job:progress:{job_id}", json.dumps({
            "name": "citation_check",
            "status": "completed",
            "message": f"Checked {output['queries_run']} queries across {len(output['models_checked'])} models",
            "startedAt": None,
            "completedAt": datetime.now(timezone.utc).isoformat(),
        }))

    except Exception as exc:
        with Session(engine) as db:
            job = db.get(AgentJob, job_id)
            if job:
                job.status = "failed"
                job.error_message = str(exc)[:1000]
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        raise self.retry(exc=exc, countdown=30)
    finally:
        r.close()
        engine.dispose()
