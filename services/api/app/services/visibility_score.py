"""
Full 6-dimension visibility score engine.

Dimensions and weights:
  SEO Quality         30%
  AI Readability      20%
  Semantic Clarity    15%
  Social Amplification 15%
  Authority Signals   15%
  Distribution Coverage 5%
"""

from datetime import date, timezone, datetime
from sqlalchemy.orm import Session
from app.db.models.project import Project
from app.db.models.content_item import ContentItem
from app.db.models.keyword import Keyword
from app.db.models.competitor import Competitor
from app.db.models.social_post import SocialPost
from app.db.models.cms_connection import CmsConnection
from app.db.models.social_connection import SocialConnection
from app.db.models.visibility_score_history import VisibilityScoreHistory


def calculate_full_score(
    project: Project, org_id: str, db: Session
) -> tuple[float, dict]:
    """
    Compute the full 6-dimension score. Returns (total_score, dimension_breakdown).
    Upserts a VisibilityScoreHistory record for today.
    """
    seo = _seo_quality(project, db)
    ai = _ai_readability(project, db)
    semantic = _semantic_clarity(project, db)
    social = _social_amplification(project, org_id, db)
    authority = _authority_signals(project, db)
    distribution = _distribution_coverage(project, org_id, db)

    total = (
        seo * 0.30
        + ai * 0.20
        + semantic * 0.15
        + social * 0.15
        + authority * 0.15
        + distribution * 0.05
    ) * 100.0
    total = round(min(max(total, 0.0), 100.0), 1)

    breakdown = {
        "seoQuality": round(seo * 100, 1),
        "aiReadability": round(ai * 100, 1),
        "semanticClarity": round(semantic * 100, 1),
        "socialAmplification": round(social * 100, 1),
        "authoritySignals": round(authority * 100, 1),
        "distributionCoverage": round(distribution * 100, 1),
    }

    _upsert_history(project, org_id, total, seo, ai, semantic, social, authority, distribution, breakdown, db)

    return total, breakdown


def calculate_partial_score(project: Project, db: Session) -> float:
    """
    Phase 1-compatible wrapper — returns just the total score using all six dimensions.
    Used by the agent_tasks pipeline to set project.visibility_score.
    """
    from app.db.models.org import Organization
    org = db.get(Organization, project.org_id) if hasattr(project, "org_id") else None
    org_id = org.id if org else "org-dev-1"
    score, _ = calculate_full_score(project, org_id, db)
    return score


# ──────────────────────────────────────────────
# Dimension calculators — each returns 0.0–1.0
# ──────────────────────────────────────────────


def _seo_quality(project: Project, db: Session) -> float:
    keywords = db.query(Keyword).filter(Keyword.project_id == project.id).all()
    if not keywords:
        return 0.0

    analyzed = [kw for kw in keywords if kw.last_analyzed_at is not None]
    if not analyzed:
        return 0.05

    coverage = len(analyzed) / len(keywords)
    easy = sum(1 for kw in analyzed if kw.keyword_difficulty and kw.keyword_difficulty < 30)
    quick_win_boost = min(easy * 0.08, 0.25)

    has_volume = any(kw.search_volume for kw in analyzed)
    data_boost = 0.15 if has_volume else 0.0

    # Bonus: project has content with seo_score populated
    scored_content = db.query(ContentItem).filter(
        ContentItem.project_id == project.id,
        ContentItem.seo_score.isnot(None),
    ).count()
    content_boost = min(scored_content * 0.05, 0.15)

    return min(coverage * 0.45 + quick_win_boost + data_boost + content_boost, 1.0)


def _ai_readability(project: Project, db: Session) -> float:
    items = db.query(ContentItem).filter(
        ContentItem.project_id == project.id,
        ContentItem.status.in_(["draft", "review", "approved", "published"]),
    ).all()

    if not items:
        return 0.0

    scores = []
    for item in items:
        # Use stored ai_visibility_score if available (set by AIVisibilityAgent)
        if item.ai_visibility_score is not None:
            scores.append(item.ai_visibility_score / 100.0)
            continue

        if not item.body_markdown:
            scores.append(0.05)
            continue

        md = item.body_markdown
        has_h2 = "## " in md
        has_h3 = "### " in md
        has_faq = "faq" in md.lower() or "frequently asked" in md.lower()
        word_count = len(md.split())
        length_score = min(word_count / 1500, 1.0)
        s = (
            (0.30 if has_h2 else 0.0)
            + (0.15 if has_h3 else 0.0)
            + (0.20 if has_faq else 0.0)
            + (0.35 * length_score)
        )
        scores.append(s)

    return sum(scores) / len(scores) if scores else 0.0


def _semantic_clarity(project: Project, db: Session) -> float:
    """
    Proxy: content volume + keyword cluster diversity.
    Full implementation requires pgvector cosine similarity across embeddings.
    """
    published = db.query(ContentItem).filter(
        ContentItem.project_id == project.id,
        ContentItem.status.in_(["published", "approved"]),
    ).count()

    keyword_count = db.query(Keyword).filter(Keyword.project_id == project.id).count()

    content_score = min(published / 10.0, 1.0)  # 10 published = full score
    cluster_score = min(keyword_count / 20.0, 1.0)  # 20 keywords = full score

    return content_score * 0.6 + cluster_score * 0.4


def _social_amplification(project: Project, org_id: str, db: Session) -> float:
    posts = db.query(SocialPost).filter(
        SocialPost.project_id == project.id,
        SocialPost.status == "posted",
    ).all()

    if not posts:
        return 0.0

    platforms = len({p.platform for p in posts})
    platform_score = min(platforms / 3.0, 1.0)

    # Posting frequency: score based on posts in last 30 days
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    recent = [p for p in posts if p.posted_at and p.posted_at.replace(tzinfo=timezone.utc) >= cutoff]
    frequency_score = min(len(recent) / 12.0, 1.0)  # 12 posts/month = full score

    # Engagement bonus
    total_engagement = 0
    for p in posts:
        if p.engagement:
            total_engagement += (
                (p.engagement.get("likes") or 0)
                + (p.engagement.get("shares") or 0)
                + (p.engagement.get("comments") or 0)
            )
    engagement_score = min(total_engagement / 500.0, 1.0)

    return platform_score * 0.30 + frequency_score * 0.40 + engagement_score * 0.30


def _authority_signals(project: Project, db: Session) -> float:
    """
    Based on competitor analysis data (backlinks available from DataForSEO).
    Proxy: number of competitors found and their domain authority.
    """
    competitors = db.query(Competitor).filter(Competitor.project_id == project.id).all()

    if not competitors:
        return 0.0

    # Having competitor data means we've run SERP analysis — base score
    base = 0.25

    # Domain authority scores from competitors give us benchmark data
    da_scores = [c.domain_authority for c in competitors if c.domain_authority]
    if da_scores:
        avg_competitor_da = sum(da_scores) / len(da_scores)
        # Our relative authority (placeholder — no DA for our domain yet)
        # Score based on having the data itself + number of tracked competitors
        competitor_count_score = min(len(competitors) / 10.0, 0.75)
        return base + competitor_count_score
    return base


def _distribution_coverage(project: Project, org_id: str, db: Session) -> float:
    active_cms = db.query(CmsConnection).filter(
        CmsConnection.org_id == org_id,
        CmsConnection.status == "active",
    ).count()

    active_social = db.query(SocialConnection).filter(
        SocialConnection.org_id == org_id,
        SocialConnection.status == "active",
    ).count()

    cms_score = min(active_cms / 2.0, 1.0)    # 2 CMS = full
    social_score = min(active_social / 3.0, 1.0)  # 3 social = full

    return cms_score * 0.5 + social_score * 0.5


def _upsert_history(
    project: Project,
    org_id: str,
    total: float,
    seo: float,
    ai: float,
    semantic: float,
    social: float,
    authority: float,
    distribution: float,
    breakdown: dict,
    db: Session,
) -> None:
    import uuid as _uuid
    today = date.today()
    existing = (
        db.query(VisibilityScoreHistory)
        .filter(
            VisibilityScoreHistory.project_id == project.id,
            VisibilityScoreHistory.score_date == today,
        )
        .first()
    )

    if existing:
        existing.total_score = total
        existing.seo_quality = round(seo * 100, 1)
        existing.ai_readability = round(ai * 100, 1)
        existing.semantic_clarity = round(semantic * 100, 1)
        existing.social_amplification = round(social * 100, 1)
        existing.authority_signals = round(authority * 100, 1)
        existing.distribution_coverage = round(distribution * 100, 1)
        existing.raw_inputs = breakdown
    else:
        record = VisibilityScoreHistory(
            id=str(_uuid.uuid4()),
            project_id=project.id,
            org_id=org_id,
            score_date=today,
            total_score=total,
            seo_quality=round(seo * 100, 1),
            ai_readability=round(ai * 100, 1),
            semantic_clarity=round(semantic * 100, 1),
            social_amplification=round(social * 100, 1),
            authority_signals=round(authority * 100, 1),
            distribution_coverage=round(distribution * 100, 1),
            raw_inputs=breakdown,
        )
        db.add(record)
