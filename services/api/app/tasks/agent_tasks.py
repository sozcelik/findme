import json
from datetime import datetime, timezone
from app.celery_app import celery_app


@celery_app.task(
    name="app.tasks.agent_tasks.run_full_pipeline",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def run_full_pipeline(self, job_id: str, project_id: str, org_id: str):
    import redis as sync_redis
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.config import settings
    from app.db.models.agent_job import AgentJob
    from app.db.models.project import Project
    from app.agents.seo_intelligence import SEOIntelligenceAgent
    from app.agents.content_generation import ContentGenerationAgent
    from app.services.visibility_score import calculate_partial_score

    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True)
    r = sync_redis.from_url(settings.redis_url)

    def set_progress(progress: int, db: Session):
        job = db.get(AgentJob, job_id)
        if job:
            job.progress = progress
            db.commit()

    with Session(engine) as db:
        job = db.get(AgentJob, job_id)
        if not job:
            return

        # Credit enforcement
        from app.db.models.org import Organization
        org = db.get(Organization, org_id)
        if org and org.credits_used_this_month >= org.monthly_credit_limit:
            job.status = "failed"
            job.error_message = "Monthly credit limit reached. Upgrade your plan to continue."
            db.commit()
            return

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        project = db.get(Project, project_id)
        if not project:
            job.status = "failed"
            job.error_message = "Project not found"
            db.commit()
            return

    try:
        # --- Step 1: SEO Analysis ---
        with Session(engine) as db:
            seo_agent = SEOIntelligenceAgent(job_id=job_id, redis_client=r)
            seo_output = seo_agent.run(
                project_id=project_id,
                org_id=org_id,
                db=db,
                project=db.get(Project, project_id),
            )
            set_progress(30, db)

        seo_brief = seo_output.get("seo_brief", "")

        # --- Step 2: Content Strategy (brief is the strategy output) ---
        r.publish(f"job:progress:{job_id}", json.dumps({
            "name": "content_strategy",
            "status": "completed",
            "message": f"Strategy ready — {seo_output.get('keywords_analyzed', 0)} keywords analysed",
            "startedAt": None,
            "completedAt": datetime.now(timezone.utc).isoformat(),
        }))

        with Session(engine) as db:
            set_progress(50, db)

        # --- Step 3: Content Generation ---
        if seo_brief and not seo_output.get("skipped"):
            with Session(engine) as db:
                content_agent = ContentGenerationAgent(job_id=job_id, redis_client=r)
                content_output = content_agent.run(
                    project_id=project_id,
                    org_id=org_id,
                    db=db,
                    project=db.get(Project, project_id),
                    seo_brief=seo_brief,
                )
                set_progress(80, db)
        else:
            content_output = {"articles_generated": 0, "articles": []}
            r.publish(f"job:progress:{job_id}", json.dumps({
                "name": "content_generation",
                "status": "completed",
                "message": "Skipped — no SEO brief",
                "startedAt": None,
                "completedAt": datetime.now(timezone.utc).isoformat(),
            }))

        # --- Step 4: Visibility Score ---
        r.publish(f"job:progress:{job_id}", json.dumps({
            "name": "visibility_score",
            "status": "running",
            "message": "Calculating visibility score...",
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "completedAt": None,
        }))

        with Session(engine) as db:
            project = db.get(Project, project_id)
            score = calculate_partial_score(project, db)
            project.visibility_score = score
            project.visibility_updated_at = datetime.now(timezone.utc)

            job = db.get(AgentJob, job_id)
            job.status = "completed"
            job.progress = 100
            job.completed_at = datetime.now(timezone.utc)
            job.credits_used = float(
                seo_output.get("cost", 0) + content_output.get("cost", 0)
            )
            job.output_data = {
                "seo_brief": seo_brief[:500] + "..." if len(seo_brief) > 500 else seo_brief,
                "keywords_analyzed": seo_output.get("keywords_analyzed", 0),
                "articles_generated": content_output.get("articles_generated", 0),
                "articles": content_output.get("articles", []),
                "visibility_score": score,
            }

            # Increment credit usage
            from app.db.models.org import Organization
            org = db.get(Organization, org_id)
            if org:
                org.credits_used_this_month += 1

            db.commit()

        r.publish(f"job:progress:{job_id}", json.dumps({
            "name": "visibility_score",
            "status": "completed",
            "message": f"Visibility score: {score}",
            "startedAt": None,
            "completedAt": datetime.now(timezone.utc).isoformat(),
        }))

    except Exception as exc:
        with Session(engine) as db:
            job = db.get(AgentJob, job_id)
            if job:
                job.status = "failed"
                job.error_message = str(exc)[:1000]
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 10)

    finally:
        r.close()
        engine.dispose()


@celery_app.task(
    name="app.tasks.agent_tasks.run_outreach_pipeline",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def run_outreach_pipeline(self, job_id: str, project_id: str, org_id: str):
    import redis as sync_redis
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.config import settings
    from app.db.models.agent_job import AgentJob
    from app.db.models.project import Project
    from app.agents.outreach import OutreachAgent
    from app.agents.ai_visibility import AIVisibilityAgent
    from app.agents.visual_content import VisualContentAgent

    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True)
    r = sync_redis.from_url(settings.redis_url)

    try:
        with Session(engine) as db:
            job = db.get(AgentJob, job_id)
            if not job:
                return
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            db.commit()

            project = db.get(Project, project_id)
            if not project:
                job.status = "failed"
                job.error_message = "Project not found"
                db.commit()
                return

            total_cost = 0.0

            # Step 1: Outreach
            outreach_agent = OutreachAgent(job_id=job_id, redis_client=r)
            outreach_output = outreach_agent.run(
                project_id=project_id, org_id=org_id, db=db, project=project
            )
            total_cost += outreach_output.get("cost", 0.0)

            # Step 2: AI Visibility evaluation
            ai_agent = AIVisibilityAgent(job_id=job_id, redis_client=r)
            ai_output = ai_agent.run(project_id=project_id, org_id=org_id, db=db)
            total_cost += ai_output.get("cost", 0.0)

            # Step 3: Visual content generation
            visual_agent = VisualContentAgent(job_id=job_id, redis_client=r)
            visual_output = visual_agent.run(project_id=project_id, org_id=org_id, db=db)
            total_cost += visual_output.get("cost", 0.0)

            job.status = "completed"
            job.progress = 100
            job.completed_at = datetime.now(timezone.utc)
            job.credits_used = total_cost
            job.output_data = {
                "opportunities_found": outreach_output.get("opportunities_found", 0),
                "ai_visibility_avg": ai_output.get("avg_score", 0.0),
                "images_generated": visual_output.get("generated", 0),
            }
            db.commit()

    except Exception as exc:
        with Session(engine) as db:
            job = db.get(AgentJob, job_id)
            if job:
                job.status = "failed"
                job.error_message = str(exc)[:1000]
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        raise self.retry(exc=exc, countdown=30)
    finally:
        r.close()
        engine.dispose()
