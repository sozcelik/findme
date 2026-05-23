import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models.keyword import Keyword

router = APIRouter()

ORG_ID = "org-dev-1"


class AddKeywordsRequest(BaseModel):
    keywords: list[str]


@router.get("/{project_id}/keywords")
async def list_keywords(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Keyword)
        .where(Keyword.project_id == project_id, Keyword.org_id == ORG_ID)
        .order_by(Keyword.created_at.desc())
    )
    return [_serialize(kw) for kw in result.scalars().all()]


@router.post("/{project_id}/keywords", status_code=201)
async def add_keywords(
    project_id: str,
    body: AddKeywordsRequest,
    db: AsyncSession = Depends(get_db),
):
    created = []
    for raw in body.keywords[:100]:
        kw_text = raw.strip().lower()
        if not kw_text:
            continue
        exists = (
            await db.execute(
                select(Keyword).where(
                    Keyword.project_id == project_id,
                    Keyword.keyword == kw_text,
                )
            )
        ).scalar_one_or_none()
        if exists:
            continue
        kw = Keyword(
            id=str(uuid.uuid4()),
            project_id=project_id,
            org_id=ORG_ID,
            keyword=kw_text,
        )
        db.add(kw)
        created.append(kw)

    await db.commit()
    return [_serialize(kw) for kw in created]


@router.delete("/{project_id}/keywords/{keyword_id}", status_code=204)
async def delete_keyword(
    project_id: str,
    keyword_id: str,
    db: AsyncSession = Depends(get_db),
):
    kw = await db.get(Keyword, keyword_id)
    if not kw or kw.project_id != project_id or kw.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Keyword not found")
    await db.delete(kw)
    await db.commit()


def _serialize(kw: Keyword) -> dict:
    return {
        "id": kw.id,
        "keyword": kw.keyword,
        "searchVolume": kw.search_volume,
        "cpc": kw.cpc,
        "keywordDifficulty": kw.keyword_difficulty,
        "searchIntent": kw.search_intent,
        "currentPosition": kw.current_position,
        "bestPosition": kw.best_position,
        "lastAnalyzedAt": kw.last_analyzed_at.isoformat() if kw.last_analyzed_at else None,
    }
