from datetime import datetime
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

_utcnow = lambda: datetime.utcnow()


class KeywordIntent:
    BRAND = "brand"
    INDUSTRY = "industry"
    LONG_TAIL = "long_tail"
    COMPETITOR = "competitor"


class KeywordTopic(Base):
    __tablename__ = "keyword_topics"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brand_profiles.id"), nullable=False, index=True
    )
    keyword: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    intent: Mapped[str] = mapped_column(String(50), default=KeywordIntent.INDUSTRY)
    source: Mapped[str] = mapped_column(String(100), default="manual")
    priority: Mapped[int] = mapped_column(Integer, default=50)
    difficulty: Mapped[str] = mapped_column(String(30), default="medium")
    score: Mapped[float] = mapped_column(Float, default=50.0)
    target_platforms: Mapped[dict] = mapped_column(JSON, default=list)
    notes: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )
