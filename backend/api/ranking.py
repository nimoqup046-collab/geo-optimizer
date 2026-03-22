"""API routes for AI search engine ranking monitoring."""

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from services.ranking_monitor import (
    check_ai_rankings,
    compute_ranking_trends,
    generate_optimization_actions,
)

router = APIRouter(prefix="/ranking", tags=["ranking"])


class RankingCheckRequest(BaseModel):
    keywords: List[str]
    platform: str = "wechat"
    geo_score: float = 50.0


class RankingHistoryRequest(BaseModel):
    keyword: Optional[str] = None
    ai_engine: Optional[str] = None
    days: int = 30


@router.post("/check")
async def check_rankings(req: RankingCheckRequest):
    """Trigger ranking check for given keywords across AI engines."""
    if not req.keywords:
        return {"results": [], "count": 0}

    results = await check_ai_rankings(
        keywords=req.keywords[:20],
        platform=req.platform,
        geo_score=req.geo_score,
    )
    return {
        "results": [r.to_dict() for r in results],
        "count": len(results),
        "engines_checked": ["chatgpt", "perplexity", "bing_copilot"],
    }


@router.get("/trends")
async def get_ranking_trends(keyword: Optional[str] = None):
    """Get aggregated ranking trends (mock data for demo)."""
    # In production, this would query RankingSnapshot from DB.
    # For now, generate mock trend data.
    mock_snapshots = []
    if keyword:
        for i in range(10):
            for engine in ["chatgpt", "perplexity", "bing_copilot"]:
                mock_snapshots.append({
                    "keyword": keyword,
                    "ai_engine": engine,
                    "rank_position": max(1, 8 - i // 3 + (hash(f"{keyword}{engine}{i}") % 3)),
                })

    trends = compute_ranking_trends(mock_snapshots)
    return {"keyword": keyword or "all", "trends": trends}


@router.get("/actions")
async def get_optimization_actions(
    keyword: str = "",
    rank_position: int = 0,
    geo_score: float = 50.0,
):
    """Get optimization action suggestions for a keyword."""
    if not keyword:
        return {"actions": [], "keyword": ""}

    actions = generate_optimization_actions(keyword, rank_position, geo_score)
    return {
        "keyword": keyword,
        "actions": [a.to_dict() for a in actions],
        "count": len(actions),
    }
