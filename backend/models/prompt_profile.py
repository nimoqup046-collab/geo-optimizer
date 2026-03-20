from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class PromptProfile(Base):
    __tablename__ = "prompt_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(80), default="brand_editor", index=True)
    platform: Mapped[str] = mapped_column(String(80), default="generic", index=True)
    industry: Mapped[str] = mapped_column(String(80), default="general", index=True)
    tone_of_voice: Mapped[str] = mapped_column(String(200), default="")
    banned_words: Mapped[dict] = mapped_column(JSON, default=list)
    call_to_action: Mapped[str] = mapped_column(String(300), default="")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    user_prompt_template: Mapped[str] = mapped_column(Text, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
