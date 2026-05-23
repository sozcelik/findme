import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CmsConnection(Base):
    __tablename__ = "cms_connections"
    __table_args__ = (Index("ix_cms_connections_org_id", "org_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("projects.id", ondelete="SET NULL")
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)  # wordpress|webflow|shopify
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    config_encrypted: Mapped[dict | None] = mapped_column(JSONB)  # encrypted in Supabase Vault in prod
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
