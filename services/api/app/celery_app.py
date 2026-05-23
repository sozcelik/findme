from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "findme",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.agent_tasks",
        "app.tasks.publish_tasks",
        "app.tasks.analytics_tasks",
        "app.tasks.campaign_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_scheduler="redbeat.RedBeatScheduler",
    beat_max_loop_interval=5,
    task_routes={
        "app.tasks.agent_tasks.*": {"queue": "default"},
        "app.tasks.publish_tasks.*": {"queue": "publish"},
        "app.tasks.analytics_tasks.*": {"queue": "analytics"},
        "app.tasks.campaign_tasks.*": {"queue": "default"},
    },
    worker_max_tasks_per_child=50,
    beat_schedule={
        "daily-visibility-scores": {
            "task": "app.tasks.analytics_tasks.daily_visibility_scores",
            "schedule": crontab(hour=3, minute=0),  # 03:00 UTC daily
        },
        "daily-keyword-rankings": {
            "task": "app.tasks.analytics_tasks.daily_keyword_rankings",
            "schedule": crontab(hour=4, minute=0),  # 04:00 UTC daily
        },
        "hourly-token-refresh": {
            "task": "app.tasks.analytics_tasks.hourly_token_refresh",
            "schedule": crontab(minute=30),  # every hour at :30
        },
    },
)
