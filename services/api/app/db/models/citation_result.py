from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from app.db.base import Base


class CitationResult(Base):
    __tablename__ = "citation_results"

    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    org_id = Column(String, nullable=False)
    job_id = Column(String, nullable=True)
    query = Column(Text, nullable=False)
    model = Column(String(50), nullable=False)
    mentioned = Column(Boolean, nullable=False, default=False)
    mention_position = Column(Integer, nullable=True)
    sentiment = Column(String(20), nullable=True)
    excerpt = Column(Text, nullable=True)
    full_response = Column(Text, nullable=True)
    checked_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
