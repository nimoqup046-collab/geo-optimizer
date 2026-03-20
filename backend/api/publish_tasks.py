from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import resolve_workspace_id
from database import get_db
from models.account import PlatformAccount
from models.brand import BrandProfile
from models.content import ContentVariant
from models.publish_task import PublishTask


router = APIRouter(prefix="/publish-tasks", tags=["publish_tasks"])


class PublishTaskCreateRequest(BaseModel):
    workspace_id: Optional[str] = None
    brand_id: str
    content_variant_id: str
    platform: str
    account_id: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class PublishTaskUpdateRequest(BaseModel):
    status: Optional[str] = None
    human_confirmation: Optional[str] = None
    publish_url: Optional[str] = None
    failure_reason: Optional[str] = None
    result_payload: Optional[dict] = None


class PublishTaskResponse(BaseModel):
    id: str
    workspace_id: str
    brand_id: str
    content_variant_id: str
    platform: str
    account_id: Optional[str]
    scheduled_at: Optional[datetime]
    status: str
    human_confirmation: str
    publish_url: str
    result_payload: dict
    failure_reason: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=PublishTaskResponse)
async def create_publish_task(
    request: PublishTaskCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    workspace_id = await resolve_workspace_id(db, request.workspace_id)

    brand = await db.execute(select(BrandProfile).where(BrandProfile.id == request.brand_id))
    if not brand.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="未找到品牌")

    variant_result = await db.execute(
        select(ContentVariant).where(ContentVariant.id == request.content_variant_id)
    )
    variant = variant_result.scalar_one_or_none()
    if not variant:
        raise HTTPException(status_code=404, detail="未找到内容变体")

    if request.account_id:
        account_result = await db.execute(
            select(PlatformAccount).where(PlatformAccount.id == request.account_id)
        )
        if not account_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="未找到平台账号")

    task = PublishTask(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        brand_id=request.brand_id,
        content_variant_id=request.content_variant_id,
        platform=request.platform,
        account_id=request.account_id,
        scheduled_at=request.scheduled_at,
        status="scheduled" if request.scheduled_at else "queued",
        human_confirmation="pending",
        result_payload={},
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("", response_model=List[PublishTaskResponse])
async def list_publish_tasks(
    workspace_id: Optional[str] = None,
    brand_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    resolved_workspace_id = await resolve_workspace_id(db, workspace_id)
    query = select(PublishTask).where(PublishTask.workspace_id == resolved_workspace_id)
    if brand_id:
        query = query.where(PublishTask.brand_id == brand_id)
    if status:
        query = query.where(PublishTask.status == status)
    result = await db.execute(query.order_by(PublishTask.created_at.desc()))
    return list(result.scalars().all())


@router.patch("/{task_id}", response_model=PublishTaskResponse)
async def update_publish_task(
    task_id: str,
    request: PublishTaskUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PublishTask).where(PublishTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="未找到发布任务")

    for field, value in request.model_dump(exclude_none=True).items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task
