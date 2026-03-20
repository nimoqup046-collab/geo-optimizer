from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import resolve_workspace_id
from database import get_db
from models.brand import BrandProfile
from models.performance import OptimizationInsight, PerformanceSnapshot


router = APIRouter(prefix="/optimization-insights", tags=["optimization"])


class OptimizationRunRequest(BaseModel):
    workspace_id: Optional[str] = None
    brand_id: str
    lookback_days: int = 30


class OptimizationInsightResponse(BaseModel):
    id: str
    workspace_id: str
    brand_id: str
    source_snapshot_ids: List[str]
    insight_type: str
    title: str
    details: str
    action_items: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/run", response_model=List[OptimizationInsightResponse])
async def run_optimization_insights(
    request: OptimizationRunRequest,
    db: AsyncSession = Depends(get_db),
):
    workspace_id = await resolve_workspace_id(db, request.workspace_id)
    brand_result = await db.execute(select(BrandProfile).where(BrandProfile.id == request.brand_id))
    brand = brand_result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="未找到品牌")

    since = datetime.utcnow() - timedelta(days=max(1, request.lookback_days))
    snapshots_result = await db.execute(
        select(PerformanceSnapshot).where(
            PerformanceSnapshot.workspace_id == workspace_id,
            PerformanceSnapshot.brand_id == request.brand_id,
            PerformanceSnapshot.created_at >= since,
        )
    )
    snapshots = list(snapshots_result.scalars().all())
    if not snapshots:
        raise HTTPException(status_code=404, detail="回溯窗口内没有表现数据")

    by_platform = defaultdict(list)
    by_keyword = defaultdict(list)
    for s in snapshots:
        by_platform[s.platform].append(s)
        if s.keyword:
            by_keyword[s.keyword].append(s)

    insights: List[OptimizationInsight] = []

    # Insight 1: best platform
    platform_scores = {}
    for platform, rows in by_platform.items():
        score = mean([(r.reads + r.likes * 2 + r.comments * 3 + r.leads * 8) for r in rows])
        platform_scores[platform] = score
    best_platform = max(platform_scores, key=platform_scores.get)
    best_value = round(platform_scores[best_platform], 2)
    i1 = OptimizationInsight(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        brand_id=request.brand_id,
        source_snapshot_ids=[s.id for s in snapshots],
        insight_type="platform_priority",
        title=f"下一轮优先强化 {best_platform} 平台",
        details=f"{best_platform} 的加权互动得分最高（{best_value}）。",
        action_items=[
            f"未来 2 周内将 {best_platform} 发布频次提升 20%-30%。",
            "复用高表现主题，至少新增 3 个变体。",
        ],
    )
    db.add(i1)
    insights.append(i1)

    # Insight 2: keyword opportunities
    keyword_scores = []
    for keyword, rows in by_keyword.items():
        score = mean([(r.reads + r.likes + r.comments * 2 + r.leads * 10) for r in rows])
        keyword_scores.append((keyword, score))
    keyword_scores.sort(key=lambda x: x[1], reverse=True)
    top_keywords = [k for k, _ in keyword_scores[:3]]
    i2 = OptimizationInsight(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        brand_id=request.brand_id,
        source_snapshot_ids=[s.id for s in snapshots],
        insight_type="keyword_focus",
        title="优先扩写已验证的高转化关键词",
        details="当前窗口期的重点关键词：" + "、".join(top_keywords or ["暂无"]),
        action_items=[
            "每个重点关键词输出 1 篇主文 + 2 篇衍生内容。",
            "每篇内容补充可引用结论句，提升 AI 摘要引用概率。",
        ],
    )
    db.add(i2)
    insights.append(i2)

    await db.commit()
    for i in insights:
        await db.refresh(i)
    return insights


@router.get("", response_model=List[OptimizationInsightResponse])
async def list_optimization_insights(
    workspace_id: Optional[str] = None,
    brand_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    resolved_workspace_id = await resolve_workspace_id(db, workspace_id)
    query = select(OptimizationInsight).where(
        OptimizationInsight.workspace_id == resolved_workspace_id
    )
    if brand_id:
        query = query.where(OptimizationInsight.brand_id == brand_id)
    result = await db.execute(query.order_by(OptimizationInsight.created_at.desc()))
    return list(result.scalars().all())
