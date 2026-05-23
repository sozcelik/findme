import uuid
from datetime import date, datetime
from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class VisibilityScoreHistory(Base):
    __tablename__ = "visibility_scores"
    __table_args__ = (
        UniqueConstraint("project_id", "score_date", name="uq_visibility_scores_project_date"),
        Index("ix_visibility_scores_project_id", "project_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    score_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    seo_quality: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    ai_readability: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    semantic_clarity: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    social_amplification: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    authority_signals: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    distribution_coverage: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    raw_inputs: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
