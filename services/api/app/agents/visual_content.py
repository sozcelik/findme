import asyncio
import uuid
from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.db.models.content_item import ContentItem
from app.db.models.visual_asset import VisualAsset


class VisualContentAgent(BaseAgent):
    def run(  # type: ignore[override]
        self,
        project_id: str,
        org_id: str,
        db: Session,
    ) -> dict:
        from app.services import replicate_client

        self.emit("visual_content", "running", "Generating hero images...")

        # Find content items without a featured image
        items = db.query(ContentItem).filter(
            ContentItem.project_id == project_id,
            ContentItem.featured_image_url.is_(None),
            ContentItem.status.in_(["draft", "review", "approved", "published"]),
        ).all()

        if not items:
            self.emit("visual_content", "completed", "All articles already have images")
            return {"generated": 0}

        total_cost = 0.0
        generated = 0

        for item in items[:5]:  # cap to 5 images per run
            self.emit("visual_content", "running", f"Generating image for: {item.title[:50]}...")

            prompt = _build_prompt(item)
            try:
                storage_url, cdn_url, cost = asyncio.run(
                    replicate_client.generate_image(prompt, width=1200, height=630)
                )
                total_cost += cost

                asset = VisualAsset(
                    id=str(uuid.uuid4()),
                    content_id=item.id,
                    org_id=org_id,
                    type="blog_hero",
                    prompt_used=prompt,
                    model_used="flux-dev",
                    storage_url=storage_url,
                    cdn_url=cdn_url,
                    alt_text=item.title,
                    generation_cost=cost,
                )
                db.add(asset)
                item.featured_image_url = cdn_url
                generated += 1

            except Exception as e:
                self.emit("visual_content", "running", f"Image failed for {item.id}: {e}")

        db.commit()

        self.emit(
            "visual_content",
            "completed",
            f"Generated {generated} image{'s' if generated != 1 else ''}",
        )

        return {"generated": generated, "cost": total_cost}


def _build_prompt(item: ContentItem) -> str:
    keyword = item.focus_keyword or ""
    title = item.title or "article"
    return (
        f"Professional blog hero image for an article titled '{title}'. "
        f"Topic: {keyword}. "
        "Clean, modern design, no text overlay, editorial photography style, "
        "soft lighting, high resolution, suitable for a business blog."
    )
