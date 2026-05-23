import re
import uuid
from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.db.models.content_item import ContentItem
from app.db.models.social_post import SocialPost


class ContentGenerationAgent(BaseAgent):
    def run(  # type: ignore[override]
        self,
        project_id: str,
        org_id: str,
        db: Session,
        project,
        seo_brief: str,
        topics: list[dict] | None = None,
    ) -> dict:
        from app.services import anthropic_client

        self.emit("content_generation", "running", "Preparing topics...")

        if not topics:
            topics = _parse_topics_from_brief(seo_brief)[:3]

        if not topics:
            self.emit("content_generation", "completed", "No topics found in brief")
            return {"articles_generated": 0, "articles": []}

        articles = []
        total_cost = 0.0

        for i, topic in enumerate(topics):
            label = topic["title"][:60]
            self.emit("content_generation", "running", f"Article {i+1}/{len(topics)}: {label}...")

            try:
                markdown, cost = anthropic_client.generate_article(
                    project_seo_brief=seo_brief,
                    topic=topic["title"],
                    focus_keyword=topic.get("keyword") or topic["title"],
                    target_audience=project.target_audience,
                )
                total_cost += cost

                title = _extract_h1(markdown) or topic["title"]
                word_count = len(markdown.split())

                item = ContentItem(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    org_id=org_id,
                    type="article",
                    title=title,
                    slug=_slugify(title),
                    body_markdown=markdown,
                    focus_keyword=topic.get("keyword"),
                    word_count=word_count,
                    status="draft",
                    ai_model_used="claude-sonnet-4-6",
                    generation_cost=cost,
                )
                db.add(item)

                # Generate social posts for this article
                try:
                    social_posts, social_cost = anthropic_client.generate_social_posts(
                        article_title=title,
                        article_markdown=markdown,
                        focus_keyword=topic.get("keyword") or title,
                    )
                    total_cost += social_cost
                    for platform, post_data in social_posts.items():
                        hashtags = " ".join(post_data.get("hashtags", []))
                        sp = SocialPost(
                            id=str(uuid.uuid4()),
                            content_id=item.id,
                            project_id=project_id,
                            org_id=org_id,
                            platform=platform,
                            body=post_data.get("body") or post_data.get("body", ""),
                            hashtags=hashtags[:500],
                            reddit_title=post_data.get("title") if platform == "reddit" else None,
                            status="draft",
                        )
                        db.add(sp)
                except Exception:
                    pass  # social post generation failure is non-fatal

                articles.append({"id": item.id, "title": title, "wordCount": word_count})

            except Exception as e:
                self.emit("content_generation", "running", f"Article {i+1} failed: {e}")

        db.commit()

        self.emit(
            "content_generation",
            "completed",
            f"Generated {len(articles)} article{'s' if len(articles) != 1 else ''}",
        )

        return {"articles_generated": len(articles), "articles": articles, "cost": total_cost}


def _parse_topics_from_brief(brief: str) -> list[dict]:
    topics: list[dict] = []
    in_section = False

    for line in brief.splitlines():
        lower = line.lower().strip()
        if "recommended article" in lower or ("article" in lower and "title" in lower):
            in_section = True
            continue
        if in_section and lower.startswith(("##", "**")):
            if "quick win" in lower or "intent" in lower or "cluster" in lower or "gap" in lower:
                break

        if in_section and line.strip():
            raw = re.sub(r"^[\d\.\-\*\s#]+", "", line).strip()
            raw = re.sub(r"\*+", "", raw).strip()
            if len(raw) > 15:
                topics.append({"title": raw, "keyword": raw.lower()})

    return topics[:3]


def _extract_h1(markdown: str) -> str | None:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug[:200]
