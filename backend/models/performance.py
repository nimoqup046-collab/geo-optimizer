from datetime import datetime, timezone
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

_utcnow = lambda: datetime.now(timezone.utc)


class PerformanceSnapshot(Base):
    __tablename__ = "performance_snapshots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brand_profiles.id"), nullable=False, index=True
    )
    publish_task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("publish_tasks.id"), nullable=True, index=True
    )
    content_variant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("content_variants.id"), nullable=True, index=True
    )
    keyword: Mapped[str] = mapped_column(String(200), default="")
    platform: Mapped[str] = mapped_column(String(50), default="")
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    reads: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    favorites: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    leads: Mapped[int] = mapped_column(Integer, default=0)
    keyword_index: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )


class OptimizationInsight(Base):
    __tablename__ = "optimization_insights"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brand_profiles.id"), nullable=False, index=True
    )
    source_snapshot_ids: Mapped[dict] = mapped_column(JSON, default=list)
    insight_type: Mapped[str] = mapped_column(String(100), default="next_action")
    title: Mapped[str] = mapped_column(String(300), default="")
    details: Mapped[str] = mapped_column(Text, default="")
    action_items: Mapped[dict] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
