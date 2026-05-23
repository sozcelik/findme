import anthropic
from app.config import settings

# Tier 2: content type template — static, cached once per worker at import time
ARTICLE_TEMPLATE = """You are an expert SEO content writer. When generating articles:
- Structure with H2/H3 headings for AI readability and featured snippet capture
- Include a FAQ section with 5 questions at the end
- Write clear, direct answers — AI search engines cite concise, factual paragraphs
- Use the focus keyword naturally (2-3% density), semantic keywords throughout
- Target 1500-2500 words for comprehensive coverage
- Use bullet points and numbered lists for scannable structure
- Add [INTERNAL_LINK: topic] placeholders where relevant internal links could go
- End with a strong CTA paragraph"""

OUTREACH_TEMPLATE = """You are an expert digital PR and link-building specialist.
Write concise, personalized outreach emails that:
- Open with a genuine, specific observation about the target site
- Explain the value proposition clearly (why linking to us benefits their readers)
- Keep the email under 200 words — decision-makers don't read long emails
- Use a friendly but professional tone — not salesy
- Include a specific call-to-action"""

AI_VISIBILITY_RUBRIC = """You are an AI search engine evaluator. Score content on how likely an AI assistant
(like ChatGPT, Claude, Perplexity) would cite it as a direct answer to a user query.

Scoring criteria (0-100):
- Direct answers: Does the content answer questions directly and concisely? (25 pts)
- Structure: H2/H3 headings, bullet points, numbered lists? (20 pts)
- FAQ coverage: Does it anticipate follow-up questions? (20 pts)
- Entity clarity: Are people, places, products named precisely? (15 pts)
- Factual depth: Statistics, dates, specific numbers present? (20 pts)

Return JSON: {"score": <0-100>, "suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"]}"""

_sync_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _sync_client
    if _sync_client is None:
        _sync_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _sync_client


def generate_seo_brief(
    project_name: str,
    website_url: str,
    business_description: str,
    keywords_with_serp: list[dict],
) -> tuple[str, float]:
    """
    Generate SEO strategy brief using Claude Opus 4.7.
    SERP data goes in a cached user message (Tier 3).
    Returns (brief_text, cost_usd).
    """
    client = get_client()

    serp_context = "\n\n".join(
        f"**{kw['keyword']}** | Volume: {kw.get('search_volume') or '?'} | "
        f"Difficulty: {kw.get('keyword_difficulty') or '?'}\n"
        + "\n".join(
            f"  {r['position']}. {r.get('domain','')} — {r.get('title','')}"
            for r in (kw.get("serp_results") or [])[:5]
        )
        for kw in keywords_with_serp[:10]
    )

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": (
                    f"You are an expert SEO strategist for {project_name} ({website_url}). "
                    f"Business: {business_description or 'Not specified'}. "
                    "Provide actionable, data-driven SEO briefs."
                ),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"## SERP Data\n\n{serp_context}",
                        "cache_control": {"type": "ephemeral"},  # Tier 3: cached per run
                    },
                    {
                        "type": "text",
                        "text": (
                            "Analyze the SERP data above and generate a comprehensive SEO brief:\n\n"
                            "1. **Keyword Clusters** — group related keywords by topic\n"
                            "2. **Competitor Gaps** — what top-ranking content covers that we don't\n"
                            "3. **Recommended Articles** — 5 specific article titles with focus keywords\n"
                            "4. **Quick Wins** — low-difficulty keywords worth targeting first\n"
                            "5. **Search Intent Map** — classify each keyword by intent\n\n"
                            "Be specific and actionable."
                        ),
                    },
                ],
            }
        ],
    )

    brief = response.content[0].text
    cost = (response.usage.output_tokens / 1_000_000) * 15.0  # Opus 4.7 output
    return brief, cost


SOCIAL_TEMPLATE = """You are a social media content expert. Generate platform-optimized posts that:
- LinkedIn: professional tone, 150-300 words, insight-driven, 3-5 relevant hashtags
- Twitter/X: punchy, max 270 chars, 2-3 hashtags, strong hook
- Reddit: conversational, no self-promotion tone, discussion-oriented title + body"""


def generate_social_posts(
    article_title: str,
    article_markdown: str,
    focus_keyword: str,
) -> tuple[dict[str, dict], float]:
    """
    Generate LinkedIn, Twitter, Reddit posts for an article.
    Returns (posts_by_platform, cost_usd).
    posts_by_platform = {"linkedin": {"body": ..., "hashtags": [...]}, ...}
    """
    client = get_client()

    snippet = article_markdown[:1500]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": SOCIAL_TEMPLATE,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    f"Article title: {article_title}\n"
                    f"Focus keyword: {focus_keyword}\n\n"
                    f"Article excerpt:\n{snippet}\n\n"
                    "Generate social posts in this exact JSON format:\n"
                    '{"linkedin": {"body": "...", "hashtags": ["tag1", "tag2"]}, '
                    '"twitter": {"body": "...", "hashtags": ["tag1", "tag2"]}, '
                    '"reddit": {"title": "...", "body": "..."}}'
                ),
            }
        ],
    )

    import json as _json
    raw = response.content[0].text
    # Extract JSON block if wrapped in markdown code fences
    if "```" in raw:
        raw = raw.split("```")[1].lstrip("json").strip()

    try:
        posts = _json.loads(raw)
    except Exception:
        posts = {}

    cost = (response.usage.output_tokens / 1_000_000) * 3.75
    return posts, cost


def generate_article(
    project_seo_brief: str,
    topic: str,
    focus_keyword: str,
    target_audience: str | None = None,
) -> tuple[str, float]:
    """
    Generate a full SEO article using Claude Sonnet 4.6.
    Uses two cached system blocks (Tier 1 + Tier 2).
    Returns (article_markdown, cost_usd).
    """
    client = get_client()

    audience = f"Target audience: {target_audience}." if target_audience else ""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8096,
        system=[
            {
                "type": "text",
                "text": ARTICLE_TEMPLATE,
                "cache_control": {"type": "ephemeral"},  # Tier 2: template, stable across articles
            },
            {
                "type": "text",
                "text": f"## Project SEO Brief\n\n{project_seo_brief}",
                "cache_control": {"type": "ephemeral"},  # Tier 1: per-project brief
            },
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    f"Write a comprehensive SEO article.\n\n"
                    f"Topic: {topic}\n"
                    f"Focus keyword: {focus_keyword}\n"
                    f"{audience}\n\n"
                    "Include: H1 title, intro paragraph, 4-6 H2 sections with H3 subsections, "
                    "FAQ section (5 Q&A), conclusion with CTA. Output in Markdown."
                ),
            }
        ],
    )

    article = response.content[0].text
    # Cost: cache read $0.30/1M + output $3.75/1M (Sonnet 4.6)
    cache_read = getattr(response.usage, "cache_read_input_tokens", 0)
    cost = (cache_read / 1_000_000) * 0.30 + (response.usage.output_tokens / 1_000_000) * 3.75
    return article, cost


def generate_outreach_email(
    project_name: str,
    website_url: str,
    target_domain: str,
    domain_authority: int,
) -> tuple[str, float]:
    """
    Generate a personalized outreach email using Claude Opus 4.7.
    Returns (email_text, cost_usd).
    """
    client = get_client()

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        system=[
            {
                "type": "text",
                "text": OUTREACH_TEMPLATE,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    f"Write a backlink outreach email.\n\n"
                    f"Our site: {website_url} ({project_name})\n"
                    f"Target site: {target_domain} (Domain Authority: {domain_authority})\n\n"
                    "Write a short, personalized email requesting a backlink or guest post opportunity. "
                    "Subject line first, then email body. Do not use placeholders like [Your Name]."
                ),
            }
        ],
    )

    email = response.content[0].text
    cost = (response.usage.output_tokens / 1_000_000) * 15.0  # Opus 4.7 output
    return email, cost


def evaluate_ai_visibility(
    title: str,
    body_markdown: str,
    focus_keyword: str,
) -> tuple[float, list[str], float]:
    """
    Evaluate content AI visibility using Claude Sonnet 4.6 with structured rubric.
    Returns (score_0_to_100, suggestions, cost_usd).
    """
    import json as _json

    client = get_client()

    snippet = body_markdown[:3000]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=[
            {
                "type": "text",
                "text": AI_VISIBILITY_RUBRIC,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    f"Title: {title}\n"
                    f"Focus keyword: {focus_keyword}\n\n"
                    f"Content:\n{snippet}\n\n"
                    "Evaluate and return JSON only."
                ),
            }
        ],
    )

    raw = response.content[0].text
    if "```" in raw:
        raw = raw.split("```")[1].lstrip("json").strip()

    try:
        result = _json.loads(raw)
        score = float(result.get("score", 0))
        suggestions = result.get("suggestions", [])
    except Exception:
        score = 0.0
        suggestions = []

    cost = (response.usage.output_tokens / 1_000_000) * 3.75
    return score, suggestions, cost
