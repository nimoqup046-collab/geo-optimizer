"""Expert Agent Team API routes.

Provides endpoints for:
- Running the full 5-expert pipeline
- Running individual experts
- Getting team configuration
- GEO scoring
- GEO optimization strategies
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import resolve_workspace_id
from config import settings
from database import get_db
from models.brand import BrandProfile
from models.report import AnalysisReport
from models.source_asset import SourceAsset
from services.analysis_engine import (
    build_data_layer_summary,
    build_recommendations,
    classify_keyword,
    estimate_difficulty,
    score_keyword,
)
from services.expert_team import (
    get_team_config,
    run_expert_pipeline,
    run_single_expert,
)
from services.geo_scorer import compute_geo_score
from services.geo_strategies import AVAILABLE_STRATEGIES, apply_multiple_strategies


router = APIRouter(prefix="/expert-team", tags=["expert-team"])


# ── Request / Response models ──────────────────────────────────────


class ExpertPipelineRequest(BaseModel):
    workspace_id: Optional[str] = None
    brand_id: str
    keyword_seeds: List[str] = Field(default_factory=list)
    competitor_keywords: List[str] = Field(default_factory=list)
    target_platforms: List[str] = Field(
        default_factory=lambda: ["wechat", "xiaohongshu", "zhihu", "video"]
    )
    provider: str = "openrouter"


class SingleExpertRequest(BaseModel):
    role: str
    payload: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    provider: str = "openrouter"


class GEOScoreRequest(BaseModel):
    text: str


class GEOOptimizeRequest(BaseModel):
    content: str
    strategies: List[str] = Field(default_factory=lambda: ["citation_enhancement"])
    provider: str = "openrouter"


class ExpertOutputResponse(BaseModel):
    role: str
    label: str
    model: str
    content: str
    duration_ms: int
    error: Optional[str] = None


class TeamReportResponse(BaseModel):
    report_id: str
    experts: Dict[str, ExpertOutputResponse]
    geo_scores: Dict[str, Any]
    total_duration_ms: int
    markdown_report: str
    created_at: datetime


class GEOScoreResponse(BaseModel):
    claim_density: float
    citability: float
    extractability: float
    readability: float
    overall: float
    details: Dict[str, str]


class StrategyResultResponse(BaseModel):
    strategy_name: str
    optimized_text: str
    changes_made: List[str]
    estimated_improvement: str


# ── Endpoints ──────────────────────────────────────────────────────


@router.get("/config")
async def get_expert_team_configuration():
    """Return current expert team configuration (roles, models, pipeline)."""
    return get_team_config()


@router.get("/roles")
async def list_expert_roles():
    """List all available expert roles with their models."""
    config = get_team_config()
    return config["roles"]


@router.get("/strategies")
async def list_geo_strategies():
    """List available GEO optimization strategies."""
    return {
        "strategies": AVAILABLE_STRATEGIES,
        "descriptions": {
            "citation_enhancement": "引用增强 — 添加可信来源和数据引用",
            "statistics_addition": "统计增强 — 插入具体数据和研究结论",
            "qa_structuring": "问答结构化 — 重构为搜索引擎友好的 Q&A 格式",
            "answer_frontloading": "断言前置 — 核心答案放在开头",
            "entity_enrichment": "实体丰富 — 增加专业术语和命名实体",
        },
    }


@router.post("/analyze", response_model=TeamReportResponse)
async def run_expert_analysis(
    request: ExpertPipelineRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run the full 5-expert pipeline for a brand.

    Pipeline: Chief Strategist → Data Analyst + GEO Optimizer (parallel)
    → Content Architect → Quality Reviewer.
    """
    if not settings.FEATURE_EXPERT_TEAM:
        raise HTTPException(status_code=403, detail="专家团队功能未启用")

    workspace_id = await resolve_workspace_id(db, request.workspace_id)

    # Load brand.
    brand_result = await db.execute(
        select(BrandProfile).where(BrandProfile.id == request.brand_id)
    )
    brand = brand_result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="未找到品牌")

    # Load assets.
    asset_result = await db.execute(
        select(SourceAsset).where(
            SourceAsset.workspace_id == workspace_id,
            SourceAsset.brand_id == request.brand_id,
        )
    )
    assets = list(asset_result.scalars().all())
    asset_texts = [a.raw_text for a in assets if a.raw_text and a.raw_text.strip()]

    # Build keyword layers.
    all_keywords = [k.strip() for k in request.keyword_seeds if k.strip()]
    all_keywords.extend([k.strip() for k in request.competitor_keywords if k.strip()])
    all_keywords = list(dict.fromkeys(all_keywords))
    if not all_keywords:
        raise HTTPException(status_code=400, detail="keyword_seeds 不能为空")

    keyword_layers: Dict[str, list] = {
        "brand": [], "industry": [], "long_tail": [], "competitor": []
    }
    for kw in all_keywords:
        intent = classify_keyword(kw, brand.name, brand.competitors or [])
        difficulty = estimate_difficulty(kw)
        score = score_keyword(kw, intent, difficulty)
        keyword_layers[intent].append({
            "keyword": kw, "intent": intent,
            "difficulty": difficulty, "score": score,
        })

    gap_analysis = build_data_layer_summary(asset_texts, all_keywords)
    recommendations = build_recommendations(keyword_layers, gap_analysis)

    brand_data = {
        "name": brand.name,
        "industry": brand.industry,
        "tone_of_voice": brand.tone_of_voice,
        "call_to_action": brand.call_to_action,
        "region": brand.region,
        "competitors": brand.competitors or [],
        "content_boundaries": brand.content_boundaries,
    }

    # Run expert pipeline.
    team_report = await run_expert_pipeline(
        brand_data=brand_data,
        keyword_layers=keyword_layers,
        gap_analysis=gap_analysis,
        recommendations=recommendations,
        asset_texts=asset_texts,
        target_platforms=request.target_platforms,
        provider=request.provider,
    )

    # Save as analysis report.
    report_id = str(uuid.uuid4())
    report = AnalysisReport(
        id=report_id,
        workspace_id=workspace_id,
        brand_id=request.brand_id,
        title=f"{brand.name} 专家团队 GEO 深度分析报告",
        report_type="expert_team",
        input_payload=request.model_dump(),
        keyword_layers=keyword_layers,
        gap_analysis=gap_analysis,
        competitor_analysis={"competitors": brand.competitors or []},
        recommendations=recommendations,
        llm_summary=team_report.to_markdown(),
        status="completed",
    )
    db.add(report)
    await db.commit()

    report_dict = team_report.to_dict()
    experts_response = {}
    for role_key, data in report_dict["experts"].items():
        experts_response[role_key] = ExpertOutputResponse(**data)

    return TeamReportResponse(
        report_id=report_id,
        experts=experts_response,
        geo_scores=report_dict["geo_scores"],
        total_duration_ms=report_dict["total_duration_ms"],
        markdown_report=team_report.to_markdown(),
        created_at=datetime.utcnow(),
    )


@router.post("/expert/run", response_model=ExpertOutputResponse)
async def run_individual_expert(request: SingleExpertRequest):
    """Run a single expert for ad-hoc queries."""
    if not settings.FEATURE_EXPERT_TEAM:
        raise HTTPException(status_code=403, detail="专家团队功能未启用")

    output = await run_single_expert(
        role=request.role,
        payload=request.payload,
        context=request.context,
        provider=request.provider,
    )
    return ExpertOutputResponse(
        role=output.role,
        label=output.label,
        model=output.model,
        content=output.content,
        duration_ms=output.duration_ms,
        error=output.error,
    )


@router.post("/geo-score", response_model=GEOScoreResponse)
async def score_content(request: GEOScoreRequest):
    """Compute GEO semantic scores for a piece of text."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")
    card = compute_geo_score(request.text)
    return GEOScoreResponse(**card.to_dict())


@router.post("/optimize", response_model=List[StrategyResultResponse])
async def optimize_content(request: GEOOptimizeRequest):
    """Apply GEO optimization strategies to content."""
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")
    for s in request.strategies:
        if s not in AVAILABLE_STRATEGIES:
            raise HTTPException(
                status_code=400,
                detail=f"未知策略: {s}。可用: {AVAILABLE_STRATEGIES}",
            )

    results = await apply_multiple_strategies(
        strategies=request.strategies,
        content=request.content,
        provider=request.provider,
    )
    return [
        StrategyResultResponse(
            strategy_name=r.strategy_name,
            optimized_text=r.optimized_text,
            changes_made=r.changes_made,
            estimated_improvement=r.estimated_improvement,
        )
        for r in results
    ]
