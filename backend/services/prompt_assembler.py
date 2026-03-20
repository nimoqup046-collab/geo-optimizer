from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prompt_profile import PromptProfile
from services.template_manager import format_generation_prompt


@dataclass
class PromptBundle:
    profile_id: Optional[str]
    profile_name: str
    role: str
    system_prompt: str
    user_prompt: str


def _fallback_system_prompt(
    role: str,
    brand_name: str,
    tone_of_voice: str,
    call_to_action: str,
    banned_words: str,
) -> str:
    return (
        "你是内容团队高级编辑，输出必须可执行、结构清晰、避免空话。\n"
        f"角色: {role}\n"
        f"品牌: {brand_name}\n"
        f"语气: {tone_of_voice or '专业、温和、可执行'}\n"
        f"CTA: {call_to_action or '引导用户私信或提交具体场景'}\n"
        f"禁用词: {banned_words or '绝对化承诺、夸大疗效'}\n"
        "要求：先给可引用结论，再给步骤，最后给风险提示。"
    )


async def resolve_prompt_bundle(
    db: AsyncSession,
    workspace_id: str,
    platform: str,
    topic: str,
    brand_name: str,
    brand_industry: str,
    tone_of_voice: str,
    call_to_action: str,
    banned_words: str,
    role: str = "brand_editor",
    prompt_profile_id: Optional[str] = None,
) -> PromptBundle:
    profile: PromptProfile | None = None
    if prompt_profile_id:
        result = await db.execute(
            select(PromptProfile).where(
                PromptProfile.id == prompt_profile_id,
                PromptProfile.workspace_id == workspace_id,
            )
        )
        profile = result.scalar_one_or_none()

    if not profile:
        result = await db.execute(
            select(PromptProfile)
            .where(
                PromptProfile.workspace_id == workspace_id,
                PromptProfile.role == role,
                PromptProfile.platform.in_([platform, "generic"]),
                PromptProfile.industry.in_([brand_industry or "general", "general"]),
                PromptProfile.is_default.is_(True),
            )
            .order_by(PromptProfile.platform.desc(), PromptProfile.industry.desc())
        )
        profile = result.scalars().first()

    user_prompt = format_generation_prompt(
        platform=platform,
        topic=topic,
        brand_name=brand_name,
        tone_of_voice=tone_of_voice,
        call_to_action=call_to_action,
        banned_words=banned_words,
    )
    if profile and profile.user_prompt_template:
        user_prompt = (
            profile.user_prompt_template.replace("{topic}", topic)
            .replace("{platform}", platform)
            .replace("{brand_name}", brand_name)
            .replace("{tone_of_voice}", tone_of_voice or "")
            .replace("{call_to_action}", call_to_action or "")
            .replace("{banned_words}", banned_words or "")
        )

    if profile:
        system_prompt = profile.system_prompt or _fallback_system_prompt(
            role=profile.role,
            brand_name=brand_name,
            tone_of_voice=profile.tone_of_voice or tone_of_voice,
            call_to_action=profile.call_to_action or call_to_action,
            banned_words=",".join(profile.banned_words or []) or banned_words,
        )
        return PromptBundle(
            profile_id=profile.id,
            profile_name=profile.name,
            role=profile.role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    return PromptBundle(
        profile_id=None,
        profile_name="default-fallback",
        role=role,
        system_prompt=_fallback_system_prompt(
            role=role,
            brand_name=brand_name,
            tone_of_voice=tone_of_voice,
            call_to_action=call_to_action,
            banned_words=banned_words,
        ),
        user_prompt=user_prompt,
    )
