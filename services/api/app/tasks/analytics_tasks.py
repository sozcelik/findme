"""
Cron tasks:
- daily_visibility_scores: runs at 03:00 UTC for all Pro+ projects
- daily_keyword_rankings: fetch current SERP positions for all keywords
- hourly_token_refresh: refresh OAuth tokens expiring within 24h
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from app.celery_app import celery_app


@celery_app.task(name="app.tasks.analytics_tasks.daily_visibility_scores")
def daily_visibility_scores():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.config import settings
    from app.db.models.project import Project
    from app.db.models.org import Organization
    from app.services.visibility_score import calculate_full_score

    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True)

    with Session(engine) as db:
        # Pro+ orgs only for daily refresh
        pro_orgs = db.query(Organization).filter(
            Organization.plan.in_(["pro", "enterprise"])
        ).all()
        pro_org_ids = {o.id for o in pro_orgs}

        projects = db.query(Project).filter(
            Project.status == "active",
            Project.org_id.in_(pro_org_ids),
        ).all()

        updated = 0
        for project in projects:
            try:
                score, _ = calculate_full_score(project, project.org_id, db)
                project.visibility_score = score
                project.visibility_updated_at = datetime.now(timezone.utc)
                updated += 1
            except Exception:
                pass

        db.commit()

    engine.dispose()
    return {"projects_updated": updated}


@celery_app.task(name="app.tasks.analytics_tasks.daily_keyword_rankings")
def daily_keyword_rankings():
    import uuid
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.config import settings
    from app.db.models.keyword import Keyword
    from app.db.models.keyword_ranking import KeywordRanking
    from app.services.dataforseo import fetch_serp

    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True)
    today = date.today()

    with Session(engine) as db:
        # Only keywords with SERP data, checked more than 23h ago
        cutoff = datetime.now(timezone.utc) - timedelta(hours=23)
        keywords = db.query(Keyword).filter(
            Keyword.last_analyzed_at <= cutoff,
        ).limit(100).all()

        updated = 0
        for kw in keywords:
            try:
                serp = asyncio.run(fetch_serp(kw.keyword))
                # Find our domain's position if project.website_url is set
                position = None
                url = None
                # (In a full implementation, compare against project.website_url)

                # Store whatever we got
                existing = db.query(KeywordRanking).filter(
                    KeywordRanking.keyword_id == kw.id,
                    KeywordRanking.checked_at == today,
                ).first()

                if existing:
                    existing.position = position
                    existing.search_volume = kw.search_volume
                else:
                    db.add(KeywordRanking(
                        id=str(uuid.uuid4()),
                        keyword_id=kw.id,
                        project_id=kw.project_id,
                        checked_at=today,
                        position=position,
                        url_ranking=url,
                        search_volume=kw.search_volume,
                    ))
                updated += 1
            except Exception:
                pass

        db.commit()

    engine.dispose()
    return {"keywords_checked": updated}


@celery_app.task(name="app.tasks.analytics_tasks.hourly_token_refresh")
def hourly_token_refresh():
    """Refresh OAuth access tokens expiring within 24 hours."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.config import settings
    from app.db.models.social_connection import SocialConnection
    from app.services.vault import encrypt, decrypt

    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True)
    threshold = datetime.now(timezone.utc) + timedelta(hours=24)

    with Session(engine) as db:
        expiring = db.query(SocialConnection).filter(
            SocialConnection.refresh_token_encrypted.isnot(None),
            SocialConnection.token_expires_at <= threshold,
            SocialConnection.status == "active",
        ).all()

        refreshed = 0
        for conn in expiring:
            try:
                refresh_token = decrypt(conn.refresh_token_encrypted)
                if conn.platform == "twitter":
                    _refresh_twitter_token(conn, refresh_token, encrypt, db)
                    refreshed += 1
                # LinkedIn tokens last 60 days — no refresh needed unless using offline_access
            except Exception:
                pass

        db.commit()

    engine.dispose()
    return {"tokens_refreshed": refreshed}


def _refresh_twitter_token(conn, refresh_token: str, encrypt_fn, db):
    import httpx
    from app.config import settings

    resp = httpx.post(
        "https://api.twitter.com/2/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": settings.twitter_client_id,
        },
        auth=(settings.twitter_client_id, settings.twitter_client_secret),
        timeout=15.0,
    )
    resp.raise_for_status()
    tokens = resp.json()

    conn.access_token_encrypted = encrypt_fn(tokens["access_token"])
    if tokens.get("refresh_token"):
        conn.refresh_token_encrypted = encrypt_fn(tokens["refresh_token"])
    if tokens.get("expires_in"):
        conn.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"])
