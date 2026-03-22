"""Competitor content analysis — identifies content gaps and differentiation opportunities.

Default implementation uses mock data for development. When LLM is available,
uses LLM-based analysis for deeper competitor strategy insights.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

GAP_TYPES = {
    "uncovered": "未覆盖",
    "weak": "弱覆盖",
    "beatable": "可超越",
}

PLATFORMS = ["wechat", "xiaohongshu", "zhihu", "video"]


@dataclass
class CompetitorProfile:
    """Analysis result for a single competitor."""

    name: str
    platforms: List[str] = field(default_factory=list)
    content_themes: List[str] = field(default_factory=list)
    posting_frequency: str = ""
    avg_geo_score: float = 0.0
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "platforms": self.platforms,
            "content_themes": self.content_themes,
            "posting_frequency": self.posting_frequency,
            "avg_geo_score": round(self.avg_geo_score, 1),
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
        }


@dataclass
class ContentGap:
    """A content gap identified between us and competitors."""

    keyword: str
    gap_type: str  # uncovered / weak / beatable
    competitor_count: int  # how many competitors cover this
    opportunity_score: float  # 0-100
    recommended_action: str
    platform: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "keyword": self.keyword,
            "gap_type": self.gap_type,
            "gap_type_label": GAP_TYPES.get(self.gap_type, self.gap_type),
            "competitor_count": self.competitor_count,
            "opportunity_score": round(self.opportunity_score, 1),
            "recommended_action": self.recommended_action,
            "platform": self.platform,
        }


class MockCompetitorData:
    """Generate deterministic mock competitor analysis data."""

    def _seed(self, text: str) -> int:
        return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)

    def generate_profiles(
        self, competitor_names: List[str], keywords: List[str]
    ) -> List[CompetitorProfile]:
        profiles = []
        for name in competitor_names:
            seed = self._seed(name)
            num_platforms = 2 + (seed % 3)
            platforms = PLATFORMS[:num_platforms]
            themes = []
            for i, kw in enumerate(keywords[:4]):
                if (seed + i) % 3 != 0:
                    themes.append(kw)

            profiles.append(CompetitorProfile(
                name=name,
                platforms=platforms,
                content_themes=themes,
                posting_frequency=["每天1篇", "每周3篇", "每周1篇", "每月2篇"][seed % 4],
                avg_geo_score=30.0 + (seed % 50),
                strengths=self._gen_strengths(name, seed),
                weaknesses=self._gen_weaknesses(name, seed),
            ))
        return profiles

    def _gen_strengths(self, name: str, seed: int) -> List[str]:
        all_strengths = [
            "内容更新频率高", "专业术语使用准确", "数据引用丰富",
            "用户互动率高", "多平台覆盖全面", "品牌认知度高",
        ]
        count = 2 + (seed % 2)
        return [all_strengths[i % len(all_strengths)] for i in range(seed % len(all_strengths), seed % len(all_strengths) + count)]

    def _gen_weaknesses(self, name: str, seed: int) -> List[str]:
        all_weaknesses = [
            "缺少结构化数据", "AI 搜索适配不足", "内容时效性差",
            "缺乏权威引用", "互动引导不明确", "缺少问答格式内容",
        ]
        count = 1 + (seed % 2)
        start = (seed >> 4) % len(all_weaknesses)
        return [all_weaknesses[i % len(all_weaknesses)] for i in range(start, start + count)]

    def generate_gaps(
        self,
        keywords: List[str],
        competitor_names: List[str],
    ) -> List[ContentGap]:
        gaps = []
        for kw in keywords:
            for platform in PLATFORMS:
                p_seed = self._seed(f"{kw}:{platform}")
                gap_idx = p_seed % 4
                if gap_idx == 3:
                    continue  # no gap for this combo

                gap_type = ["uncovered", "weak", "beatable"][gap_idx % 3]
                comp_count = 1 + (p_seed % min(3, max(1, len(competitor_names))))
                opportunity = 40.0 + (p_seed % 60)

                actions = {
                    "uncovered": f"为「{kw}」创建{platform}专题内容，抢占空白市场",
                    "weak": f"优化已有「{kw}」内容的结构和数据支撑，超越竞品",
                    "beatable": f"升级「{kw}」内容的GEO评分，增加权威引用和问答结构",
                }

                gaps.append(ContentGap(
                    keyword=kw,
                    gap_type=gap_type,
                    competitor_count=comp_count,
                    opportunity_score=opportunity,
                    recommended_action=actions[gap_type],
                    platform=platform,
                ))
        return gaps


async def analyze_competitors(
    competitor_names: List[str],
    keywords: List[str],
) -> List[CompetitorProfile]:
    """Analyze competitor content strategies."""
    mock = MockCompetitorData()
    return mock.generate_profiles(competitor_names, keywords)


async def find_content_gaps(
    keywords: List[str],
    competitor_names: List[str],
) -> List[ContentGap]:
    """Identify content gaps between us and competitors."""
    mock = MockCompetitorData()
    return mock.generate_gaps(keywords, competitor_names)


async def generate_differentiation_strategy(
    brand_name: str,
    competitor_profiles: List[CompetitorProfile],
    content_gaps: List[ContentGap],
) -> Dict[str, Any]:
    """Generate a differentiation strategy based on competitor analysis."""
    # Aggregate weaknesses across competitors.
    all_weaknesses = []
    for profile in competitor_profiles:
        all_weaknesses.extend(profile.weaknesses)

    # Find high-opportunity gaps.
    high_opps = sorted(content_gaps, key=lambda g: g.opportunity_score, reverse=True)[:5]
    uncovered = [g for g in content_gaps if g.gap_type == "uncovered"]

    strategy = {
        "brand": brand_name,
        "competitor_count": len(competitor_profiles),
        "total_gaps": len(content_gaps),
        "uncovered_gaps": len(uncovered),
        "top_opportunities": [g.to_dict() for g in high_opps],
        "recommended_focus": [],
        "differentiation_angles": [],
    }

    # Generate focus areas.
    if uncovered:
        kws = list(set(g.keyword for g in uncovered[:3]))
        strategy["recommended_focus"].append(
            f"优先覆盖竞品未涉及的关键词：{'、'.join(kws)}"
        )

    common_weaknesses = list(set(all_weaknesses))[:3]
    if common_weaknesses:
        strategy["differentiation_angles"].append(
            f"竞品共同薄弱点：{'、'.join(common_weaknesses)}，可作为差异化突破口"
        )

    strategy["differentiation_angles"].extend([
        "强化 AI 搜索适配：增加结构化数据、FAQ 模块和权威引用",
        "提升内容时效性：定期更新数据和案例，保持内容新鲜度",
        "建立品牌专业壁垒：打造系列专题内容，形成知识图谱",
    ])

    return strategy
