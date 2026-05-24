from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.content_item import ContentItem
from app.db.models.social_post import SocialPost

router = APIRouter()

ORG_ID = "org-dev-1"


@router.get("")
async def list_content(
    project_id: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ContentItem).where(ContentItem.org_id == ORG_ID)
    if project_id:
        query = query.where(ContentItem.project_id == project_id)
    if status:
        query = query.where(ContentItem.status == status)
    query = query.order_by(ContentItem.created_at.desc())
    result = await db.execute(query)
    return [_serialize(c, body=False) for c in result.scalars().all()]


@router.get("/{content_id}")
async def get_content(content_id: str, db: AsyncSession = Depends(get_db)):
    item = await db.get(ContentItem, content_id)
    if not item or item.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Not found")
    return _serialize(item, body=True)


class UpdateContentRequest(BaseModel):
    title: str | None = None
    bodyMarkdown: str | None = None
    metaTitle: str | None = None
    metaDescription: str | None = None
    status: str | None = None


@router.patch("/{content_id}")
async def update_content(
    content_id: str,
    body: UpdateContentRequest,
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(ContentItem, content_id)
    if not item or item.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Not found")

    if body.title is not None:
        item.title = body.title
    if body.bodyMarkdown is not None:
        item.body_markdown = body.bodyMarkdown
        item.word_count = len(body.bodyMarkdown.split())
    if body.metaTitle is not None:
        item.meta_title = body.metaTitle
    if body.metaDescription is not None:
        item.meta_description = body.metaDescription
    if body.status is not None:
        item.status = body.status

    await db.commit()
    await db.refresh(item)
    return _serialize(item, body=True)


class PublishRequest(BaseModel):
    cmsConnectionId: str


@router.post("/{content_id}/publish")
async def publish_content(
    content_id: str,
    body: PublishRequest,
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(ContentItem, content_id)
    if not item or item.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Not found")

    from app.tasks.publish_tasks import publish_to_cms
    task = publish_to_cms.delay(content_id, body.cmsConnectionId, ORG_ID)
    return {"taskId": task.id, "status": "queued"}


class DistributeRequest(BaseModel):
    socialConnectionId: str
    socialPostId: str


@router.post("/{content_id}/distribute")
async def distribute_content(
    content_id: str,
    body: DistributeRequest,
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(ContentItem, content_id)
    if not item or item.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Not found")

    from app.tasks.publish_tasks import post_to_social
    task = post_to_social.delay(body.socialPostId, body.socialConnectionId, ORG_ID)
    return {"taskId": task.id, "status": "queued"}


@router.get("/{content_id}/social-posts")
async def list_social_posts(content_id: str, db: AsyncSession = Depends(get_db)):
    item = await db.get(ContentItem, content_id)
    if not item or item.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Not found")

    result = await db.execute(
        select(SocialPost)
        .where(SocialPost.content_id == content_id)
        .order_by(SocialPost.platform)
    )
    posts = result.scalars().all()
    return [
        {
            "id": p.id,
            "platform": p.platform,
            "body": p.body,
            "hashtags": (p.hashtags or "").split(),
            "redditTitle": p.reddit_title,
            "status": p.status,
            "postedAt": p.posted_at.isoformat() if p.posted_at else None,
            "externalPostId": p.external_post_id,
        }
        for p in posts
    ]


def _serialize(c: ContentItem, body: bool) -> dict:
    from app.services.aeo_scorer import score_content, score_to_dict
    from app.services.schema_markup import generate_all_schemas

    data: dict = {
        "id": c.id,
        "projectId": c.project_id,
        "type": c.type,
        "title": c.title,
        "slug": c.slug,
        "metaTitle": c.meta_title,
        "metaDescription": c.meta_description,
        "focusKeyword": c.focus_keyword,
        "wordCount": c.word_count,
        "seoScore": c.seo_score,
        "aeoScore": int(c.ai_visibility_score) if c.ai_visibility_score is not None else None,
        "aiVisibilityScore": c.ai_visibility_score,
        "status": c.status,
        "aiModelUsed": c.ai_model_used,
        "generationCost": c.generation_cost,
        "publishedAt": c.published_at.isoformat() if c.published_at else None,
        "createdAt": c.created_at.isoformat(),
    }
    if body and c.body_markdown:
        data["bodyMarkdown"] = c.body_markdown
        aeo_data = score_to_dict(score_content(c.body_markdown))
        data["aeoScore"] = aeo_data["aeo_score"]
        data["aeoBreakdown"] = aeo_data["breakdown"]
        data["aeoSuggestions"] = aeo_data["suggestions"]
        data["schemas"] = generate_all_schemas(
            title=c.title or "",
            markdown=c.body_markdown,
            url=f"/{c.slug or c.id}",
            publisher_name="",
        )
    return data
