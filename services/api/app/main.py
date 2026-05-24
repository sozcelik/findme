from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import health, projects, agents, keywords, content, integrations, billing, analytics, outreach, campaigns, audit, citation


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="findme API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(keywords.router, prefix="/api/projects", tags=["keywords"])
app.include_router(agents.router, prefix="/api", tags=["agents"])
app.include_router(content.router, prefix="/api/content", tags=["content"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["integrations"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(outreach.router, prefix="/api/outreach", tags=["outreach"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["campaigns"])
app.include_router(citation.router, prefix="/api", tags=["citation"])
