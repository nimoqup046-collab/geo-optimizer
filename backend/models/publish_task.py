from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

_utcnow = lambda: datetime.utcnow()


class PublishTask(Base):
    __tablename__ = "publish_tasks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brand_profiles.id"), nullable=False, index=True
    )
    content_variant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("content_variants.id"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("platform_accounts_v2.id"), nullable=True, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="queued"
    )  # queued | scheduled | posted | failed
    human_confirmation: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending | confirmed
    publish_url: Mapped[str] = mapped_column(String(500), default="")
    result_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    failure_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )
