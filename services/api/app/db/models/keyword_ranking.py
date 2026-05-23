import uuid
from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class KeywordRanking(Base):
    __tablename__ = "keyword_rankings"
    __table_args__ = (
        UniqueConstraint("keyword_id", "checked_at", name="uq_keyword_rankings_kw_date"),
        Index("ix_keyword_rankings_project_id", "project_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    keyword_id: Mapped[str] = mapped_column(
        String, ForeignKey("keywords.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    checked_at: Mapped[date] = mapped_column(Date, nullable=False)
    position: Mapped[int | None] = mapped_column(Integer)
    url_ranking: Mapped[str | None] = mapped_column(String(2048))
    search_volume: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
