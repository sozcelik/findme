from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.db.models.content_item import ContentItem


class AIVisibilityAgent(BaseAgent):
    def run(  # type: ignore[override]
        self,
        project_id: str,
        org_id: str,
        db: Session,
    ) -> dict:
        from app.services import anthropic_client

        self.emit("ai_visibility", "running", "Evaluating content for AI search visibility...")

        items = db.query(ContentItem).filter(
            ContentItem.project_id == project_id,
            ContentItem.status.in_(["published", "approved", "review"]),
        ).all()

        if not items:
            self.emit("ai_visibility", "completed", "No published content to evaluate")
            return {"evaluated": 0, "avg_score": 0.0}

        total_cost = 0.0
        scores = []

        for i, item in enumerate(items[:10]):  # cap at 10 per run
            if not item.body_markdown:
                continue

            self.emit(
                "ai_visibility",
                "running",
                f"Evaluating {i+1}/{min(len(items), 10)}: {item.title[:50]}...",
            )

            try:
                score, suggestions, cost = anthropic_client.evaluate_ai_visibility(
                    title=item.title or "",
                    body_markdown=item.body_markdown,
                    focus_keyword=item.focus_keyword or "",
                )
                total_cost += cost
                item.ai_visibility_score = score
                scores.append(score)
            except Exception as e:
                self.emit("ai_visibility", "running", f"Skipped {item.id}: {e}")

        db.commit()

        avg = round(sum(scores) / len(scores), 1) if scores else 0.0
        self.emit(
            "ai_visibility",
            "completed",
            f"Evaluated {len(scores)} items — avg AI visibility: {avg}",
        )

        return {"evaluated": len(scores), "avg_score": avg, "cost": total_cost}
