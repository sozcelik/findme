# findme

AI-powered visibility SaaS that helps businesses become more discoverable across Google Search, AI search engines (ChatGPT, Perplexity), social platforms, and via backlinks. Seven specialized agents run in orchestrated pipelines to analyze competitors, generate content, publish to CMS, distribute to social, and track a composite **Visibility Score** (0–100).

---

## Architecture

```
findme/
├── apps/web/               Next.js 15 App Router (Vercel)
├── packages/types/         Shared TypeScript types
├── packages/api-contract/  Zod schemas matching FastAPI shapes
└── services/api/           FastAPI + Celery + SQLAlchemy (Railway)
```

**Frontend** — Next.js 15 App Router, Tailwind v4, shadcn/ui (base-nova), Supabase SSR Auth  
**Backend** — FastAPI, SQLAlchemy 2.0 async (+asyncpg), Alembic, Celery + celery-redbeat, Redis  
**Database** — Postgres + pgvector (Supabase)  
**LLM** — Claude Sonnet 4.6 (content gen, social posts, AI visibility eval) · Claude Opus 4.7 (strategy, outreach)  
**SEO data** — DataForSEO (SERP, keyword volume, backlinks)  
**Image gen** — Flux via Replicate → Cloudflare R2  
**Billing** — Stripe (checkout, billing portal, webhook)

---

## Quick Start

```bash
# 1. Infrastructure
docker compose up -d          # Postgres (pgvector) + Redis

# 2. Backend
cd services/api
uv sync
alembic upgrade head          # runs all 4 migrations
uvicorn app.main:app --reload # http://localhost:8000

# 3. Celery worker (separate terminal)
celery -A app.celery_app worker --loglevel=info

# 4. Celery Beat — cron jobs (separate terminal)
celery -A app.celery_app beat --loglevel=info

# 5. Frontend
npm install
cd apps/web && npm run dev    # http://localhost:3000
```

Copy `.env.example` to `.env` and fill in your keys before starting.

---

## Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://…` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `SUPABASE_URL` / `SUPABASE_JWT_SECRET` | Supabase project |
| `ANTHROPIC_API_KEY` | Claude API |
| `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD` | DataForSEO API |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | Stripe |
| `STRIPE_GROWTH_PRICE_ID` / `STRIPE_PRO_PRICE_ID` | Stripe price IDs |
| `LINKEDIN_CLIENT_ID` / `LINKEDIN_CLIENT_SECRET` | LinkedIn OAuth2 |
| `TWITTER_CLIENT_ID` / `TWITTER_CLIENT_SECRET` | Twitter OAuth2 PKCE |
| `ENCRYPTION_KEY` | Fernet key for credential encryption (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) |
| `REPLICATE_API_TOKEN` | Replicate (Flux image gen) |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET_NAME` | Cloudflare R2 |

---

## Agent System

Seven agents, each a `BaseAgent` subclass that emits progress via Redis pub/sub → SSE.

| Agent | Model | What it does |
|---|---|---|
| `SEOIntelligenceAgent` | Opus 4.7 | Fetches SERP data via DataForSEO, generates SEO brief |
| `ContentGenerationAgent` | Sonnet 4.6 | Generates articles + social post drafts from SEO brief |
| `OutreachAgent` | Opus 4.7 | Finds backlink opportunities, drafts personalized outreach emails |
| `AIVisibilityAgent` | Sonnet 4.6 | Scores content on AI search citation likelihood (0–100 rubric) |
| `VisualContentAgent` | Flux (Replicate) | Generates blog hero images, uploads to R2 |
| `CMSPublisher` | — | Publishes content to WordPress / Webflow / Shopify via adapters |
| `SocialDistribution` | — | Posts to LinkedIn / Twitter via OAuth2 connections |

### Pipeline Flow

```
POST /api/projects/{id}/run-pipeline
  → AgentJob created (status=queued)
  → run_full_pipeline.delay(job_id)

Worker:
  SEOIntelligenceAgent  →  ContentGenerationAgent  →  VisibilityScore
  (+ OutreachAgent, AIVisibilityAgent, VisualContentAgent via run-outreach-pipeline)

Progress: Redis pub/sub → SSE /api/jobs/{id}/stream → useJobProgress hook → AgentProgress component
```

---

## Visibility Score

Composite 0–100 score updated after every pipeline run and daily at 03:00 UTC for Pro+ projects.

| Dimension | Weight | Data Sources |
|---|---|---|
| SEO Quality | 30% | Keyword coverage, difficulty, volume data, content SEO scores |
| AI Readability | 20% | H2/H3 density, FAQ presence, word count, Claude rubric score |
| Semantic Clarity | 15% | Published content count, keyword cluster diversity |
| Social Amplification | 15% | Active platforms, posting frequency, engagement |
| Authority Signals | 15% | Competitor domain authority data, backlink tracking |
| Distribution Coverage | 5% | Active CMS connections, active social connections |

History stored in `visibility_scores` table (one row per project per day). Accessible at `/visibility?projectId=…`.

---

## Database

Migrations in `services/api/alembic/versions/`:

| Migration | Tables |
|---|---|
| `001_initial` | `organizations`, `users`, `projects`, `agent_jobs` |
| `002_keywords_content` | `keywords`, `serp_results`, `competitors`, `content_items`, `content_versions` |
| `003_integrations_billing` | `cms_connections`, `social_connections`, `publish_records`, `social_posts` |
| `004_phase3` | `outreach_opportunities`, `visual_assets`, `visibility_scores`, `campaigns`, `keyword_rankings` |

Dev org seeded on `alembic upgrade head`: `id=org-dev-1`, plan=pro, 9999 credits.

---

## API Routes

```
# Projects & keywords
GET/POST       /api/projects
GET/PATCH      /api/projects/{id}
GET/POST       /api/projects/{id}/keywords
POST           /api/projects/{id}/run-pipeline

# Jobs & streaming
GET            /api/jobs/{id}
GET            /api/jobs/{id}/stream          SSE

# Content
GET            /api/content
GET/PATCH      /api/content/{id}
POST           /api/content/{id}/publish       → queues publish_to_cms task
POST           /api/content/{id}/distribute    → queues post_to_social task
GET            /api/content/{id}/social-posts

# Integrations
GET/POST/DELETE /api/integrations/cms
GET             /api/integrations/cms/{id}/test
GET/DELETE      /api/integrations/social
GET             /api/integrations/social/{platform}/oauth-url
POST            /api/integrations/social/callback

# Analytics
GET            /api/analytics/rankings?project_id=…
GET            /api/analytics/visibility?project_id=…&days=30

# Outreach
GET            /api/outreach?project_id=…
PATCH          /api/outreach/{id}
POST           /api/outreach/run?project_id=…

# Campaigns
GET/POST       /api/campaigns
GET/PATCH/DELETE /api/campaigns/{id}
POST           /api/campaigns/{id}/run

# Billing
GET            /api/billing/subscription
POST           /api/billing/create-checkout
POST           /api/billing/portal
POST           /api/billing/webhook
```

---

## Prompt Caching (3 tiers)

| Tier | What | How |
|---|---|---|
| 1 | Project SEO brief (2–4k tokens) | `cache_control: ephemeral` on system block, per project |
| 2 | Content type templates | Module-level constants, cached at worker import time |
| 3 | SERP data batches | Cached user message when analyzing 10+ keyword results |

Cost at Sonnet 4.6 with cache hits ≈ $0.008/article. Opus 4.7 called only for strategy + outreach (5–15 calls/run).

---

## CMS Adapters

| CMS | Auth | API |
|---|---|---|
| WordPress | Basic Auth (Application Passwords) | WP REST API v2 `/wp-json/wp/v2/posts` |
| Webflow | Bearer token | CMS Items API v2 |
| Shopify | `X-Shopify-Access-Token` | Blog Posts REST API |

All implement `CMSAdapter` ABC (`test_connection`, `publish`, `update`). Factory: `CMSAdapter.from_config(type, config)`.

---

## Social Adapters

| Platform | Auth | Notes |
|---|---|---|
| LinkedIn | OAuth2 (`w_member_social`) | UGC Posts API |
| Twitter/X | OAuth2 PKCE (`tweet.write`) | `/2/tweets` POST |
| Reddit | Draft only | ToS prohibits automated posting; UI surfaces draft for manual post |

Tokens encrypted at rest via Fernet (`app/services/vault.py`). Hourly cron refreshes tokens expiring within 24h.

---

## Scheduled Tasks (celery-redbeat)

| Task | Schedule | Description |
|---|---|---|
| `daily_visibility_scores` | 03:00 UTC | Recalculates full 6-dimension score for all Pro+ projects |
| `daily_keyword_rankings` | 04:00 UTC | Checks current SERP positions for all keywords |
| `hourly_token_refresh` | :30 every hour | Refreshes OAuth tokens expiring within 24h |
| `run_campaign` | Per-campaign cron | Triggers full pipeline for scheduled campaigns |

---

## Subscription Plans

| Plan | Price | Pipeline runs/mo | CMS | Social |
|---|---|---|---|---|
| Free/Starter | — | 5 | — | — |
| Growth | $49/mo | 50 | 2 | 3 |
| Pro | $149/mo | 200 | Unlimited | Unlimited |

Credit limit enforced in `run_full_pipeline` before starting. Stripe webhooks update plan + limits in `organizations` table.

---

## Credential Security

CMS and social credentials are encrypted with Fernet (AES-128-CBC + HMAC) before storing in the database. The key is read from `ENCRYPTION_KEY`; if unset, it is derived from `SUPABASE_JWT_SECRET` (dev only).

**Never return decrypted credentials in API responses.** In production, replace with Supabase Vault for proper secret isolation outside the main database.

---

## Key Conventions

- `ORG_ID = "org-dev-1"` hardcoded in all routers until Supabase JWT auth is wired. Replace with `request.state.org_id`.
- Celery tasks use **sync** SQLAlchemy (`+psycopg2`). FastAPI routers use **async** (`+asyncpg`).
- Server Components by default in Next.js. `"use client"` only for hooks (`useState`, `usePathname`, `EventSource`).
- Tailwind v4 source scanning via `@source "../**/*.{tsx,ts,jsx,js}"` in `globals.css` — do not remove.
- Model routing: `claude-sonnet-4-6` for fast tasks, `claude-opus-4-7` for strategy and reasoning.
