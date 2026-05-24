"""
Schema.org JSON-LD markup generator for AEO-optimized content.
Generates Article and FAQPage schemas that help AI models and search engines
understand and cite the content.
"""

import json
import re
from datetime import datetime, timezone


def generate_article_schema(
    title: str,
    description: str,
    url: str,
    publisher_name: str,
    published_at: str | None = None,
) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title[:110],
        "description": description[:300],
        "url": url,
        "datePublished": published_at or datetime.now(timezone.utc).isoformat(),
        "dateModified": datetime.now(timezone.utc).isoformat(),
        "author": {
            "@type": "Organization",
            "name": publisher_name,
        },
        "publisher": {
            "@type": "Organization",
            "name": publisher_name,
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": url,
        },
    }


def generate_faq_schema(markdown: str) -> dict | None:
    """Extract Q&A pairs from markdown and generate FAQPage schema."""
    pairs = _extract_faq_pairs(markdown)
    if not pairs:
        return None

    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": a[:500],
                },
            }
            for q, a in pairs
        ],
    }


def generate_howto_schema(title: str, markdown: str) -> dict | None:
    """Generate HowTo schema if article contains numbered steps."""
    steps = _extract_steps(markdown)
    if len(steps) < 3:
        return None

    return {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": title,
        "step": [
            {
                "@type": "HowToStep",
                "position": i + 1,
                "name": step[:100],
                "text": step,
            }
            for i, step in enumerate(steps)
        ],
    }


def generate_all_schemas(
    title: str,
    markdown: str,
    url: str,
    publisher_name: str,
    published_at: str | None = None,
) -> list[dict]:
    schemas = []

    # Extract description from first paragraph
    description = _first_paragraph(markdown)

    schemas.append(generate_article_schema(title, description, url, publisher_name, published_at))

    faq = generate_faq_schema(markdown)
    if faq:
        schemas.append(faq)

    howto = generate_howto_schema(title, markdown)
    if howto:
        schemas.append(howto)

    return schemas


def schemas_to_html(schemas: list[dict]) -> str:
    """Render schemas as <script type='application/ld+json'> tags."""
    tags = []
    for schema in schemas:
        tags.append(
            f'<script type="application/ld+json">\n{json.dumps(schema, ensure_ascii=False, indent=2)}\n</script>'
        )
    return "\n".join(tags)


# ── Private helpers ──────────────────────────────────────────────────────────

def _extract_faq_pairs(markdown: str) -> list[tuple[str, str]]:
    """Extract question/answer pairs from FAQ section or question headings."""
    pairs: list[tuple[str, str]] = []
    lines = markdown.splitlines()
    in_faq = False
    current_q: str | None = None
    current_a_lines: list[str] = []

    for line in lines:
        lower = line.lower().strip()

        if re.match(r"#{1,3}\s*(faq|frequently asked|sık sorulan)", lower):
            in_faq = True
            continue

        # New major section ends FAQ
        if in_faq and re.match(r"^#{1,2}\s+", line) and not re.match(r"#{3,}", line):
            if not re.match(r"#{1,3}\s*(faq|frequently asked|sık sorulan)", lower):
                if "?" not in line:
                    break

        # Question heading
        if re.match(r"^#{2,4}\s+.+\?", line):
            if current_q and current_a_lines:
                pairs.append((current_q, " ".join(current_a_lines).strip()))
            current_q = re.sub(r"^#{2,4}\s+", "", line).strip()
            current_a_lines = []
        elif current_q and line.strip() and not line.startswith("#"):
            current_a_lines.append(line.strip())

    if current_q and current_a_lines:
        pairs.append((current_q, " ".join(current_a_lines).strip()))

    return pairs[:10]


def _extract_steps(markdown: str) -> list[str]:
    """Extract numbered steps from markdown."""
    steps = re.findall(r"^\d+\.\s+(.+)", markdown, re.MULTILINE)
    return [s.strip() for s in steps if len(s.strip()) > 20]


def _first_paragraph(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("!") and len(stripped) > 50:
            return stripped[:300]
    return ""
