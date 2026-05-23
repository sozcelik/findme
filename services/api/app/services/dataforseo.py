import base64
from typing import Any
import httpx
from app.config import settings

BASE_URL = "https://api.dataforseo.com/v3"


def _auth() -> dict[str, str]:
    creds = f"{settings.dataforseo_login}:{settings.dataforseo_password}"
    return {"Authorization": "Basic " + base64.b64encode(creds.encode()).decode()}


async def fetch_serp(
    keyword: str,
    language_code: str = "en",
    location_code: int = 2840,  # United States
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{BASE_URL}/serp/google/organic/live/advanced",
            headers={**_auth(), "Content-Type": "application/json"},
            json=[{
                "keyword": keyword,
                "language_code": language_code,
                "location_code": location_code,
                "calculate_rectangles": False,
                "depth": 10,
            }],
        )
        r.raise_for_status()
        data = r.json()

    task = (data.get("tasks") or [{}])[0]
    result = ((task.get("result") or [{}])[0])
    items = result.get("items") or []

    organic = [
        {
            "position": item.get("rank_absolute"),
            "url": item.get("url"),
            "domain": item.get("domain"),
            "title": item.get("title"),
            "description": item.get("description"),
        }
        for item in items
        if item.get("type") == "organic"
    ]

    featured_snippet = next(
        (item for item in items if item.get("type") == "featured_snippet"), None
    )

    return {
        "keyword": keyword,
        "organic_results": organic[:10],
        "featured_snippet": featured_snippet,
        "total_count": result.get("total_count"),
    }


async def fetch_backlink_opportunities(
    target_domain: str,
    limit: int = 20,
) -> list[dict]:
    """
    Fetch referring domains linking to competitors to find outreach targets.
    Uses DataForSEO Backlinks Domain Pages API.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{BASE_URL}/backlinks/referring_domains/live",
            headers={**_auth(), "Content-Type": "application/json"},
            json=[{
                "target": target_domain,
                "limit": limit,
                "order_by": ["rank,desc"],
                "filters": [["is_new", "=", True]],
            }],
        )
        r.raise_for_status()
        data = r.json()

    task = (data.get("tasks") or [{}])[0]
    items = (task.get("result") or [{}])[0].get("items") or []

    return [
        {
            "domain": item.get("domain"),
            "domain_rank": item.get("rank"),
            "backlinks": item.get("backlinks"),
            "referring_pages": item.get("referring_pages"),
        }
        for item in items
        if item.get("domain")
    ]


async def fetch_keyword_data(
    keywords: list[str],
    language_code: str = "en",
    location_code: int = 2840,
) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{BASE_URL}/keywords_data/google_ads/search_volume/live",
            headers={**_auth(), "Content-Type": "application/json"},
            json=[{
                "keywords": keywords[:100],
                "language_code": language_code,
                "location_code": location_code,
            }],
        )
        r.raise_for_status()
        data = r.json()

    task = (data.get("tasks") or [{}])[0]
    result = task.get("result") or []

    return [
        {
            "keyword": item.get("keyword"),
            "search_volume": item.get("search_volume"),
            "cpc": item.get("cpc"),
            "keyword_difficulty": item.get("keyword_difficulty") or item.get("competition_index"),
            "search_intent": None,
        }
        for item in result
    ]
