from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import resolve_workspace_id
from config import settings
from database import get_db
from models.brand import BrandProfile
from models.source_asset import SourceAsset
from services.asset_parser import parse_text_from_file
from services.storage import storage_service


router = APIRouter(prefix="/assets", tags=["assets"])


class AssetPasteRequest(BaseModel):
    workspace_id: Optional[str] = None
    brand_id: str
    title: str = ""
    source_type: str = "pasted_text"
    platform: str = ""
    raw_text: str
    tags: List[str] = Field(default_factory=list)


class AssetResponse(BaseModel):
    id: str
    workspace_id: str
    brand_id: str
    title: str
    source_type: str
    platform: str
    file_name: str
    file_path: str
    mime_type: str
    raw_text: str
    summary: str
    tags: List[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("/paste", response_model=AssetResponse)
async def create_asset_from_paste(
    request: AssetPasteRequest,
    db: AsyncSession = Depends(get_db),
):
    workspace_id = await resolve_workspace_id(db, request.workspace_id)
    brand = await db.execute(select(BrandProfile).where(BrandProfile.id == request.brand_id))
    if not brand.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="未找到品牌")

    text = request.raw_text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="raw_text 不能为空")

    asset = SourceAsset(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        brand_id=request.brand_id,
        title=request.title or "粘贴素材",
        source_type=request.source_type,
        platform=request.platform,
        raw_text=text,
        summary=text[:300],
        tags=request.tags,
        status="ready",
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.post("/upload", response_model=AssetResponse)
async def upload_asset(
    file: UploadFile = File(...),
    brand_id: str = Form(...),
    workspace_id: Optional[str] = Form(default=None),
    title: str = Form(default=""),
    platform: str = Form(default=""),
    tags: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
):
    resolved_workspace_id = await resolve_workspace_id(db, workspace_id)
    brand = await db.execute(select(BrandProfile).where(BrandProfile.id == brand_id))
    if not brand.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="未找到品牌")

    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="上传文件超过大小限制")
    await file.seek(0)

    saved_name, stored_path = await storage_service.save_upload(file)
    parsed_text, parse_status = parse_text_from_file(stored_path)
    parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]

    asset = SourceAsset(
        id=str(uuid.uuid4()),
        workspace_id=resolved_workspace_id,
        brand_id=brand_id,
        title=title or file.filename or saved_name,
        source_type="uploaded_file",
        platform=platform,
        file_name=file.filename or saved_name,
        file_path=stored_path,
        mime_type=file.content_type or "",
        raw_text=parsed_text,
        summary=(parsed_text[:300] if parsed_text else ""),
        tags=parsed_tags,
        status=parse_status,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.get("", response_model=List[AssetResponse])
async def list_assets(
    brand_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    source_type: Optional[str] = None,
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    resolved_workspace_id = await resolve_workspace_id(db, workspace_id)
    query = select(SourceAsset).where(SourceAsset.workspace_id == resolved_workspace_id)
    if brand_id:
        query = query.where(SourceAsset.brand_id == brand_id)
    if source_type:
        query = query.where(SourceAsset.source_type == source_type)
    if platform:
        query = query.where(SourceAsset.platform == platform)

    result = await db.execute(query.order_by(SourceAsset.created_at.desc()))
    return list(result.scalars().all())
