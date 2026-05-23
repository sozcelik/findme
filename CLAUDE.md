# CLAUDE.md

## Commands

```bash
# Start local infra (Postgres + Redis)
docker compose up -d

# Install JS deps
npm install

# Start Next.js dev server
cd apps/web && npm run dev      # http://localhost:3000

# Type-check all packages
npm run type-check

# Install Python deps (from services/api/)
cd services/api && uv sync

# Run migrations
cd services/api && alembic upgrade head

# Start FastAPI
cd services/api && uvicorn app.main:app --reload  # http://localhost:8000

# Start Celery worker
cd services/api && celery -A app.celery_app worker --loglevel=info

# Start Celery Beat (scheduled tasks)
cd services/api && celery -A app.celery_app beat --loglevel=info
```

## Architecture

findme is an AI-powered visibility SaaS. Seven specialized agents analyze SEO, generate content, publish to CMS, distribute to social platforms, and track visibility. A composite "Visibility Score" (0–100) surfaces the impact.

```
apps/web          — Next.js 15 App Router frontend (Vercel)
packages/types    — Shared TypeScript types
packages/api-contract — Zod schemas matching FastAPI shapes
services/api      — FastAPI + Celery + SQLAlchemy (Railway)
services/worker   — Celery worker Dockerfile (separate Railway deployment)
```

## Tech Stack

- **Frontend**: Next.js 15 App Router, Tailwind v4, shadcn/ui (base-nova), Supabase Auth
- **Backend**: FastAPI, SQLAlchemy 2.0 async, Alembic, Celery + celery-redbeat, Redis
- **Database**: Postgres + pgvector (Supabase)
- **LLM**: Claude Sonnet 4.6 (content gen) + Opus 4.7 (strategy)
- **SEO data**: DataForSEO
- **Image gen**: Flux via Replicate → Cloudflare R2

## Key Conventions

### Frontend
- **Server Components by default** — all page files are async server components
- `"use client"` only when `usePathname`, `useState`, or browser APIs needed (AppSidebar, AgentProgress)
- `apiClient` in `src/lib/api-client.ts` — typed fetch → FastAPI
- `useJobProgress` in `src/lib/use-job-progress.ts` — SSE hook for live pipeline progress
- Auth: Supabase SSR via `@supabase/ssr`, session cookies, middleware protects `/(app)` routes
- Tailwind v4: source scanning via `@source "../**/*.{tsx,ts,jsx,js}"` in globals.css — do not remove
- Fonts: `Syne` (display, `--font-display`), `Geist` (body, `--font-sans`), `Geist Mono` (`--font-mono`)

### Backend
- `ORG_ID = "org-dev-1"` hardcoded until Supabase JWT auth is wired up — replace with `request.state.org_id`
- Celery tasks use **sync** SQLAlchemy (`+psycopg2`) — FastAPI routers use **async** (`+asyncpg`)
- Progress emitted via Redis pub/sub → `job:progress:{job_id}` → SSE endpoint → `useJobProgress` hook
- Idempotent tasks: check `progress_steps` on retry to skip completed steps

### Model Routing
```python
FAST = "claude-sonnet-4-6"   # articles, FAQs, social posts
DEEP = "claude-opus-4-7"     # content strategy, visibility briefs
```

### Prompt Caching (Three Tiers)
1. **Project SEO brief** (2–4k tokens) — `cache_control: ephemeral` on system block, per project
2. **Content type templates** — static module-level constants, cached once per worker
3. **SERP data batches** — cached user message when analyzing 10+ results for a keyword cluster

## Database

Core tables: `organizations`, `users`, `projects`, `agent_jobs`
Full schema in `services/api/alembic/versions/001_initial.py`

Dev org seeded on `alembic upgrade head`: `id=org-dev-1`, plan=pro, 9999 credits.
