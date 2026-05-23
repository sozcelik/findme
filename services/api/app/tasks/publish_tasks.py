import json
import uuid
from datetime import datetime, timezone
from app.celery_app import celery_app


@celery_app.task(
    name="app.tasks.publish_tasks.publish_to_cms",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def publish_to_cms(self, content_id: str, cms_connection_id: str, org_id: str):
    import asyncio
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.config import settings
    from app.db.models.content_item import ContentItem
    from app.db.models.cms_connection import CmsConnection
    from app.db.models.publish_record import PublishRecord
    from app.integrations.cms.base import CMSAdapter, CMSPublishPayload
    from app.services.vault import decrypt

    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True)

    try:
        with Session(engine) as db:
            content = db.get(ContentItem, content_id)
            if not content or content.org_id != org_id:
                raise ValueError(f"Content {content_id} not found")

            conn = db.get(CmsConnection, cms_connection_id)
            if not conn or conn.org_id != org_id:
                raise ValueError(f"CMS connection {cms_connection_id} not found")

            # Decrypt config values
            raw_config: dict = conn.config_encrypted or {}
            config = {k: decrypt(v) if isinstance(v, str) else v for k, v in raw_config.items()}

            adapter = CMSAdapter.from_config(conn.type, config)
            payload = CMSPublishPayload(
                title=content.title or "",
                body_html="",
                body_markdown=content.body_markdown or "",
                slug=content.slug,
                meta_title=content.meta_title,
                meta_description=content.meta_description,
            )

            # Check for existing publish record to decide create vs update
            from sqlalchemy import select
            existing = db.execute(
                select(PublishRecord).where(
                    PublishRecord.content_id == content_id,
                    PublishRecord.cms_connection_id == cms_connection_id,
                    PublishRecord.status == "published",
                )
            ).scalar_one_or_none()

            if existing and existing.external_id:
                result = asyncio.run(adapter.update(existing.external_id, payload))
                existing.status = "updated"
                existing.external_url = result.external_url
                existing.published_at = datetime.now(timezone.utc)
                record = existing
            else:
                result = asyncio.run(adapter.publish(payload))
                record = PublishRecord(
                    id=str(uuid.uuid4()),
                    content_id=content_id,
                    cms_connection_id=cms_connection_id,
                    external_id=result.external_id,
                    external_url=result.external_url,
                    status="published",
                    published_at=datetime.now(timezone.utc),
                )
                db.add(record)

            content.status = "published"
            content.published_at = datetime.now(timezone.utc)
            db.commit()

            return {
                "external_id": result.external_id,
                "external_url": result.external_url,
                "status": "published",
            }

    except Exception as exc:
        with Session(engine) as db:
            record = PublishRecord(
                id=str(uuid.uuid4()),
                content_id=content_id,
                cms_connection_id=cms_connection_id,
                status="failed",
                error_message=str(exc)[:1000],
            )
            db.add(record)
            db.commit()
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 15)
    finally:
        engine.dispose()


@celery_app.task(
    name="app.tasks.publish_tasks.post_to_social",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def post_to_social(self, social_post_id: str, social_connection_id: str, org_id: str):
    import asyncio
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.config import settings
    from app.db.models.social_post import SocialPost
    from app.db.models.social_connection import SocialConnection
    from app.integrations.social.base import SocialAdapter, SocialPostPayload, SocialConnectionData
    from app.services.vault import decrypt

    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True)

    try:
        with Session(engine) as db:
            post = db.get(SocialPost, social_post_id)
            if not post or post.org_id != org_id:
                raise ValueError(f"SocialPost {social_post_id} not found")

            conn = db.get(SocialConnection, social_connection_id)
            if not conn or conn.org_id != org_id:
                raise ValueError(f"Social connection {social_connection_id} not found")

            access_token = decrypt(conn.access_token_encrypted) if conn.access_token_encrypted else ""
            refresh_token = decrypt(conn.refresh_token_encrypted) if conn.refresh_token_encrypted else None

            conn_data = SocialConnectionData(
                platform=conn.platform,
                access_token=access_token,
                refresh_token=refresh_token,
                account_id=conn.account_id or "",
                account_name=conn.account_name or "",
                scopes=(conn.scopes or "").split(),
            )
            adapter = SocialAdapter.from_platform(conn.platform, conn_data)

            hashtags = (post.hashtags or "").split() if post.hashtags else []
            payload = SocialPostPayload(
                body=post.body or "",
                hashtags=hashtags,
                reddit_title=post.reddit_title,
            )

            result = asyncio.run(adapter.post(payload))

            post.status = "posted"
            post.posted_at = datetime.now(timezone.utc)
            post.external_post_id = result.external_post_id
            db.commit()

            return {"external_post_id": result.external_post_id, "url": result.url}

    except NotImplementedError:
        # Reddit is draft-only
        with Session(engine) as db:
            post = db.get(SocialPost, social_post_id)
            if post:
                post.status = "draft"
                db.commit()
        return {"status": "draft_only"}

    except Exception as exc:
        with Session(engine) as db:
            post = db.get(SocialPost, social_post_id)
            if post:
                post.status = "failed"
                db.commit()
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 20)
    finally:
        engine.dispose()
