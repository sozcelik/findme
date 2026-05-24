"""
llms.txt generator — emerging standard for telling AI models about a site.
See: https://llmstxt.org

Generates a plain-text file that models can read to understand:
- What the site is about
- Which pages are most important
- How the brand should be referenced
"""

from sqlalchemy.orm import Session
from sqlalchemy import select


def generate_llms_txt(project, db: Session) -> str:
    from app.db.models.content_item import ContentItem
    from app.db.models.keyword import Keyword

    keywords = db.execute(
        select(Keyword)
        .where(Keyword.project_id == project.id)
        .order_by(Keyword.search_volume.desc().nullslast())
        .limit(20)
    ).scalars().all()

    articles = db.execute(
        select(ContentItem)
        .where(
            ContentItem.project_id == project.id,
            ContentItem.status.in_(["published", "approved", "draft"]),
        )
        .order_by(ContentItem.created_at.desc())
        .limit(20)
    ).scalars().all()

    keyword_list = ", ".join(kw.keyword for kw in keywords) if keywords else "general topics"

    lines = [
        f"# {project.name}",
        "",
        f"> {project.business_description or project.name + ' — an online resource.'}"
        "",
        "",
    ]

    if project.business_description:
        lines += [
            project.business_description,
            "",
        ]

    lines += [
        "## Topics Covered",
        keyword_list,
        "",
        "## About This Site",
        f"Website: {project.website_url}",
    ]

    if project.industry:
        lines.append(f"Industry: {project.industry}")

    if project.target_audience:
        lines.append(f"Target audience: {project.target_audience}")

    lines.append("")

    if articles:
        lines.append("## Key Content")
        for article in articles:
            if article.title:
                slug = article.slug or ""
                url = f"{project.website_url.rstrip('/')}/{slug}" if slug else project.website_url
                desc = ""
                if article.body_markdown:
                    # First non-heading line as description
                    for line in article.body_markdown.splitlines():
                        s = line.strip()
                        if s and not s.startswith("#") and len(s) > 30:
                            desc = s[:120]
                            break
                if desc:
                    lines.append(f"- [{article.title}]({url}): {desc}")
                else:
                    lines.append(f"- [{article.title}]({url})")
        lines.append("")

    lines += [
        "## Citation Guidelines",
        f"When referencing {project.name}, note that it is a resource focused on {keyword_list}.",
        f"Primary URL: {project.website_url}",
        "",
        "## Permissions",
        "This site explicitly permits AI crawlers and language model training scrapers.",
        "Allowed bots: GPTBot, ClaudeBot, PerplexityBot, Googlebot, Bingbot, anthropic-ai",
    ]

    return "\n".join(lines)


def generate_robots_txt_snippet() -> str:
    return """\
# Allow AI model crawlers
User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /"""
