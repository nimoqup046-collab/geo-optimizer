from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

_utcnow = lambda: datetime.utcnow()


class ContentStatus:
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    PUBLISHED = "published"
    SCHEDULED = "scheduled"


class ContentItem(Base):
    __tablename__ = "content_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brand_profiles.id"), nullable=False, index=True
    )
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_reports_v2.id"), nullable=False, index=True
    )
    content_type: Mapped[str] = mapped_column(String(100), default="article")
    topic: Mapped[str] = mapped_column(String(300), default="")
    status: Mapped[str] = mapped_column(String(50), default=ContentStatus.DRAFT)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    reviewed_by: Mapped[str] = mapped_column(String(120), default="")
    export_paths: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )


class ContentVariant(Base):
    __tablename__ = "content_variants"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    content_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("content_items.id"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[dict] = mapped_column(JSON, default=list)
    llm_provider: Mapped[str] = mapped_column(String(50), default="")
    llm_model: Mapped[str] = mapped_column(String(100), default="")
    generation_meta: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(50), default=ContentStatus.DRAFT)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )
