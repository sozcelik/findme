import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Competitor(Base):
    __tablename__ = "competitors"
    __table_args__ = (
        UniqueConstraint("project_id", "domain", name="uq_competitors_project_domain"),
        Index("ix_competitors_project_id", "project_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    domain_authority: Mapped[int | None] = mapped_column(Integer)
    backlinks_count: Mapped[int | None] = mapped_column(Integer)
    traffic_estimate: Mapped[int | None] = mapped_column(Integer)
    top_keywords: Mapped[dict | None] = mapped_column(JSONB)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
