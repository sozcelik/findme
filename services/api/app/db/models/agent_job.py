import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AgentJob(Base):
    __tablename__ = "agent_jobs"
    __table_args__ = (
        Index("ix_agent_jobs_org_id", "org_id"),
        Index("ix_agent_jobs_project_id", "project_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    campaign_id: Mapped[str | None] = mapped_column(String)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="queued")
    triggered_by: Mapped[str | None] = mapped_column(String)
    celery_task_id: Mapped[str | None] = mapped_column(String(255))
    input_data: Mapped[dict | None] = mapped_column(JSONB)
    output_data: Mapped[dict | None] = mapped_column(JSONB)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    progress_steps: Mapped[list | None] = mapped_column(JSONB, server_default="[]")
    error_message: Mapped[str | None] = mapped_column(String)
    credits_used: Mapped[float | None] = mapped_column(Float)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
