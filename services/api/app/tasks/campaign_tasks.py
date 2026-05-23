"""
Campaign orchestrator: runs the full pipeline for a scheduled campaign.
Scheduled via celery-redbeat using the campaign's schedule_cron.
"""

from datetime import datetime, timezone
from app.celery_app import celery_app


@celery_app.task(
    name="app.tasks.campaign_tasks.run_campaign",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def run_campaign(self, campaign_id: str):
    import uuid
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.config import settings
    from app.db.models.campaign import Campaign
    from app.db.models.agent_job import AgentJob

    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True)

    try:
        with Session(engine) as db:
            campaign = db.get(Campaign, campaign_id)
            if not campaign or campaign.status == "paused":
                return {"skipped": True}

            campaign.status = "running"
            campaign.last_run_at = datetime.now(timezone.utc)
            db.commit()

            # Enqueue the full pipeline for this project
            from app.tasks.agent_tasks import run_full_pipeline

            job = AgentJob(
                id=str(uuid.uuid4()),
                org_id=campaign.org_id,
                project_id=campaign.project_id,
                type="full_pipeline",
                status="queued",
                triggered_by="campaign",
                input_data={
                    "campaign_id": campaign_id,
                    "target_keywords": campaign.target_keywords or [],
                    "content_types": campaign.content_types or [],
                    "publish_to_cms": campaign.publish_to_cms,
                    "distribute_social": campaign.distribute_social,
                },
            )
            db.add(job)
            db.commit()

            run_full_pipeline.delay(job.id, campaign.project_id, campaign.org_id)

            # Update next_run_at
            if campaign.schedule_cron:
                campaign.next_run_at = _next_cron_run(campaign.schedule_cron)

            campaign.status = "completed"
            db.commit()

            return {"job_id": job.id, "campaign_id": campaign_id}

    except Exception as exc:
        with Session(engine) as db:
            campaign = db.get(Campaign, campaign_id)
            if campaign:
                campaign.status = "paused"
                db.commit()
        raise self.retry(exc=exc)
    finally:
        engine.dispose()


def _next_cron_run(cron_expr: str) -> datetime | None:
    """Parse a simple 5-field cron expression and return the next UTC run time."""
    try:
        from croniter import croniter
        ct = croniter(cron_expr, datetime.now(timezone.utc))
        return ct.get_next(datetime)
    except Exception:
        return None


def register_campaign_schedule(campaign_id: str, cron_expr: str, org_id: str) -> None:
    """Register or update a campaign's celery-redbeat schedule."""
    from redbeat import RedBeatSchedulerEntry
    from celery.schedules import crontab
    from app.celery_app import celery_app

    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expr}")

    minute, hour, day, month, day_of_week = parts
    schedule = crontab(
        minute=minute,
        hour=hour,
        day_of_month=day,
        month_of_year=month,
        day_of_week=day_of_week,
    )

    entry = RedBeatSchedulerEntry(
        f"campaign:{campaign_id}",
        "app.tasks.campaign_tasks.run_campaign",
        schedule,
        kwargs={"campaign_id": campaign_id},
        app=celery_app,
    )
    entry.save()


def unregister_campaign_schedule(campaign_id: str) -> None:
    """Remove a campaign's redbeat schedule entry."""
    try:
        from redbeat import RedBeatSchedulerEntry
        from app.celery_app import celery_app
        entry = RedBeatSchedulerEntry.from_key(
            f"redbeat:campaign:{campaign_id}", app=celery_app
        )
        entry.delete()
    except Exception:
        pass
