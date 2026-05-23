import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (Index("ix_campaigns_project_id", "project_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="draft"
    )  # draft|running|completed|paused
    schedule_cron: Mapped[str | None] = mapped_column(String(100))  # e.g. "0 3 * * 1" (Mon 03:00)
    target_keywords: Mapped[list | None] = mapped_column(ARRAY(String))
    content_types: Mapped[list | None] = mapped_column(ARRAY(String))
    publish_to_cms: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    distribute_social: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
