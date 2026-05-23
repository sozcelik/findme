import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (Index("ix_projects_org_id", "org_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    website_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    business_description: Mapped[str | None] = mapped_column(String(2000))
    target_audience: Mapped[str | None] = mapped_column(String(500))
    industry: Mapped[str | None] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(String(10), nullable=False, server_default="en")
    visibility_score: Mapped[float | None] = mapped_column(Float)
    visibility_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
