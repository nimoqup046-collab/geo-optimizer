from datetime import datetime, timezone
import uuid

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

_utcnow = lambda: datetime.now(timezone.utc)


class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    industry: Mapped[str] = mapped_column(String(100), default="general")
    service_description: Mapped[str] = mapped_column(Text, default="")
    target_audience: Mapped[str] = mapped_column(Text, default="")
    tone_of_voice: Mapped[str] = mapped_column(String(200), default="")
    call_to_action: Mapped[str] = mapped_column(String(300), default="")
    region: Mapped[str] = mapped_column(String(200), default="")
    competitors: Mapped[dict] = mapped_column(JSON, default=list)
    banned_words: Mapped[dict] = mapped_column(JSON, default=list)
    glossary: Mapped[dict] = mapped_column(JSON, default=dict)
    platform_preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    content_boundaries: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )
