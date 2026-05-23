import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class OutreachOpportunity(Base):
    __tablename__ = "outreach_opportunities"
    __table_args__ = (
        Index("ix_outreach_opportunities_project_id", "project_id"),
        Index("ix_outreach_opportunities_status", "status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # backlink|guest_post|pr|mention
    target_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    domain_authority: Mapped[int | None] = mapped_column(Integer)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="identified"
    )  # identified|drafted|sent|replied|closed
    outreach_draft: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
