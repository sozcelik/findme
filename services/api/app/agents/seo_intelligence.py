import asyncio
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.db.models.keyword import Keyword
from app.db.models.competitor import Competitor


class SEOIntelligenceAgent(BaseAgent):
    def run(self, project_id: str, org_id: str, db: Session, project) -> dict:  # type: ignore[override]
        from app.services import dataforseo, anthropic_client

        self.emit("seo_analysis", "running", "Loading keywords...")

        keywords = db.query(Keyword).filter(
            Keyword.project_id == project_id,
            Keyword.org_id == org_id,
        ).all()

        if not keywords:
            self.emit("seo_analysis", "completed", "No keywords to analyze — add keywords first")
            return {"skipped": True, "reason": "no_keywords", "seo_brief": ""}

        kw_texts = [kw.keyword for kw in keywords[:10]]
        self.emit("seo_analysis", "running", f"Fetching SERP data for {len(kw_texts)} keywords...")

        # Fetch SERP for each keyword
        serp_map: dict[str, dict] = {}
        for kw_text in kw_texts:
            try:
                serp_map[kw_text] = asyncio.run(
                    dataforseo.fetch_serp(kw_text, language_code=project.language or "en")
                )
            except Exception as e:
                serp_map[kw_text] = {"keyword": kw_text, "organic_results": [], "error": str(e)}

        # Fetch volume / difficulty data
        try:
            kw_data_list = asyncio.run(
                dataforseo.fetch_keyword_data(kw_texts, language_code=project.language or "en")
            )
            kw_data_map = {item["keyword"]: item for item in kw_data_list}
        except Exception:
            kw_data_map = {}

        # Update keyword rows + collect competitor domains
        competitor_counts: dict[str, int] = {}
        keywords_with_serp: list[dict] = []
        project_domain = _domain(project.website_url)

        for kw in keywords[:10]:
            serp = serp_map.get(kw.keyword, {})
            data = kw_data_map.get(kw.keyword, {})

            kw.search_volume = data.get("search_volume")
            kw.cpc = data.get("cpc")
            kw.keyword_difficulty = data.get("keyword_difficulty")
            kw.last_analyzed_at = datetime.now(timezone.utc)

            for result in serp.get("organic_results", []):
                domain = result.get("domain", "")
                if domain and domain != project_domain:
                    competitor_counts[domain] = competitor_counts.get(domain, 0) + 1

            keywords_with_serp.append({
                "keyword": kw.keyword,
                "search_volume": kw.search_volume,
                "keyword_difficulty": kw.keyword_difficulty,
                "serp_results": serp.get("organic_results", []),
            })

        db.commit()

        # Upsert top 5 competitors
        for domain, _ in sorted(competitor_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            exists = db.query(Competitor).filter(
                Competitor.project_id == project_id,
                Competitor.domain == domain,
            ).first()
            if not exists:
                db.add(Competitor(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    org_id=org_id,
                    domain=domain,
                    last_analyzed_at=datetime.now(timezone.utc),
                ))
        db.commit()

        self.emit("seo_analysis", "running", "Generating SEO brief with Claude Opus 4.7...")

        try:
            brief, cost = anthropic_client.generate_seo_brief(
                project_name=project.name,
                website_url=project.website_url,
                business_description=project.business_description or "",
                keywords_with_serp=keywords_with_serp,
            )
        except Exception as e:
            brief = f"[SEO brief generation failed: {e}]"
            cost = 0.0

        # Parse suggested article topics from the brief
        from app.agents.content_generation import _parse_topics_from_brief
        suggested_topics = _parse_topics_from_brief(brief)

        self.emit(
            "seo_analysis",
            "completed",
            f"Brief ready — {len(keywords_with_serp)} keywords, {len(competitor_counts)} competitors",
        )

        return {
            "seo_brief": brief,
            "suggested_topics": suggested_topics,
            "keywords_analyzed": len(keywords_with_serp),
            "competitors_found": len(competitor_counts),
            "keywords_summary": [
                {
                    "keyword": kw["keyword"],
                    "search_volume": kw.get("search_volume"),
                    "keyword_difficulty": kw.get("keyword_difficulty"),
                }
                for kw in keywords_with_serp
            ],
            "top_competitors": sorted(competitor_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "cost": cost,
        }


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""
