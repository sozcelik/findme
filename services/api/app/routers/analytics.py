from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.keyword import Keyword
from app.db.models.keyword_ranking import KeywordRanking
from app.db.models.visibility_score_history import VisibilityScoreHistory
from app.db.models.project import Project

router = APIRouter()

ORG_ID = "org-dev-1"


@router.get("/rankings")
async def get_rankings(
    project_id: str,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(KeywordRanking, Keyword)
        .join(Keyword, KeywordRanking.keyword_id == Keyword.id)
        .where(KeywordRanking.project_id == project_id)
        .order_by(KeywordRanking.checked_at.desc(), KeywordRanking.position.asc())
        .limit(limit)
    )
    rows = result.all()

    return [
        {
            "keyword": kw.keyword,
            "position": ranking.position,
            "searchVolume": kw.search_volume,
            "checkedAt": ranking.checked_at.isoformat(),
            "urlRanking": ranking.url_ranking,
        }
        for ranking, kw in rows
    ]


@router.get("/visibility")
async def get_visibility_history(
    project_id: str,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project or project.org_id != ORG_ID:
        raise HTTPException(status_code=404, detail="Project not found")

    from datetime import date, timedelta
    cutoff = date.today() - timedelta(days=days)

    result = await db.execute(
        select(VisibilityScoreHistory)
        .where(
            VisibilityScoreHistory.project_id == project_id,
            VisibilityScoreHistory.score_date >= cutoff,
        )
        .order_by(VisibilityScoreHistory.score_date.asc())
    )
    rows = result.scalars().all()

    return [
        {
            "date": row.score_date.isoformat(),
            "total": row.total_score,
            "seoQuality": row.seo_quality,
            "aiReadability": row.ai_readability,
            "semanticClarity": row.semantic_clarity,
            "socialAmplification": row.social_amplification,
            "authoritySignals": row.authority_signals,
            "distributionCoverage": row.distribution_coverage,
        }
        for row in rows
    ]
