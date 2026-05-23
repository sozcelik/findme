import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class SocialConnection(Base):
    __tablename__ = "social_connections"
    __table_args__ = (Index("ix_social_connections_org_id", "org_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(30), nullable=False)  # linkedin|twitter|reddit
    account_name: Mapped[str | None] = mapped_column(String(255))
    account_id: Mapped[str | None] = mapped_column(String(255))
    access_token_encrypted: Mapped[str | None] = mapped_column(String(2048))
    refresh_token_encrypted: Mapped[str | None] = mapped_column(String(2048))
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[str | None] = mapped_column(String(500))  # space-separated
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
