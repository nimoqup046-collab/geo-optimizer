"""API routes for competitor content analysis."""

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from services.competitor_analyzer import (
    analyze_competitors,
    find_content_gaps,
    generate_differentiation_strategy,
)

router = APIRouter(prefix="/competitors", tags=["competitors"])


class AnalyzeRequest(BaseModel):
    competitor_names: List[str]
    keywords: List[str]


class GapsRequest(BaseModel):
    keywords: List[str]
    competitor_names: List[str]


class StrategyRequest(BaseModel):
    brand_name: str
    competitor_names: List[str]
    keywords: List[str]


@router.post("/analyze")
async def run_competitor_analysis(req: AnalyzeRequest):
    """Run competitor content strategy analysis."""
    if not req.competitor_names:
        return {"profiles": [], "count": 0}

    profiles = await analyze_competitors(req.competitor_names, req.keywords)
    return {
        "profiles": [p.to_dict() for p in profiles],
        "count": len(profiles),
    }


@router.post("/gaps")
async def get_content_gaps(req: GapsRequest):
    """Identify content gaps between us and competitors."""
    if not req.keywords:
        return {"gaps": [], "count": 0, "summary": {}}

    gaps = await find_content_gaps(req.keywords, req.competitor_names)

    # Summarize by gap type.
    by_type = {}
    for g in gaps:
        by_type.setdefault(g.gap_type, 0)
        by_type[g.gap_type] += 1

    # Summarize by platform.
    by_platform = {}
    for g in gaps:
        by_platform.setdefault(g.platform, 0)
        by_platform[g.platform] += 1

    return {
        "gaps": [g.to_dict() for g in gaps],
        "count": len(gaps),
        "summary": {
            "by_type": by_type,
            "by_platform": by_platform,
            "avg_opportunity": round(sum(g.opportunity_score for g in gaps) / max(1, len(gaps)), 1),
        },
    }


@router.get("/benchmarks")
async def get_benchmarks(competitor_names: Optional[str] = None):
    """Get comparative benchmark data."""
    names = [n.strip() for n in (competitor_names or "").split(",") if n.strip()]
    if not names:
        names = ["竞品A", "竞品B", "竞品C"]

    profiles = await analyze_competitors(names, ["行业关键词"])
    benchmarks = []
    for p in profiles:
        benchmarks.append({
            "name": p.name,
            "platform_count": len(p.platforms),
            "avg_geo_score": p.avg_geo_score,
            "posting_frequency": p.posting_frequency,
            "strength_count": len(p.strengths),
            "weakness_count": len(p.weaknesses),
        })

    return {"benchmarks": benchmarks, "count": len(benchmarks)}


@router.post("/strategy")
async def gen_strategy(req: StrategyRequest):
    """Generate differentiation strategy based on competitor analysis."""
    profiles = await analyze_competitors(req.competitor_names, req.keywords)
    gaps = await find_content_gaps(req.keywords, req.competitor_names)
    strategy = await generate_differentiation_strategy(req.brand_name, profiles, gaps)
    return strategy
