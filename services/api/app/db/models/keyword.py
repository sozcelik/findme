import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Keyword(Base):
    __tablename__ = "keywords"
    __table_args__ = (
        UniqueConstraint("project_id", "keyword", name="uq_keywords_project_keyword"),
        Index("ix_keywords_project_id", "project_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    search_volume: Mapped[int | None] = mapped_column(Integer)
    cpc: Mapped[float | None] = mapped_column(Float)
    keyword_difficulty: Mapped[int | None] = mapped_column(Integer)
    search_intent: Mapped[str | None] = mapped_column(String(30))
    current_position: Mapped[int | None] = mapped_column(Integer)
    best_position: Mapped[int | None] = mapped_column(Integer)
    serp_features: Mapped[dict | None] = mapped_column(JSONB)
    last_analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
