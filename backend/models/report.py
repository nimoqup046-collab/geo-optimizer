from datetime import datetime, timezone
import uuid

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

_utcnow = lambda: datetime.now(timezone.utc)


class AnalysisReport(Base):
    __tablename__ = "analysis_reports_v2"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    brand_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("brand_profiles.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    report_type: Mapped[str] = mapped_column(String(100), default="strategy")
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    keyword_layers: Mapped[dict] = mapped_column(JSON, default=dict)
    gap_analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    competitor_analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    recommendations: Mapped[dict] = mapped_column(JSON, default=list)
    llm_summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="completed")
    md_path: Mapped[str] = mapped_column(String(500), default="")
    html_path: Mapped[str] = mapped_column(String(500), default="")
    pdf_path: Mapped[str] = mapped_column(String(500), default="")
    pptx_path: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )
