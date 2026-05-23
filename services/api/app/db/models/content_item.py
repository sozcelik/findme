import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class ContentItem(Base):
    __tablename__ = "content_items"
    __table_args__ = (
        Index("ix_content_items_project_id", "project_id"),
        Index("ix_content_items_org_id", "org_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="article")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(500))
    body_markdown: Mapped[str | None] = mapped_column(Text)
    body_html: Mapped[str | None] = mapped_column(Text)
    meta_title: Mapped[str | None] = mapped_column(String(200))
    meta_description: Mapped[str | None] = mapped_column(String(500))
    focus_keyword: Mapped[str | None] = mapped_column(String(255))
    word_count: Mapped[int | None] = mapped_column(Integer)
    readability_score: Mapped[float | None] = mapped_column(Float)
    seo_score: Mapped[float | None] = mapped_column(Float)
    ai_visibility_score: Mapped[float | None] = mapped_column(Float)
    schema_markup: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    campaign_id: Mapped[str | None] = mapped_column(String)
    ai_model_used: Mapped[str | None] = mapped_column(String(50))
    generation_cost: Mapped[float | None] = mapped_column(Float)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
