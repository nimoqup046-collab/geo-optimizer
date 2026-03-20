from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import resolve_workspace_id
from database import get_db
from models.prompt_profile import PromptProfile


router = APIRouter(prefix="/prompt-profiles", tags=["prompt_profiles"])


class PromptProfileCreateRequest(BaseModel):
    workspace_id: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=120)
    role: str = "brand_editor"
    platform: str = "generic"
    industry: str = "general"
    tone_of_voice: str = ""
    banned_words: List[str] = Field(default_factory=list)
    call_to_action: str = ""
    system_prompt: str = ""
    user_prompt_template: str = ""
    is_default: bool = False


class PromptProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    platform: Optional[str] = None
    industry: Optional[str] = None
    tone_of_voice: Optional[str] = None
    banned_words: Optional[List[str]] = None
    call_to_action: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    is_default: Optional[bool] = None


class PromptProfileResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    role: str
    platform: str
    industry: str
    tone_of_voice: str
    banned_words: List[str]
    call_to_action: str
    system_prompt: str
    user_prompt_template: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=PromptProfileResponse)
async def create_prompt_profile(
    request: PromptProfileCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    workspace_id = await resolve_workspace_id(db, request.workspace_id)
    profile = PromptProfile(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        name=request.name,
        role=request.role,
        platform=request.platform,
        industry=request.industry,
        tone_of_voice=request.tone_of_voice,
        banned_words=request.banned_words,
        call_to_action=request.call_to_action,
        system_prompt=request.system_prompt,
        user_prompt_template=request.user_prompt_template,
        is_default=request.is_default,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("", response_model=List[PromptProfileResponse])
async def list_prompt_profiles(
    workspace_id: Optional[str] = None,
    role: Optional[str] = None,
    platform: Optional[str] = None,
    industry: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    resolved_workspace = await resolve_workspace_id(db, workspace_id)
    query = select(PromptProfile).where(PromptProfile.workspace_id == resolved_workspace)
    if role:
        query = query.where(PromptProfile.role == role)
    if platform:
        query = query.where(PromptProfile.platform == platform)
    if industry:
        query = query.where(PromptProfile.industry == industry)
    result = await db.execute(query.order_by(PromptProfile.updated_at.desc()))
    return list(result.scalars().all())


@router.put("/{profile_id}", response_model=PromptProfileResponse)
async def update_prompt_profile(
    profile_id: str,
    request: PromptProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PromptProfile).where(PromptProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="未找到提示词档案")

    for key, value in request.model_dump(exclude_none=True).items():
        setattr(profile, key, value)

    await db.commit()
    await db.refresh(profile)
    return profile
