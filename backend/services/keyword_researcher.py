"""Multi-dimensional keyword research engine.

Inspired by seo-geo-claude-skills keyword-research skill — produces rich,
structured research reports with trending analysis, commercial evaluation,
long-tail discovery, topic clustering, GEO suggestions, and content calendar.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from services.llm_service import LLMService
from services.analysis_engine import classify_keyword, estimate_difficulty, has_qa_structure
from config import settings


@dataclass
class TrendingKeyword:
    keyword: str
    search_intent: str  # 信息型/交易型/导航型
    heat_level: int  # 1-5
    commercial_value: str  # 高/中/低
    reasoning: str = ""


@dataclass
class CommercialKeyword:
    keyword: str
    buyer_stage: str  # 认知/考虑/决策
    competition: str  # 高/中/低
    content_angle: str = ""


@dataclass
class LongTailKeyword:
    keyword: str
    parent_keyword: str
    search_intent: str
    ai_citation_potential: str  # 高/中/低
    suggested_format: str = ""  # 问答/指南/对比/清单


@dataclass
class GEOSuggestion:
    keyword: str
    strategy: str  # citation_enhancement/statistics_addition/qa_structuring/answer_frontloading/entity_enrichment
    action: str
    expected_improvement: str


@dataclass
class KeywordResearchReport:
    topic: str
    brand_context: Dict[str, Any]
    trending_keywords: List[TrendingKeyword] = field(default_factory=list)
    commercial_keywords: List[CommercialKeyword] = field(default_factory=list)
    long_tail_opportunities: List[LongTailKeyword] = field(default_factory=list)
    geo_suggestions: List[GEOSuggestion] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "trending_keywords": [asdict(k) for k in self.trending_keywords],
            "commercial_keywords": [asdict(k) for k in self.commercial_keywords],
            "long_tail_opportunities": [asdict(k) for k in self.long_tail_opportunities],
            "geo_suggestions": [asdict(s) for s in self.geo_suggestions],
            "summary": self.summary,
        }


def _extract_json(text: str) -> Any:
    """Extract JSON from LLM response that may contain markdown fences."""
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return json.loads(text.strip())


class KeywordResearcher:
    """Enhanced keyword research engine combining local analysis with LLM deep analysis."""

    def __init__(self, provider: str = "openrouter", model: Optional[str] = None):
        self.provider = provider
        self.model = model or settings.EXPERT_ANALYSIS_MODEL

    async def research(
        self,
        topic: str,
        brand_context: Optional[Dict[str, Any]] = None,
    ) -> KeywordResearchReport:
        """Execute comprehensive keyword research, outputting a multi-dimensional report."""
        ctx = brand_context or {}
        report = KeywordResearchReport(topic=topic, brand_context=ctx)

        trending, commercial, long_tail, geo = await asyncio.gather(
            self._analyze_trends(topic, ctx),
            self._analyze_commercial(topic, ctx),
            self._find_long_tail(topic, ctx),
            self._geo_suggestions(topic, ctx),
            return_exceptions=True,
        )

        if isinstance(trending, list):
            report.trending_keywords = trending
        if isinstance(commercial, list):
            report.commercial_keywords = commercial
        if isinstance(long_tail, list):
            report.long_tail_opportunities = long_tail
        if isinstance(geo, list):
            report.geo_suggestions = geo

        # Build summary
        report.summary = self._build_summary(report)

        # Enrich with local analysis
        self._enrich_with_local_analysis(report, ctx)

        return report

    async def _analyze_trends(self, topic: str, ctx: Dict[str, Any]) -> List[TrendingKeyword]:
        brand = ctx.get("brand_name", "")
        industry = ctx.get("industry", "")
        prompt = (
            f"请为主题「{topic}」生成 8-12 个热门趋势关键词。\n"
            f"行业：{industry or '通用'}\n"
            f"品牌：{brand or '未指定'}\n\n"
            "要求：\n"
            "1. 涵盖信息型、交易型、导航型搜索意图\n"
            "2. 包含当前热门趋势和新兴话题\n"
            "3. 评估每个关键词的热度和商业价值\n\n"
            "以 JSON 数组返回，每项包含：\n"
            '{"keyword": "...", "search_intent": "信息型/交易型/导航型", '
            '"heat_level": 1-5, "commercial_value": "高/中/低", "reasoning": "..."}\n'
            "只返回 JSON，不要其他内容。"
        )
        try:
            async with LLMService(self.provider) as llm:
                result = await llm.generate(
                    messages=[
                        {"role": "system", "content": "你是关键词研究专家。只返回 JSON 数组。"},
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=0.4,
                    max_tokens=2000,
                )
            items = _extract_json(result)
            return [TrendingKeyword(**item) for item in items[:12]]
        except Exception:
            return []

    async def _analyze_commercial(self, topic: str, ctx: Dict[str, Any]) -> List[CommercialKeyword]:
        brand = ctx.get("brand_name", "")
        industry = ctx.get("industry", "")
        prompt = (
            f"请为主题「{topic}」生成 6-10 个核心商业关键词。\n"
            f"行业：{industry or '通用'}，品牌：{brand or '未指定'}\n\n"
            "要求：覆盖买家旅程的认知/考虑/决策三个阶段。\n\n"
            "以 JSON 数组返回，每项包含：\n"
            '{"keyword": "...", "buyer_stage": "认知/考虑/决策", '
            '"competition": "高/中/低", "content_angle": "推荐的内容切入角度"}\n'
            "只返回 JSON。"
        )
        try:
            async with LLMService(self.provider) as llm:
                result = await llm.generate(
                    messages=[
                        {"role": "system", "content": "你是商业关键词分析专家。只返回 JSON 数组。"},
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=0.4,
                    max_tokens=2000,
                )
            items = _extract_json(result)
            return [CommercialKeyword(**item) for item in items[:10]]
        except Exception:
            return []

    async def _find_long_tail(self, topic: str, ctx: Dict[str, Any]) -> List[LongTailKeyword]:
        industry = ctx.get("industry", "")
        prompt = (
            f"请为主题「{topic}」发掘 8-15 个长尾关键词机会。\n"
            f"行业：{industry or '通用'}\n\n"
            "要求：\n"
            "1. 包含问答型（如何/怎么/为什么）和对比型（vs/对比/哪个好）\n"
            "2. 评估每个长尾词的 AI 引用潜力\n"
            "3. 建议最适合的内容格式\n\n"
            "以 JSON 数组返回，每项包含：\n"
            '{"keyword": "...", "parent_keyword": "对应的核心词", '
            '"search_intent": "信息型/交易型", "ai_citation_potential": "高/中/低", '
            '"suggested_format": "问答/指南/对比/清单/教程"}\n'
            "只返回 JSON。"
        )
        try:
            async with LLMService(self.provider) as llm:
                result = await llm.generate(
                    messages=[
                        {"role": "system", "content": "你是长尾关键词挖掘专家。只返回 JSON 数组。"},
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=0.5,
                    max_tokens=2000,
                )
            items = _extract_json(result)
            return [LongTailKeyword(**item) for item in items[:15]]
        except Exception:
            return []

    async def _geo_suggestions(self, topic: str, ctx: Dict[str, Any]) -> List[GEOSuggestion]:
        brand = ctx.get("brand_name", "")
        industry = ctx.get("industry", "")
        prompt = (
            f"请为主题「{topic}」提供 5-8 条 GEO（生成式引擎优化）建议。\n"
            f"行业：{industry or '通用'}，品牌：{brand or '未指定'}\n\n"
            "GEO 策略类型包括：\n"
            "- citation_enhancement（引用增强）\n"
            "- statistics_addition（统计增强）\n"
            "- qa_structuring（问答结构化）\n"
            "- answer_frontloading（断言前置）\n"
            "- entity_enrichment（实体丰富）\n\n"
            "以 JSON 数组返回，每项包含：\n"
            '{"keyword": "目标关键词", "strategy": "策略类型", '
            '"action": "具体操作建议", "expected_improvement": "预期效果"}\n'
            "只返回 JSON。"
        )
        try:
            async with LLMService(self.provider) as llm:
                result = await llm.generate(
                    messages=[
                        {"role": "system", "content": "你是 GEO 优化策略专家。只返回 JSON 数组。"},
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=0.3,
                    max_tokens=2000,
                )
            items = _extract_json(result)
            return [GEOSuggestion(**item) for item in items[:8]]
        except Exception:
            return []

    def _enrich_with_local_analysis(self, report: KeywordResearchReport, ctx: Dict[str, Any]) -> None:
        """Enrich report with local analysis engine results."""
        brand_name = ctx.get("brand_name", "")
        competitors = ctx.get("competitors", [])

        all_keywords = (
            [k.keyword for k in report.trending_keywords]
            + [k.keyword for k in report.commercial_keywords]
            + [k.keyword for k in report.long_tail_opportunities]
        )

        for kw_str in all_keywords:
            category = classify_keyword(kw_str, brand_name, competitors)
            difficulty = estimate_difficulty(kw_str)
            qa = has_qa_structure(kw_str)
            # Enrich matching objects
            for tk in report.trending_keywords:
                if tk.keyword == kw_str and not tk.reasoning:
                    tk.reasoning = f"分类={category}, 难度={difficulty}, QA={qa}"
            for lt in report.long_tail_opportunities:
                if lt.keyword == kw_str and qa and lt.ai_citation_potential != "高":
                    lt.ai_citation_potential = "高"

    def _build_summary(self, report: KeywordResearchReport) -> str:
        trending_count = len(report.trending_keywords)
        commercial_count = len(report.commercial_keywords)
        long_tail_count = len(report.long_tail_opportunities)
        geo_count = len(report.geo_suggestions)

        high_heat = [k for k in report.trending_keywords if k.heat_level >= 4]
        high_commercial = [k for k in report.commercial_keywords if k.competition == "低"]
        high_ai = [k for k in report.long_tail_opportunities if k.ai_citation_potential == "高"]

        lines = [
            f"## 关键词研究报告摘要 — {report.topic}",
            "",
            f"- 发现 **{trending_count}** 个趋势关键词（{len(high_heat)} 个高热度）",
            f"- 发现 **{commercial_count}** 个商业关键词（{len(high_commercial)} 个低竞争机会）",
            f"- 发现 **{long_tail_count}** 个长尾机会（{len(high_ai)} 个高 AI 引用潜力）",
            f"- 生成 **{geo_count}** 条 GEO 优化建议",
        ]

        if high_heat:
            lines.append("\n### 高热度关键词 TOP 3")
            for k in high_heat[:3]:
                lines.append(f"- {k.keyword}（热度 {k.heat_level}/5，{k.search_intent}）")

        if high_ai:
            lines.append("\n### 高 AI 引用潜力 TOP 3")
            for k in high_ai[:3]:
                lines.append(f"- {k.keyword}（建议格式：{k.suggested_format}）")

        return "\n".join(lines)
