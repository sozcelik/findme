# Changelog

All notable changes to findme are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.3.0] — Phase 3: Full Visibility System — 2026-05-23

Complete implementation of the third and final MVP phase. All seven agents are now live, the Visibility Score uses all six dimensions, and campaigns can be scheduled via cron.

### Added — Backend

**New agents**

- `app/agents/outreach.py` — `OutreachAgent`: queries DataForSEO for backlink opportunities on competitor domains, then calls Claude Opus 4.7 to draft a personalized outreach email per domain. Stores results in `outreach_opportunities`.
- `app/agents/ai_visibility.py` — `AIVisibilityAgent`: runs a structured Claude Sonnet 4.6 rubric (direct answers, structure, FAQ coverage, entity clarity, factual depth) against each published article; stores 0–100 score in `content_items.ai_visibility_score`. Used by the visibility score engine for the AI Readability dimension.
- `app/agents/visual_content.py` — `VisualContentAgent`: generates blog hero images (1200×630 WebP) for articles that have no `featured_image_url`. Uses Flux via Replicate API (polling loop), uploads to Cloudflare R2 via boto3, stores metadata in `visual_assets`.

**New service**

- `app/services/replicate_client.py` — Flux image generation via Replicate predictions API. Polls until `succeeded`/`failed` (max 90s), downloads the WebP, uploads to R2 with permanent cache headers. Returns `(storage_url, cdn_url, cost_usd)`. Cost ≈ $0.055/image.

**Visibility score engine rewrite** (`app/services/visibility_score.py`)

- Replaced the Phase 1 two-dimension partial score with a full six-dimension engine:
  - **SEO Quality (30%)** — keyword coverage ratio, quick-win keyword count (difficulty < 30), volume data presence, content SEO scores
  - **AI Readability (20%)** — uses `content_items.ai_visibility_score` when available (set by `AIVisibilityAgent`); falls back to structural heuristics (H2/H3/FAQ/word count)
  - **Semantic Clarity (15%)** — proxy: published content count + keyword cluster diversity (full pgvector cosine similarity deferred to post-MVP)
  - **Social Amplification (15%)** — active platform count, 30-day posting frequency, engagement totals
  - **Authority Signals (15%)** — competitor domain authority data from DataForSEO; full own-domain DA deferred until backlink tracking matures
  - **Distribution Coverage (5%)** — active CMS connections + active social connections
- `calculate_full_score()` returns `(total_score, breakdown_dict)` and upserts a `visibility_scores` history row for today.
- `calculate_partial_score()` is now a thin wrapper that calls `calculate_full_score()` — backward-compatible with the pipeline task.

**New Celery tasks**

- `app/tasks/analytics_tasks.py`:
  - `daily_visibility_scores` — recalculates full score for all Pro+ projects; runs at **03:00 UTC** via celery-redbeat.
  - `daily_keyword_rankings` — re-fetches SERP positions for all keywords not checked in the last 23h; writes rows to `keyword_rankings`; runs at **04:00 UTC**.
  - `hourly_token_refresh` — refreshes OAuth access tokens expiring within 24h; runs every hour at **:30**. Currently handles Twitter PKCE refresh_token flow; LinkedIn tokens are 60-day and do not require refresh at this cadence.
- `app/tasks/campaign_tasks.py`:
  - `run_campaign` — campaign orchestrator task. Reads `campaigns` row, creates an `AgentJob`, enqueues `run_full_pipeline`, updates `last_run_at`/`next_run_at`.
  - `register_campaign_schedule(campaign_id, cron_expr)` — creates or updates a `RedBeatSchedulerEntry` so the campaign survives Railway redeploys.
  - `unregister_campaign_schedule(campaign_id)` — removes the entry from Redis when a campaign is paused or deleted.
- `app/tasks/agent_tasks.py` — added `run_outreach_pipeline` task: runs `OutreachAgent` → `AIVisibilityAgent` → `VisualContentAgent` in sequence, tracked under a single `AgentJob`.

**Updated Celery config** (`app/celery_app.py`)

- Added `analytics` task queue to routes.
- Registered three `beat_schedule` entries (`daily-visibility-scores`, `daily-keyword-rankings`, `hourly-token-refresh`).
- Expanded `include` list to cover all four task modules.

**New routers**

- `app/routers/analytics.py`
  - `GET /api/analytics/rankings?project_id=` — returns keyword + ranking rows ordered by date desc.
  - `GET /api/analytics/visibility?project_id=&days=30` — returns daily score history.
- `app/routers/outreach.py`
  - `GET /api/outreach?project_id=` — list opportunities (filterable by status).
  - `PATCH /api/outreach/{id}` — update status (`drafted → sent → replied`), contact email, or draft text. Sets `sent_at` automatically when status is set to `sent`.
  - `POST /api/outreach/run?project_id=` — triggers `run_outreach_pipeline` Celery task.
- `app/routers/campaigns.py`
  - Full CRUD for campaigns (`GET/POST /api/campaigns`, `GET/PATCH/DELETE /api/campaigns/{id}`).
  - `POST /api/campaigns/{id}/run` — runs the campaign immediately, independent of its schedule.
  - Creating a campaign with a `scheduleCron` automatically registers it with celery-redbeat.
  - `PATCH` with `status=paused` unregisters the redbeat entry.

**DataForSEO extension** (`app/services/dataforseo.py`)

- Added `fetch_backlink_opportunities(target_domain, limit)` — calls DataForSEO Backlinks Referring Domains Live API, returns domains ranked by domain authority.

**Anthropic client additions** (`app/services/anthropic_client.py`)

- `OUTREACH_TEMPLATE` — module-level cached system prompt for outreach email style (under 200 words, no placeholders, specific CTA).
- `AI_VISIBILITY_RUBRIC` — module-level cached rubric for the AI visibility evaluation; returns structured JSON `{score, suggestions}`.
- `generate_outreach_email(project_name, website_url, target_domain, domain_authority)` — Opus 4.7, returns `(email_text, cost_usd)`.
- `evaluate_ai_visibility(title, body_markdown, focus_keyword)` — Sonnet 4.6 with cached rubric, parses JSON response, returns `(score, suggestions, cost_usd)`.

**New DB models**

- `app/db/models/outreach_opportunity.py` — `OutreachOpportunity`: type, target_domain, contact_email, domain_authority, relevance_score, status, outreach_draft, sent_at, replied_at.
- `app/db/models/visual_asset.py` — `VisualAsset`: content_id, type (blog_hero/infographic/social_graphic/thumbnail), prompt_used, model_used, storage_url, cdn_url, alt_text, generation_cost.
- `app/db/models/visibility_score_history.py` — `VisibilityScoreHistory`: per-day score snapshot with all six dimension values + raw_inputs JSONB.
- `app/db/models/campaign.py` — `Campaign`: project_id, name, status, schedule_cron, target_keywords[], content_types[], publish_to_cms, distribute_social, last_run_at, next_run_at.
- `app/db/models/keyword_ranking.py` — `KeywordRanking`: keyword_id, project_id, checked_at (date), position, url_ranking, search_volume. Unique on (keyword_id, checked_at).

**Migration 004** (`alembic/versions/004_phase3.py`)

Creates: `outreach_opportunities`, `visual_assets`, `visibility_scores`, `campaigns`, `keyword_rankings` with all indexes and unique constraints.

**New dependencies** (`services/api/pyproject.toml`)

- `boto3>=1.35.0` — Cloudflare R2 uploads via S3-compatible API.
- `croniter>=3.0.0` — next-run-at calculation from cron expressions.

**Config** (`app/config.py`)

Added: `replicate_api_token`, `r2_account_id`, `r2_access_key_id`, `r2_secret_access_key`, `r2_bucket_name`, `r2_public_url`.

### Added — Frontend

- `apps/web/src/app/(app)/visibility/page.tsx` — Visibility Score breakdown page:
  - SVG donut gauge (inline, no chart library) showing total score with smooth transition.
  - Six dimension bars, each labeled with its percentage weight.
  - 30-day history table with all six dimension columns.
  - Inline SVG line chart (no external deps) plotting total score over time with Y-axis grid lines, dots per data point, and date labels every 7 days.
  - Accepts `?projectId=` query param.
- `apps/web/src/app/(app)/campaigns/page.tsx` — Campaign management page:
  - List view with status badges (running/completed/paused/draft), schedule cron, last/next run timestamps.
  - Create form with project selector, cron presets (daily/weekly/bi-weekly/monthly), CMS publish and social distribute toggles.
  - Run Now button triggers `POST /api/campaigns/{id}/run` immediately.
  - Pause/resume toggle calls `PATCH` with the new status.
  - Delete with confirmation calls `DELETE` and removes the redbeat schedule entry server-side.

---

## [0.2.0] — Phase 2: CMS, Social, Billing — 2026-05-23

### Added — Backend

**CMS integration layer**

- `app/integrations/cms/base.py` — `CMSAdapter` ABC with `CMSPublishPayload` / `CMSPublishResult` dataclasses and `from_config(cms_type, config)` factory.
- `app/integrations/cms/wordpress.py` — WordPress REST API v2 with Application Passwords. Basic Auth header, `POST /wp-json/wp/v2/posts`. Includes minimal markdown→HTML converter (no heavy deps).
- `app/integrations/cms/webflow.py` — Webflow CMS Items API v2 with Bearer token.
- `app/integrations/cms/shopify.py` — Shopify Blog Posts REST API with `X-Shopify-Access-Token`.

**Social integration layer**

- `app/integrations/social/base.py` — `SocialAdapter` ABC with `SocialPostPayload` / `SocialPostResult` / `SocialConnectionData` dataclasses and `from_platform()` factory.
- `app/integrations/social/linkedin.py` — LinkedIn OAuth2 UGC Posts API.
- `app/integrations/social/twitter.py` — Twitter/X OAuth2 PKCE `/2/tweets` POST.
- `app/integrations/social/reddit.py` — Draft-only; raises `NotImplementedError` for actual posting (Reddit ToS).

**Credential encryption** (`app/services/vault.py`)

- Fernet (AES-128-CBC + HMAC) encryption for CMS configs and OAuth tokens stored in the database.
- Key from `ENCRYPTION_KEY` env var; falls back to a SHA-256 derivation of `SUPABASE_JWT_SECRET` in dev.
- Production target: replace with Supabase Vault for secret isolation outside the main DB.
- Rule: **never return decrypted credentials in API responses**.

**Stripe billing** (`app/services/stripe_service.py`)

- `create_checkout_session()` — creates Stripe Checkout session, attaches `org_id` to metadata.
- `create_billing_portal()` — creates Stripe Customer Portal session.
- `handle_webhook()` — verifies Stripe signature, returns parsed event dict for `checkout.session.completed`, `customer.subscription.updated/created/deleted`.
- `PLAN_CREDITS` map: free=5, growth=50, pro=200.

**Social post generation** (`app/services/anthropic_client.py`)

- `SOCIAL_TEMPLATE` — cached system prompt covering LinkedIn (150–300 words, professional), Twitter (max 270 chars, punchy), Reddit (conversational, no self-promo).
- `generate_social_posts(article_title, article_markdown, focus_keyword)` — Sonnet 4.6, returns `{linkedin, twitter, reddit}` JSON with body + hashtags. Parses markdown code fence if present.

**Content Generation Agent update** (`app/agents/content_generation.py`)

- After each article, calls `generate_social_posts()` and saves three `SocialPost` records (LinkedIn, Twitter, Reddit draft). Failure is non-fatal — article save is not rolled back.

**Publish tasks** (`app/tasks/publish_tasks.py`)

- `publish_to_cms` — Celery task (3 retries, exponential backoff). Decrypts CMS config, instantiates the correct adapter, calls `publish()` or `update()` depending on whether a published `PublishRecord` already exists. Sets `content_items.status = "published"`.
- `post_to_social` — Celery task (3 retries). Decrypts access token, instantiates adapter, calls `post()`. Marks `SocialPost.status = "draft_only"` for Reddit without raising.

**New routers**

- `app/routers/integrations.py` — CMS connection CRUD, `GET /test`, social connection list/delete, LinkedIn OAuth2 flow, Twitter OAuth2 PKCE flow. Stores PKCE state/verifier in-memory dict (production: move to Redis with TTL).
- `app/routers/billing.py` — subscription status, checkout, billing portal, Stripe webhook with signature verification.
- `app/routers/content.py` additions — `POST /{id}/publish` (queues `publish_to_cms`), `POST /{id}/distribute` (queues `post_to_social`), `GET /{id}/social-posts`.

**Credit enforcement** (`app/tasks/agent_tasks.py`)

- Before starting `run_full_pipeline`: checks `org.credits_used_this_month >= org.monthly_credit_limit`; fails the job with a clear error message instead of running.
- After successful completion: increments `org.credits_used_this_month` by 1.

**New DB models**

- `app/db/models/cms_connection.py` — `CmsConnection`: type, name, config_encrypted (JSONB, values Fernet-encrypted), status, last_tested_at, last_error.
- `app/db/models/social_connection.py` — `SocialConnection`: platform, account_name/id, access_token_encrypted, refresh_token_encrypted, token_expires_at, scopes, status.
- `app/db/models/publish_record.py` — `PublishRecord`: content_id, cms_connection_id, external_id, external_url, status (pending/published/failed/updated), error_message, published_at.
- `app/db/models/social_post.py` — `SocialPost`: platform, body, hashtags (space-separated), reddit_title, status (draft/scheduled/posted/failed), posted_at, external_post_id, engagement (JSONB).

**Migration 003** (`alembic/versions/003_integrations_billing.py`)

Creates: `cms_connections`, `social_connections`, `publish_records`, `social_posts`.

**New dependencies**

- `stripe>=11.0.0`, `cryptography>=43.0.0` (Fernet).

**Config additions** — Stripe price IDs, LinkedIn client ID/secret, Twitter client ID/secret, `ENCRYPTION_KEY`.

### Added — Frontend

- `apps/web/src/app/(app)/settings/layout.tsx` — settings tab navigation (Integrations / Billing).
- `apps/web/src/app/(app)/settings/integrations/page.tsx` — CMS connection form (type-specific field sets for WordPress/Webflow/Shopify), test-connection button, status badge, social OAuth connect/disconnect buttons, Reddit "draft only" notice.
- `apps/web/src/app/(app)/settings/billing/page.tsx` — current plan display, credit usage bar (turns destructive at 90%), upgrade plan cards, Stripe Customer Portal redirect.
- `apps/web/src/app/(app)/content/[id]/page.tsx` — redesigned as 2/3 + 1/3 grid. Sidebar adds: CMS connection selector + Publish button (queues task), social posts panel per platform with Post/Connect actions and status badges.

---

## [0.1.0] — Phase 1: SEO Pipeline + Content Generation — 2026-05-23

### Added — Backend

**DataForSEO client** (`app/services/dataforseo.py`)

- `fetch_serp(keyword)` — Google Organic SERP via DataForSEO Live API, returns top-10 organic results + featured snippet.
- `fetch_keyword_data(keywords[])` — Google Ads search volume, CPC, keyword difficulty via Keywords Data Live API.

**Anthropic client** (`app/services/anthropic_client.py`)

- Three-tier prompt caching strategy:
  - **Tier 1 (project SEO brief)** — `cache_control: ephemeral` on system block, cached per project run.
  - **Tier 2 (content template)** — `ARTICLE_TEMPLATE` module-level constant, cached once per worker at import time.
  - **Tier 3 (SERP data batch)** — SERP context in cached user message, avoids re-tokenizing large context per call.
- `generate_seo_brief()` — Claude Opus 4.7, cached SERP data → comprehensive brief (keyword clusters, competitor gaps, 5 article recommendations, quick wins, intent map).
- `generate_article()` — Claude Sonnet 4.6, two cached system blocks (template + project brief) → full markdown article (H1, 4–6 H2s with H3s, FAQ, CTA). Cost ≈ $0.008/article with cache hits.

**SEO Intelligence Agent** (`app/agents/seo_intelligence.py`)

- Loads project keywords from DB.
- Calls `fetch_serp()` + `fetch_keyword_data()` concurrently via `asyncio.run()`.
- Upserts `Competitor` records from SERP domain frequency.
- Calls `generate_seo_brief()` with keyword + SERP context.

**Content Generation Agent** (`app/agents/content_generation.py`)

- Parses "Recommended Articles" section from SEO brief using regex.
- Generates up to 3 articles per run with `generate_article()`.
- Saves `ContentItem` records (type=article, status=draft, ai_model_used, generation_cost).

**Pipeline task** (`app/tasks/agent_tasks.py`)

- `run_full_pipeline` — Celery task (3 retries). Runs SEO Intelligence → Content Generation → `calculate_partial_score` → updates `project.visibility_score`. Emits Redis pub/sub progress between steps.

**SSE streaming** (`app/routers/agents.py`)

- `POST /api/projects/{id}/run-pipeline` — creates `AgentJob`, enqueues Celery task, returns `{job_id}` immediately.
- `GET /api/jobs/{id}/stream` — FastAPI `StreamingResponse` subscribed to `job:progress:{job_id}` Redis channel.
- `GET /api/jobs/{id}` — job status + output_data.

**Partial visibility score** (`app/services/visibility_score.py`)

- Phase 1 implementation using SEO Quality (30%) + AI Readability (20%) only. Normalized to 0–100 across those two dimensions until the full engine was added in Phase 3.

**Migration 002** (`alembic/versions/002_keywords_content.py`)

Creates: `keywords`, `serp_results`, `competitors`, `content_items`, `content_versions`.

### Added — Frontend

- `apps/web/src/lib/use-job-progress.ts` — `useJobProgress(jobId)` hook: opens `EventSource` to SSE endpoint, merges steps by name into state array.
- `apps/web/src/components/AgentProgress.tsx` — renders progress step list with icons (CheckCircle2 / Loader2 / XCircle / Circle), progress bar.
- `apps/web/src/components/VisibilityScore.tsx` — displays composite score with six dimension bars and weights.
- `apps/web/src/components/PipelineButton.tsx` — "Run Pipeline" button: POSTs to trigger endpoint, creates optimistic job record, connects `useJobProgress` for live updates.
- `apps/web/src/app/(app)/projects/[id]/keywords/page.tsx` — bulk keyword input (one per line), keyword table (volume/difficulty/CPC), per-row delete.
- `apps/web/src/app/(app)/content/[id]/page.tsx` — markdown textarea editor, status dropdown, word count, generation cost display, save button.

---

## [0.0.1] — Phase 0: Monorepo Infrastructure — 2026-05-23

### Added

**Monorepo**

- Turborepo + npm workspaces (`apps/*`, `packages/*`).
- Python uv workspace root with `services/api` as the only member.
- `docker-compose.yml` — Postgres 16 with pgvector extension + Redis 7, both with healthchecks.
- `tsconfig.base.json` — strict TypeScript base config shared across packages.
- `.env.example` — template for all required environment variables.

**Shared packages**

- `packages/types/src/index.ts` — TypeScript domain types: `Org`, `User`, `Project`, `Keyword`, `ContentItem` (with `ContentType` / `ContentStatus` enums), `AgentJob` (with `JobType` / `JobStatus`), `ProgressStep`, `VisibilityScore`, `NavItem`.
- `packages/api-contract/src/index.ts` — Zod schemas: `CreateProjectSchema`, `RunPipelineSchema`, `ProgressStepSchema`, `AgentJobSchema`.

**Next.js app skeleton** (`apps/web`)

- Next.js 15 App Router, Tailwind v4 (CSS-first, `@source` directive), shadcn/ui base-nova style.
- `globals.css` — indigo-slate color palette (`--primary: oklch(0.558 0.212 264)`), Syne (display) + Geist (body) + Geist Mono fonts.
- Supabase SSR auth: `src/lib/auth.ts`, `src/middleware.ts` protecting `/(app)` routes, `auth/callback/route.ts`.
- `src/lib/api-client.ts` — typed fetch wrapper pointing to FastAPI.
- `AppSidebar`, `TopNav`, `(app)/layout.tsx` — main authenticated shell.
- `(app)/dashboard/page.tsx`, `(app)/projects/page.tsx`, `(app)/projects/[id]/page.tsx` — initial project views.

**FastAPI skeleton** (`services/api`)

- pydantic-settings config reading `.env`.
- SQLAlchemy 2.0 async session factory (`+asyncpg`).
- `GET /health` endpoint.
- `app/db/base.py` — declarative base.
- `app/agents/base.py` — `BaseAgent` ABC with `emit(step_name, status, message)` publishing to `job:progress:{job_id}` Redis channel.
- `app/celery_app.py` — Celery + celery-redbeat config, `worker_max_tasks_per_child=50`.

**Migration 001** (`alembic/versions/001_initial.py`)

Creates: `organizations`, `users`, `projects`, `agent_jobs`. Seeds dev org (`id=org-dev-1`, plan=pro, 9999 credits).
