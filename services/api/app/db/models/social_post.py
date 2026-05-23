import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class SocialPost(Base):
    __tablename__ = "social_posts"
    __table_args__ = (
        Index("ix_social_posts_content_id", "content_id"),
        Index("ix_social_posts_project_id", "project_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id: Mapped[str] = mapped_column(
        String, ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(30), nullable=False)  # linkedin|twitter|reddit
    body: Mapped[str | None] = mapped_column(Text)
    hashtags: Mapped[str | None] = mapped_column(String(500))  # space-separated
    reddit_title: Mapped[str | None] = mapped_column(String(300))  # Reddit only
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="draft"
    )  # draft|scheduled|posted|failed
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_post_id: Mapped[str | None] = mapped_column(String(255))
    engagement: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
