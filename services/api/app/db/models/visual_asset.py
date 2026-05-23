import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class VisualAsset(Base):
    __tablename__ = "visual_assets"
    __table_args__ = (Index("ix_visual_assets_content_id", "content_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id: Mapped[str] = mapped_column(
        String, ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # blog_hero|infographic|social_graphic|thumbnail
    prompt_used: Mapped[str | None] = mapped_column(Text)
    model_used: Mapped[str | None] = mapped_column(String(50))  # flux-dev|dall-e-3
    storage_url: Mapped[str | None] = mapped_column(String(2048))  # R2 internal URL
    cdn_url: Mapped[str | None] = mapped_column(String(2048))  # public CDN URL
    alt_text: Mapped[str | None] = mapped_column(String(500))
    generation_cost: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
