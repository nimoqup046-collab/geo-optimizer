"""Ranking snapshot model for AI search engine ranking tracking."""

from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

_utcnow = lambda: datetime.utcnow()


class RankingSnapshot(Base):
    __tablename__ = "ranking_snapshots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    content_variant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("content_variants.id"), nullable=True, index=True
    )
    keyword: Mapped[str] = mapped_column(String(200), default="")
    platform: Mapped[str] = mapped_column(String(50), default="")
    ai_engine: Mapped[str] = mapped_column(String(50), default="")  # chatgpt/perplexity/bing
    rank_position: Mapped[int] = mapped_column(Integer, default=0)  # 0 = not found
    snippet_text: Mapped[str] = mapped_column(Text, default="")
    brand_mentioned: Mapped[bool] = mapped_column(Boolean, default=False)
    geo_score_at_check: Mapped[float] = mapped_column(Float, default=0.0)
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
