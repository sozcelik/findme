import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class PublishRecord(Base):
    __tablename__ = "publish_records"
    __table_args__ = (Index("ix_publish_records_content_id", "content_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id: Mapped[str] = mapped_column(
        String, ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    cms_connection_id: Mapped[str] = mapped_column(
        String, ForeignKey("cms_connections.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(255))
    external_url: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending"
    )  # pending|published|failed|updated
    error_message: Mapped[str | None] = mapped_column(String(1000))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
