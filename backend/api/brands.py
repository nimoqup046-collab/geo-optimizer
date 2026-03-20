from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import resolve_workspace_id
from database import get_db
from models.brand import BrandProfile


router = APIRouter(prefix="/brands", tags=["brands"])


class BrandCreateRequest(BaseModel):
    workspace_id: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=200)
    industry: str = "general"
    service_description: str = ""
    target_audience: str = ""
    tone_of_voice: str = ""
    call_to_action: str = ""
    region: str = ""
    competitors: List[str] = Field(default_factory=list)
    banned_words: List[str] = Field(default_factory=list)
    glossary: dict = Field(default_factory=dict)
    platform_preferences: dict = Field(default_factory=dict)
    content_boundaries: str = ""


class BrandUpdateRequest(BaseModel):
    industry: Optional[str] = None
    service_description: Optional[str] = None
    target_audience: Optional[str] = None
    tone_of_voice: Optional[str] = None
    call_to_action: Optional[str] = None
    region: Optional[str] = None
    competitors: Optional[List[str]] = None
    banned_words: Optional[List[str]] = None
    glossary: Optional[dict] = None
    platform_preferences: Optional[dict] = None
    content_boundaries: Optional[str] = None


class BrandResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    industry: str
    service_description: str
    target_audience: str
    tone_of_voice: str
    call_to_action: str
    region: str
    competitors: List[str]
    banned_words: List[str]
    glossary: dict
    platform_preferences: dict
    content_boundaries: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=BrandResponse)
async def create_brand(request: BrandCreateRequest, db: AsyncSession = Depends(get_db)):
    workspace_id = await resolve_workspace_id(db, request.workspace_id)
    duplicate = await db.execute(
        select(BrandProfile).where(
            BrandProfile.workspace_id == workspace_id, BrandProfile.name == request.name
        )
    )
    if duplicate.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="当前工作空间中已存在同名品牌")

    brand = BrandProfile(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        name=request.name,
        industry=request.industry,
        service_description=request.service_description,
        target_audience=request.target_audience,
        tone_of_voice=request.tone_of_voice,
        call_to_action=request.call_to_action,
        region=request.region,
        competitors=request.competitors,
        banned_words=request.banned_words,
        glossary=request.glossary,
        platform_preferences=request.platform_preferences,
        content_boundaries=request.content_boundaries,
    )
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    return brand


@router.get("", response_model=List[BrandResponse])
async def list_brands(
    workspace_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    resolved_workspace = await resolve_workspace_id(db, workspace_id)
    result = await db.execute(
        select(BrandProfile).where(BrandProfile.workspace_id == resolved_workspace)
    )
    return list(result.scalars().all())


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(brand_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BrandProfile).where(BrandProfile.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="未找到品牌")
    return brand


@router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: str,
    request: BrandUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BrandProfile).where(BrandProfile.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="未找到品牌")

    for field, value in request.model_dump(exclude_none=True).items():
        setattr(brand, field, value)
    await db.commit()
    await db.refresh(brand)
    return brand
