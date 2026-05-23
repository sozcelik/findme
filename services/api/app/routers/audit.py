"""
Free domain audit — no credits consumed.
Returns suggested keywords + competitor list from DataForSEO.
Falls back gracefully when DataForSEO credentials are not configured.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class AuditRequest(BaseModel):
    url: str
    language_code: str = "en"
    location_code: int = 2840


@router.post("")
async def run_domain_audit(body: AuditRequest):
    from app.config import settings

    if not settings.dataforseo_login or not settings.dataforseo_password:
        # Dev fallback — return mock suggestions so the UI still works locally
        return _mock_response(body.url)

    from app.services.dataforseo import fetch_domain_keywords, fetch_domain_competitors
    import asyncio

    try:
        keywords, competitors = await asyncio.gather(
            fetch_domain_keywords(body.url, body.language_code, body.location_code),
            fetch_domain_competitors(body.url, body.language_code, body.location_code),
            return_exceptions=True,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"DataForSEO error: {e}")

    # gather() returns exceptions as values when return_exceptions=True
    if isinstance(keywords, Exception):
        keywords = []
    if isinstance(competitors, Exception):
        competitors = []

    return {
        "domain": _bare_domain(body.url),
        "keywords": keywords[:50],
        "competitors": competitors[:10],
        "source": "dataforseo",
    }


def _bare_domain(url: str) -> str:
    from urllib.parse import urlparse
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return parsed.netloc or parsed.path


def _mock_response(url: str) -> dict:
    domain = _bare_domain(url)
    return {
        "domain": domain,
        "keywords": [
            {"keyword": f"{domain} review", "search_volume": 1200, "cpc": 1.5, "keyword_difficulty": 28, "position": 4},
            {"keyword": f"best {domain} alternative", "search_volume": 880, "cpc": 2.1, "keyword_difficulty": 35, "position": 7},
            {"keyword": f"how to use {domain}", "search_volume": 590, "cpc": 0.8, "keyword_difficulty": 18, "position": 3},
            {"keyword": f"{domain} pricing", "search_volume": 440, "cpc": 3.2, "keyword_difficulty": 22, "position": 6},
            {"keyword": f"{domain} features", "search_volume": 320, "cpc": 1.1, "keyword_difficulty": 15, "position": 2},
        ],
        "competitors": [
            {"domain": "competitor-one.com", "avg_position": 5.2, "intersections": 42, "competitor_metrics": {}},
            {"domain": "competitor-two.com", "avg_position": 6.8, "intersections": 31, "competitor_metrics": {}},
            {"domain": "competitor-three.com", "avg_position": 8.1, "intersections": 24, "competitor_metrics": {}},
        ],
        "source": "mock",
    }
