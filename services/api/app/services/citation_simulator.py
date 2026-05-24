"""
Citation Simulator — checks whether a brand/domain is mentioned when
AI models (Claude, GPT-4o, Perplexity) answer category queries.

Each "check" runs N queries against M models and stores per-row results
in the citation_results table so trends can be tracked over time.
"""

import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.config import settings


# ── Query generation ─────────────────────────────────────────────────────────

def build_queries(project, keywords: list) -> list[str]:
    """Generate representative queries a user might ask an AI model."""
    queries: list[str] = []

    for kw in keywords[:3]:
        kw_text = kw.keyword if hasattr(kw, "keyword") else str(kw)
        queries.append(f"What are the best {kw_text} tools in 2025?")
        queries.append(f"Recommend a {kw_text} solution for a growing startup")

    if project.business_description:
        short_desc = project.business_description[:120].rstrip(".,")
        queries.append(f"What tools help with: {short_desc}?")

    # Branded: "alternatives to competitor" — skipped unless we have competitors
    return queries[:6]


# ── Model callers ─────────────────────────────────────────────────────────────

def ask_claude(query: str) -> str:
    """Call Claude claude-sonnet-4-6 synchronously."""
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=(
            "You are a helpful assistant. Answer the user's question concisely. "
            "If recommending tools or products, provide a ranked list of 5-7 options "
            "with a one-sentence description of each."
        ),
        messages=[{"role": "user", "content": query}],
    )
    return message.content[0].text if message.content else ""


def ask_openai(query: str) -> str:
    """Call GPT-4o via OpenAI API (sync httpx)."""
    r = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o-mini",
            "max_tokens": 512,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant. Answer the user's question concisely. "
                        "If recommending tools or products, provide a ranked list of 5-7 options "
                        "with a one-sentence description of each."
                    ),
                },
                {"role": "user", "content": query},
            ],
        },
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def ask_perplexity(query: str) -> str:
    """Call Perplexity sonar model (web-search enabled) via OpenAI-compatible API."""
    r = httpx.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.perplexity_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "sonar",
            "max_tokens": 512,
            "messages": [
                {"role": "system", "content": "Be precise and concise."},
                {"role": "user", "content": query},
            ],
        },
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# ── Mention parser ────────────────────────────────────────────────────────────

def parse_mention(
    response: str,
    domain: str,
    brand_name: str,
) -> dict:
    """
    Detect if brand/domain is mentioned in the response.
    Returns: mentioned, position, sentiment, excerpt
    """
    lower = response.lower()
    brand_lower = brand_name.lower()
    domain_lower = domain.lower().replace("www.", "")

    # Check for mention
    mentioned = brand_lower in lower or domain_lower in lower

    if not mentioned:
        return {
            "mentioned": False,
            "mention_position": None,
            "sentiment": "none",
            "excerpt": None,
        }

    # Extract the sentence containing the mention
    sentences = re.split(r"(?<=[.!?])\s+", response)
    excerpt = next(
        (s for s in sentences if brand_lower in s.lower() or domain_lower in s.lower()),
        None,
    )

    # Try to determine list position (e.g. "1. Stripe", "2. Braintree")
    position = None
    for i, line in enumerate(response.splitlines()):
        if brand_lower in line.lower() or domain_lower in line.lower():
            # Check if line starts with a number
            match = re.match(r"^\s*(\d+)[\.\)]\s+", line)
            if match:
                position = int(match.group(1))
            break

    # Simple sentiment: positive if recommended/praised, negative if criticized
    positive_words = ("recommend", "best", "excellent", "great", "top", "leading", "popular", "widely used")
    negative_words = ("avoid", "not recommend", "poor", "limited", "expensive", "worse")
    excerpt_lower = (excerpt or "").lower()
    if any(w in excerpt_lower for w in negative_words):
        sentiment = "negative"
    elif any(w in excerpt_lower for w in positive_words):
        sentiment = "positive"
    else:
        sentiment = "neutral"

    return {
        "mentioned": True,
        "mention_position": position,
        "sentiment": sentiment,
        "excerpt": (excerpt or "")[:500],
    }


# ── Main simulation runner ────────────────────────────────────────────────────

def run_simulation(
    project,
    keywords: list,
    job_id: str,
    db: Session,
) -> dict:
    """
    Run citation simulation for all available models.
    Stores CitationResult rows and returns summary stats.
    """
    from app.db.models.citation_result import CitationResult

    domain = _bare_domain(project.website_url)
    brand_name = project.name
    queries = build_queries(project, keywords)
    checked_at = datetime.now(timezone.utc)

    available_models: list[tuple[str, callable]] = []
    if settings.anthropic_api_key:
        available_models.append(("claude", ask_claude))
    if settings.openai_api_key:
        available_models.append(("gpt-4o-mini", ask_openai))
    if settings.perplexity_api_key:
        available_models.append(("perplexity", ask_perplexity))

    rows: list[CitationResult] = []
    errors: list[str] = []

    for query in queries:
        for model_name, caller in available_models:
            try:
                response = caller(query)
                parsed = parse_mention(response, domain, brand_name)
                rows.append(CitationResult(
                    id=str(uuid.uuid4()),
                    project_id=project.id,
                    org_id=project.org_id,
                    job_id=job_id,
                    query=query,
                    model=model_name,
                    mentioned=parsed["mentioned"],
                    mention_position=parsed["mention_position"],
                    sentiment=parsed["sentiment"],
                    excerpt=parsed["excerpt"],
                    full_response=response[:2000],
                    checked_at=checked_at,
                ))
            except Exception as e:
                errors.append(f"{model_name}: {e}")

    for row in rows:
        db.add(row)
    db.commit()

    # Build summary
    summary: dict = {}
    for model_name, _ in available_models:
        model_rows = [r for r in rows if r.model == model_name]
        mentioned = [r for r in model_rows if r.mentioned]
        summary[model_name] = {
            "queries_run": len(model_rows),
            "mentioned_count": len(mentioned),
            "mention_rate": round(len(mentioned) / len(model_rows) * 100) if model_rows else 0,
            "avg_position": (
                round(sum(r.mention_position for r in mentioned if r.mention_position) /
                      max(1, sum(1 for r in mentioned if r.mention_position)), 1)
                if mentioned else None
            ),
            "results": [
                {
                    "query": r.query,
                    "mentioned": r.mentioned,
                    "position": r.mention_position,
                    "sentiment": r.sentiment,
                    "excerpt": r.excerpt,
                }
                for r in model_rows
            ],
        }

    return {
        "domain": domain,
        "queries_run": len(queries),
        "models_checked": [m for m, _ in available_models],
        "summary": summary,
        "errors": errors,
        "checked_at": checked_at.isoformat(),
    }


def _bare_domain(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.netloc or parsed.path).replace("www.", "")
