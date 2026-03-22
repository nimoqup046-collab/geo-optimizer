"""Performance tracking service with GEO score correlation.

Provides content-feature-performance correlation analysis to close the
feedback loop between GEO optimization scores and real-world engagement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PerformanceCorrelation:
    """Correlation between a GEO score dimension and engagement metrics."""
    dimension: str
    avg_score: float
    avg_engagement: float
    sample_count: int
    insight: str


@dataclass
class ContentInsight:
    """Actionable insight derived from performance data analysis."""
    title: str
    description: str
    action_items: List[str]
    supporting_data: Dict[str, Any] = field(default_factory=dict)


def compute_engagement_score(metrics: Dict[str, Any]) -> float:
    """Compute a normalized engagement score from raw metrics.

    Weights: reads(30%) + likes(20%) + favorites(20%) + comments(15%) + shares(15%)
    Returns 0-100 normalized score.
    """
    reads = metrics.get("reads", 0)
    likes = metrics.get("likes", 0)
    favorites = metrics.get("favorites", 0)
    comments = metrics.get("comments", 0)
    shares = metrics.get("shares", 0)
    impressions = max(metrics.get("impressions", 1), 1)

    # Convert to rates (relative to impressions).
    read_rate = min(reads / impressions, 1.0) if impressions > 0 else 0
    like_rate = min(likes / max(reads, 1), 1.0)
    fav_rate = min(favorites / max(reads, 1), 1.0)
    comment_rate = min(comments / max(reads, 1), 1.0)
    share_rate = min(shares / max(reads, 1), 1.0)

    # Weighted sum, mapped to 0-100.
    raw = (
        read_rate * 0.30
        + like_rate * 0.20
        + fav_rate * 0.20
        + comment_rate * 0.15
        + share_rate * 0.15
    )
    return round(min(raw * 500, 100.0), 1)  # scale factor 500 for reasonable scores


def correlate_geo_and_performance(
    records: List[Dict[str, Any]],
) -> List[PerformanceCorrelation]:
    """Correlate GEO score dimensions with engagement metrics.

    Each record should contain:
    - geo_scores: dict with claim_density, citability, extractability, readability, overall
    - metrics: dict with reads, likes, favorites, comments, shares, impressions
    """
    if not records:
        return []

    dimensions = ["claim_density", "citability", "extractability", "readability", "overall"]
    correlations: List[PerformanceCorrelation] = []

    for dim in dimensions:
        scored_records = [
            r for r in records
            if r.get("geo_scores", {}).get(dim) is not None
        ]
        if not scored_records:
            continue

        avg_score = sum(r["geo_scores"][dim] for r in scored_records) / len(scored_records)
        engagements = [compute_engagement_score(r.get("metrics", {})) for r in scored_records]
        avg_eng = sum(engagements) / len(engagements) if engagements else 0

        # Generate insight based on score-engagement relationship.
        if avg_score >= 70 and avg_eng >= 50:
            insight = f"{dim} 高分内容表现优秀，继续保持该维度的优化策略"
        elif avg_score >= 70 and avg_eng < 50:
            insight = f"{dim} 评分高但效果一般，可能需要优化其他维度或调整分发策略"
        elif avg_score < 70 and avg_eng >= 50:
            insight = f"{dim} 评分偏低但效果不错，该维度可能对当前平台影响较小"
        else:
            insight = f"{dim} 评分和效果均需提升，建议重点优化该维度"

        correlations.append(PerformanceCorrelation(
            dimension=dim,
            avg_score=round(avg_score, 1),
            avg_engagement=round(avg_eng, 1),
            sample_count=len(scored_records),
            insight=insight,
        ))

    return correlations


def generate_insights(
    correlations: List[PerformanceCorrelation],
    platform_breakdown: Optional[Dict[str, Dict[str, float]]] = None,
) -> List[ContentInsight]:
    """Generate actionable insights from correlation data."""
    insights: List[ContentInsight] = []

    if not correlations:
        insights.append(ContentInsight(
            title="数据不足",
            description="当前效果数据不足以生成有意义的洞察，请先录入更多内容效果数据。",
            action_items=["录入至少5条内容的效果数据", "确保内容使用专家模式生成以获取GEO评分"],
        ))
        return insights

    # Find best and worst performing dimensions.
    by_engagement = sorted(correlations, key=lambda c: c.avg_engagement, reverse=True)
    best = by_engagement[0]
    worst = by_engagement[-1] if len(by_engagement) > 1 else None

    insights.append(ContentInsight(
        title=f"最佳表现维度：{best.dimension}",
        description=f"在 {best.sample_count} 条内容中，{best.dimension} 维度平均分 {best.avg_score}，"
                    f"对应平均互动得分 {best.avg_engagement}。",
        action_items=[
            f"继续保持 {best.dimension} 维度的优化策略",
            "将该维度的优化方法复用到其他内容",
        ],
        supporting_data={
            "dimension": best.dimension,
            "avg_score": best.avg_score,
            "avg_engagement": best.avg_engagement,
        },
    ))

    if worst and worst.dimension != best.dimension:
        insights.append(ContentInsight(
            title=f"需改进维度：{worst.dimension}",
            description=f"{worst.dimension} 维度平均分 {worst.avg_score}，"
                        f"平均互动得分仅 {worst.avg_engagement}。",
            action_items=[
                f"重点提升 {worst.dimension} 维度的内容质量",
                "参考专家团队的优化建议",
                "使用 GEO 优化策略工具进行针对性优化",
            ],
            supporting_data={
                "dimension": worst.dimension,
                "avg_score": worst.avg_score,
                "avg_engagement": worst.avg_engagement,
            },
        ))

    # Platform-specific insights.
    if platform_breakdown:
        best_platform = max(
            platform_breakdown.items(),
            key=lambda x: x[1].get("avg_engagement", 0),
            default=None,
        )
        if best_platform:
            insights.append(ContentInsight(
                title=f"最佳平台：{best_platform[0]}",
                description=f"{best_platform[0]} 平台平均互动得分最高 ({best_platform[1].get('avg_engagement', 0)})。",
                action_items=[
                    f"优先为 {best_platform[0]} 平台生产内容",
                    "分析该平台成功内容的共同特征",
                ],
                supporting_data=best_platform[1],
            ))

    return insights
