import asyncio
import uuid
from sqlalchemy.orm import Session
from app.agents.base import BaseAgent
from app.db.models.outreach_opportunity import OutreachOpportunity
from app.db.models.competitor import Competitor


class OutreachAgent(BaseAgent):
    def run(  # type: ignore[override]
        self,
        project_id: str,
        org_id: str,
        db: Session,
        project,
    ) -> dict:
        from app.services import dataforseo, anthropic_client

        self.emit("outreach", "running", "Finding backlink opportunities...")

        # Gather competitor domains from DB
        competitors = db.query(Competitor).filter(Competitor.project_id == project_id).all()
        target_domains = [c.domain for c in competitors[:5]]

        if not target_domains and project.website_url:
            # Fall back to the project's own domain
            from urllib.parse import urlparse
            parsed = urlparse(project.website_url)
            target_domains = [parsed.netloc or project.website_url]

        if not target_domains:
            self.emit("outreach", "completed", "No competitor domains to analyze")
            return {"opportunities_found": 0, "opportunities": []}

        opportunities_raw = []
        for domain in target_domains[:3]:
            try:
                opps = asyncio.run(dataforseo.fetch_backlink_opportunities(domain, limit=10))
                opportunities_raw.extend(opps)
            except Exception:
                pass

        if not opportunities_raw:
            self.emit("outreach", "completed", "No backlink opportunities found")
            return {"opportunities_found": 0, "opportunities": []}

        # Deduplicate by domain
        seen: set[str] = set()
        unique_opps = []
        for opp in opportunities_raw:
            if opp["domain"] not in seen:
                seen.add(opp["domain"])
                unique_opps.append(opp)

        self.emit("outreach", "running", f"Drafting outreach emails for {len(unique_opps)} domains...")

        total_cost = 0.0
        saved = []

        for opp_data in unique_opps[:10]:
            try:
                draft, cost = anthropic_client.generate_outreach_email(
                    project_name=project.name,
                    website_url=project.website_url or "",
                    target_domain=opp_data["domain"],
                    domain_authority=opp_data.get("domain_rank") or 0,
                )
                total_cost += cost

                record = OutreachOpportunity(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    org_id=org_id,
                    type="backlink",
                    target_domain=opp_data["domain"],
                    domain_authority=opp_data.get("domain_rank"),
                    relevance_score=None,
                    status="drafted",
                    outreach_draft=draft,
                )
                db.add(record)
                saved.append({"domain": opp_data["domain"], "id": record.id})

            except Exception as e:
                self.emit("outreach", "running", f"Skipped {opp_data['domain']}: {e}")

        db.commit()

        self.emit(
            "outreach",
            "completed",
            f"Drafted {len(saved)} outreach email{'s' if len(saved) != 1 else ''}",
        )

        return {"opportunities_found": len(saved), "opportunities": saved, "cost": total_cost}
