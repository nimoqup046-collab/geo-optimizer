import csv
import io
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import resolve_workspace_id
from database import get_db
from models.brand import BrandProfile
from models.performance import PerformanceSnapshot


router = APIRouter(prefix="/performance", tags=["performance"])


class PerformanceEntry(BaseModel):
    publish_task_id: Optional[str] = None
    content_variant_id: Optional[str] = None
    keyword: str = ""
    platform: str = ""
    impressions: int = 0
    reads: int = 0
    likes: int = 0
    favorites: int = 0
    comments: int = 0
    shares: int = 0
    leads: int = 0
    keyword_index: float = 0.0
    notes: str = ""


class PerformanceImportRequest(BaseModel):
    workspace_id: Optional[str] = None
    brand_id: str
    entries: List[PerformanceEntry] = Field(default_factory=list)
    csv_text: Optional[str] = None


class PerformanceResponse(BaseModel):
    id: str
    workspace_id: str
    brand_id: str
    publish_task_id: Optional[str]
    content_variant_id: Optional[str]
    keyword: str
    platform: str
    impressions: int
    reads: int
    likes: int
    favorites: int
    comments: int
    shares: int
    leads: int
    keyword_index: float
    notes: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


def _parse_csv_rows(csv_text: str) -> List[PerformanceEntry]:
    parsed: List[PerformanceEntry] = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row_num, row in enumerate(reader, start=2):
        try:
            parsed.append(
                PerformanceEntry(
                    publish_task_id=row.get("publish_task_id") or None,
                    content_variant_id=row.get("content_variant_id") or None,
                    keyword=row.get("keyword", ""),
                    platform=row.get("platform", ""),
                    impressions=int(row.get("impressions", 0) or 0),
                    reads=int(row.get("reads", 0) or 0),
                    likes=int(row.get("likes", 0) or 0),
                    favorites=int(row.get("favorites", 0) or 0),
                    comments=int(row.get("comments", 0) or 0),
                    shares=int(row.get("shares", 0) or 0),
                    leads=int(row.get("leads", 0) or 0),
                    keyword_index=float(row.get("keyword_index", 0) or 0),
                    notes=row.get("notes", ""),
                )
            )
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=422,
                detail=f"CSV 第 {row_num} 行数据格式错误: {exc}",
            )
    return parsed


@router.post("/import", response_model=List[PerformanceResponse])
async def import_performance_data(
    request: PerformanceImportRequest,
    db: AsyncSession = Depends(get_db),
):
    workspace_id = await resolve_workspace_id(db, request.workspace_id)

    brand = await db.execute(select(BrandProfile).where(BrandProfile.id == request.brand_id))
    if not brand.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="未找到品牌")

    rows = list(request.entries)
    if request.csv_text:
        rows.extend(_parse_csv_rows(request.csv_text))
    if not rows:
        raise HTTPException(status_code=400, detail="未提供任何表现数据")

    snapshots: List[PerformanceSnapshot] = []
    for row in rows:
        snapshot = PerformanceSnapshot(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            brand_id=request.brand_id,
            publish_task_id=row.publish_task_id,
            content_variant_id=row.content_variant_id,
            keyword=row.keyword,
            platform=row.platform,
            impressions=row.impressions,
            reads=row.reads,
            likes=row.likes,
            favorites=row.favorites,
            comments=row.comments,
            shares=row.shares,
            leads=row.leads,
            keyword_index=row.keyword_index,
            notes=row.notes,
        )
        db.add(snapshot)
        snapshots.append(snapshot)

    await db.commit()
    for s in snapshots:
        await db.refresh(s)
    return snapshots


@router.get("", response_model=List[PerformanceResponse])
async def list_performance(
    workspace_id: Optional[str] = None,
    brand_id: Optional[str] = None,
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    resolved_workspace_id = await resolve_workspace_id(db, workspace_id)
    query = select(PerformanceSnapshot).where(
        PerformanceSnapshot.workspace_id == resolved_workspace_id
    )
    if brand_id:
        query = query.where(PerformanceSnapshot.brand_id == brand_id)
    if platform:
        query = query.where(PerformanceSnapshot.platform == platform)
    result = await db.execute(query.order_by(PerformanceSnapshot.created_at.desc()))
    return list(result.scalars().all())
