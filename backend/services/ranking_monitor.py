"""AI search engine ranking monitor — tracks content visibility across AI engines.

Default implementation uses mock ranking data derived from GEO scores for
development and demonstration purposes.
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

AI_ENGINES = ["chatgpt", "perplexity", "bing_copilot"]


@dataclass
class RankingCheckResult:
    """Result of a single ranking check for one keyword on one AI engine."""

    keyword: str
    platform: str
    ai_engine: str
    rank_position: int  # 1-based, 0 = not found
    snippet_found: bool
    brand_mentioned: bool
    checked_at: str = ""

    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keyword": self.keyword,
            "platform": self.platform,
            "ai_engine": self.ai_engine,
            "rank_position": self.rank_position,
            "snippet_found": self.snippet_found,
            "brand_mentioned": self.brand_mentioned,
            "checked_at": self.checked_at,
        }


@dataclass
class OptimizationAction:
    """Suggested action to improve ranking."""

    keyword: str
    action_type: str  # improve_structure / add_citations / expand_content / refresh_data
    description: str
    priority: str  # high / medium / low
    expected_impact: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keyword": self.keyword,
            "action_type": self.action_type,
            "description": self.description,
            "priority": self.priority,
            "expected_impact": self.expected_impact,
        }


class MockRankingChecker:
    """Generate mock ranking data based on GEO scores for demo/development."""

    def _hash_seed(self, keyword: str, engine: str) -> int:
        combined = f"{keyword}:{engine}"
        return int(hashlib.md5(combined.encode()).hexdigest()[:8], 16)

    async def check_rankings(
        self,
        keywords: List[str],
        platform: str = "wechat",
        geo_score: float = 50.0,
    ) -> List[RankingCheckResult]:
        results = []
        for kw in keywords:
            for engine in AI_ENGINES:
                seed = self._hash_seed(kw, engine)

                # Higher GEO score → better (lower) rank position.
                base_rank = max(1, int(20 - (geo_score / 5)))
                noise = (seed % 5) - 2  # -2 to +2
                rank = max(1, min(20, base_rank + noise))

                # Some keywords may not be found (rank 0).
                if seed % 10 == 0 and geo_score < 40:
                    rank = 0

                results.append(RankingCheckResult(
                    keyword=kw,
                    platform=platform,
                    ai_engine=engine,
                    rank_position=rank,
                    snippet_found=rank > 0 and rank <= 10,
                    brand_mentioned=rank > 0 and rank <= 5 and geo_score > 60,
                ))
        return results


async def check_ai_rankings(
    keywords: List[str],
    platform: str = "wechat",
    geo_score: float = 50.0,
) -> List[RankingCheckResult]:
    """Check AI search engine rankings for given keywords."""
    checker = MockRankingChecker()
    return await checker.check_rankings(keywords, platform, geo_score)


def compute_ranking_trends(
    snapshots: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute ranking trend statistics from historical snapshots."""
    if not snapshots:
        return {"trend": "no_data", "data_points": 0, "engines": {}}

    by_engine: Dict[str, List[int]] = {}
    for snap in snapshots:
        engine = snap.get("ai_engine", "unknown")
        rank = snap.get("rank_position", 0)
        if rank > 0:
            by_engine.setdefault(engine, []).append(rank)

    engine_trends = {}
    for engine, ranks in by_engine.items():
        if len(ranks) < 2:
            engine_trends[engine] = {"trend": "insufficient_data", "latest": ranks[-1] if ranks else 0}
            continue
        recent = ranks[-3:]  # last 3
        older = ranks[:-3] if len(ranks) > 3 else ranks[:1]
        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)
        if avg_recent < avg_older - 1:
            trend = "improving"
        elif avg_recent > avg_older + 1:
            trend = "declining"
        else:
            trend = "stable"
        engine_trends[engine] = {
            "trend": trend,
            "latest": ranks[-1],
            "avg_recent": round(avg_recent, 1),
            "data_points": len(ranks),
        }

    overall_latest = []
    for et in engine_trends.values():
        if et.get("latest", 0) > 0:
            overall_latest.append(et["latest"])

    return {
        "trend": "improving" if overall_latest and sum(overall_latest) / len(overall_latest) < 5 else "needs_work",
        "data_points": len(snapshots),
        "engines": engine_trends,
        "avg_position": round(sum(overall_latest) / max(1, len(overall_latest)), 1) if overall_latest else 0,
    }


def generate_optimization_actions(
    keyword: str,
    rank_position: int,
    geo_score: float = 50.0,
) -> List[OptimizationAction]:
    """Generate actionable optimization suggestions based on ranking and GEO score."""
    actions = []

    if rank_position == 0:
        actions.append(OptimizationAction(
            keyword=keyword,
            action_type="expand_content",
            description=f"关键词「{keyword}」在 AI 搜索中未被收录，建议创建专题内容覆盖该关键词",
            priority="high",
            expected_impact="从无到有，预计可获得 Top 10 排名",
        ))

    if rank_position > 10:
        actions.append(OptimizationAction(
            keyword=keyword,
            action_type="improve_structure",
            description=f"关键词「{keyword}」排名第 {rank_position} 位，建议优化内容结构，增加小标题和列表",
            priority="high",
            expected_impact="排名提升 5-8 位",
        ))

    if geo_score < 60:
        actions.append(OptimizationAction(
            keyword=keyword,
            action_type="add_citations",
            description=f"GEO 评分 {geo_score:.0f} 分偏低，建议增加权威引用和数据支撑",
            priority="medium",
            expected_impact="GEO 评分提升 15-25 分",
        ))

    if rank_position > 0 and rank_position <= 10 and geo_score >= 60:
        actions.append(OptimizationAction(
            keyword=keyword,
            action_type="refresh_data",
            description=f"关键词「{keyword}」已在 Top 10，建议定期更新数据保持时效性",
            priority="low",
            expected_impact="维持当前排名，防止下滑",
        ))

    return actions
