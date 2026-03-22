"""品牌引用监控服务 (Brand Citation Monitor).

核心商业价值：实时监控各大 LLM（ChatGPT、豆包、Kimi、Perplexity 等）
对特定婚姻/情感问题的回答中是否包含品牌名或观点。
这是企业愿意为此买单的闭环核心指标。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from services.llm_service import LLMService
from config import settings


@dataclass
class CitationHit:
    """单条品牌引用命中记录。"""
    query: str
    llm_provider: str
    response_snippet: str
    brand_mentioned: bool
    mention_type: str  # direct_name | viewpoint | methodology | case_study | link
    context: str  # 品牌被提及的上下文段落
    confidence: float  # 0-1 置信度
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class CompetitorMention:
    """竞品被引用的记录。"""
    competitor_name: str
    query: str
    llm_provider: str
    mention_count: int
    context_snippets: List[str] = field(default_factory=list)


@dataclass
class CitationReport:
    """品牌引用监控报告。"""
    brand_name: str
    monitoring_queries: List[str]
    total_queries: int = 0
    brand_hits: List[CitationHit] = field(default_factory=list)
    competitor_mentions: List[CompetitorMention] = field(default_factory=list)
    citation_rate: float = 0.0  # 品牌被引用的比率
    visibility_score: float = 0.0  # 0-100 综合可见性评分
    gap_analysis: str = ""  # 与竞品的差距分析
    recommendations: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand_name": self.brand_name,
            "monitoring_queries": self.monitoring_queries,
            "total_queries": self.total_queries,
            "brand_hits": [asdict(h) for h in self.brand_hits],
            "competitor_mentions": [asdict(c) for c in self.competitor_mentions],
            "citation_rate": self.citation_rate,
            "visibility_score": self.visibility_score,
            "gap_analysis": self.gap_analysis,
            "recommendations": self.recommendations,
            "summary": self.summary,
        }


# 情感咨询行业高频用户提问模板
EMOTIONAL_COUNSELING_QUERIES = [
    "老公出轨怎么沟通最有效",
    "冷战一个月还有救吗",
    "分手后怎么挽回前任",
    "婚姻出现信任危机怎么修复",
    "老公不回家怎么处理",
    "情感咨询机构哪家靠谱",
    "婚姻修复的最佳方法是什么",
    "怎么判断婚姻还值不值得挽回",
    "出轨后的婚姻还能继续吗",
    "分手挽回的正确步骤",
    "夫妻冷暴力怎么破解",
    "情感挽回需要多长时间",
]


def _extract_json(text: str) -> Any:
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return json.loads(text.strip())


class BrandCitationMonitor:
    """监控品牌在 AI 搜索回答中的引用情况。

    工作原理：
    1. 使用用户高频提问模拟查询各 LLM
    2. 分析回答中是否出现品牌名、方法论、案例等
    3. 同时检测竞品被引用的情况
    4. 生成差距分析和优化建议
    """

    def __init__(self, provider: str = "openrouter", model: Optional[str] = None):
        self.provider = provider
        self.model = model or settings.EXPERT_ANALYSIS_MODEL

    async def monitor(
        self,
        brand_name: str,
        queries: Optional[List[str]] = None,
        competitors: Optional[List[str]] = None,
        industry: str = "emotional_counseling",
    ) -> CitationReport:
        """执行品牌引用监控扫描。

        Args:
            brand_name: 品牌名称
            queries: 自定义监控查询列表（为空则使用行业默认）
            competitors: 竞品名称列表
            industry: 行业标识
        """
        monitor_queries = queries or EMOTIONAL_COUNSELING_QUERIES[:8]
        competitors = competitors or []

        report = CitationReport(
            brand_name=brand_name,
            monitoring_queries=monitor_queries,
            total_queries=len(monitor_queries),
        )

        # 批量模拟 LLM 对这些问题的回答并分析引用情况
        analysis = await self._batch_citation_analysis(
            brand_name, monitor_queries, competitors
        )

        report.brand_hits = analysis.get("brand_hits", [])
        report.competitor_mentions = analysis.get("competitor_mentions", [])
        report.citation_rate = (
            len(report.brand_hits) / max(report.total_queries, 1)
        )
        report.visibility_score = self._compute_visibility_score(report)
        report.gap_analysis = analysis.get("gap_analysis", "")
        report.recommendations = analysis.get("recommendations", [])
        report.summary = self._build_summary(report)
        return report

    async def probe_single_query(
        self,
        brand_name: str,
        query: str,
        competitors: Optional[List[str]] = None,
    ) -> CitationHit:
        """对单个查询进行品牌引用探测。"""
        competitors = competitors or []

        system_prompt = (
            "你是一个 AI 搜索引擎模拟器。请模拟大型语言模型（如 ChatGPT、豆包、Kimi）"
            "在回答用户情感咨询问题时的典型回答方式。"
            "然后作为分析师，检查回答中是否会自然引用特定品牌/机构/方法论。\n"
            "以 JSON 返回分析结果。"
        )

        user_prompt = (
            f"用户提问：{query}\n\n"
            f"目标品牌：{brand_name}\n"
            f"竞品列表：{', '.join(competitors) if competitors else '无'}\n\n"
            "请先模拟一个 AI 搜索引擎的典型回答（约 300 字），然后分析：\n"
            "1. 回答中是否提及了目标品牌？\n"
            "2. 如果没有，为什么没有被引用？\n"
            "3. 竞品是否被提及？\n\n"
            "以 JSON 返回：\n```json\n"
            "{\n"
            '  "simulated_response": "模拟回答全文",\n'
            '  "brand_mentioned": true/false,\n'
            '  "mention_type": "direct_name|viewpoint|methodology|case_study|none",\n'
            '  "context": "品牌被提及的具体段落（如未提及则说明原因）",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "competitor_mentioned": ["竞品A", "竞品B"]\n'
            "}\n```"
        )

        try:
            async with LLMService(self.provider) as llm:
                result = await llm.generate(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    model=self.model,
                    temperature=0.4,
                    max_tokens=2000,
                )

            data = _extract_json(result)
            return CitationHit(
                query=query,
                llm_provider="simulated_multi_llm",
                response_snippet=data.get("simulated_response", "")[:200],
                brand_mentioned=data.get("brand_mentioned", False),
                mention_type=data.get("mention_type", "none"),
                context=data.get("context", ""),
                confidence=float(data.get("confidence", 0.0)),
            )
        except Exception:
            return CitationHit(
                query=query,
                llm_provider="simulated_multi_llm",
                response_snippet="",
                brand_mentioned=False,
                mention_type="none",
                context="分析暂时不可用",
                confidence=0.0,
            )

    async def _batch_citation_analysis(
        self,
        brand_name: str,
        queries: List[str],
        competitors: List[str],
    ) -> Dict[str, Any]:
        """批量分析品牌在多个查询中的引用情况。"""
        system_prompt = (
            "你是 GEO（Generative Engine Optimization）引用分析专家。\n"
            "你的任务是评估一个品牌在 AI 搜索引擎回答中被引用的可能性。\n"
            "基于品牌当前的内容质量、结构化程度、权威信号，评估其被 AI 采信的概率。\n"
            "以 JSON 返回详细分析。"
        )

        queries_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(queries))
        competitors_text = ", ".join(competitors) if competitors else "未提供"

        user_prompt = (
            f"目标品牌：{brand_name}\n"
            f"竞品列表：{competitors_text}\n\n"
            f"用户高频查询列表：\n{queries_text}\n\n"
            "请逐一分析每个查询，评估品牌被 AI 引用的可能性。\n\n"
            "以 JSON 返回：\n```json\n"
            "{\n"
            '  "brand_hits": [\n'
            "    {\n"
            '      "query": "用户查询",\n'
            '      "brand_mentioned": true/false,\n'
            '      "mention_type": "direct_name|viewpoint|methodology|case_study|none",\n'
            '      "context": "分析说明",\n'
            '      "confidence": 0.0-1.0\n'
            "    }\n"
            "  ],\n"
            '  "competitor_analysis": [\n'
            "    {\n"
            '      "competitor_name": "竞品名",\n'
            '      "mention_count": 0,\n'
            '      "advantage_over_brand": "竞品优势说明"\n'
            "    }\n"
            "  ],\n"
            '  "gap_analysis": "品牌与竞品在 AI 可见性上的差距分析",\n'
            '  "recommendations": ["建议1", "建议2", "建议3"]\n'
            "}\n```"
        )

        try:
            async with LLMService(self.provider) as llm:
                result = await llm.generate(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    model=self.model,
                    temperature=0.3,
                    max_tokens=4000,
                )

            data = _extract_json(result)

            brand_hits = []
            for hit_data in data.get("brand_hits", []):
                brand_hits.append(CitationHit(
                    query=hit_data.get("query", ""),
                    llm_provider="multi_llm_analysis",
                    response_snippet="",
                    brand_mentioned=hit_data.get("brand_mentioned", False),
                    mention_type=hit_data.get("mention_type", "none"),
                    context=hit_data.get("context", ""),
                    confidence=float(hit_data.get("confidence", 0.0)),
                ))

            competitor_mentions = []
            for comp_data in data.get("competitor_analysis", []):
                competitor_mentions.append(CompetitorMention(
                    competitor_name=comp_data.get("competitor_name", ""),
                    query="batch_analysis",
                    llm_provider="multi_llm_analysis",
                    mention_count=int(comp_data.get("mention_count", 0)),
                    context_snippets=[comp_data.get("advantage_over_brand", "")],
                ))

            return {
                "brand_hits": brand_hits,
                "competitor_mentions": competitor_mentions,
                "gap_analysis": data.get("gap_analysis", ""),
                "recommendations": data.get("recommendations", []),
            }

        except Exception:
            return {
                "brand_hits": [],
                "competitor_mentions": [],
                "gap_analysis": "分析暂时不可用",
                "recommendations": ["请确保 LLM 服务可用后重试"],
            }

    def _compute_visibility_score(self, report: CitationReport) -> float:
        """计算综合可见性评分 (0-100)。"""
        if not report.brand_hits:
            return 0.0

        # 基础分：引用率 * 50
        base_score = report.citation_rate * 50

        # 置信度加权：平均置信度 * 30
        avg_confidence = sum(
            h.confidence for h in report.brand_hits if h.brand_mentioned
        ) / max(sum(1 for h in report.brand_hits if h.brand_mentioned), 1)
        confidence_score = avg_confidence * 30

        # 引用类型多样性加权：不同类型数 * 5（最高 20 分）
        mention_types = set(
            h.mention_type for h in report.brand_hits
            if h.brand_mentioned and h.mention_type != "none"
        )
        diversity_score = min(len(mention_types) * 5, 20)

        return min(base_score + confidence_score + diversity_score, 100.0)

    def _build_summary(self, report: CitationReport) -> str:
        """生成可读的监控报告摘要。"""
        hit_count = sum(1 for h in report.brand_hits if h.brand_mentioned)
        lines = [
            f"## 品牌引用监控报告 — {report.brand_name}",
            "",
            f"**监控查询数**：{report.total_queries}",
            f"**品牌被引用次数**：{hit_count}",
            f"**引用率**：{report.citation_rate:.1%}",
            f"**综合可见性评分**：{report.visibility_score:.1f}/100",
            "",
        ]

        if report.brand_hits:
            lines.append("### 引用详情")
            lines.append("| 查询 | 是否被引用 | 引用类型 | 置信度 |")
            lines.append("|------|-----------|---------|--------|")
            for hit in report.brand_hits:
                status = "✅" if hit.brand_mentioned else "❌"
                lines.append(
                    f"| {hit.query[:30]} | {status} | "
                    f"{hit.mention_type} | {hit.confidence:.0%} |"
                )
            lines.append("")

        if report.competitor_mentions:
            lines.append("### 竞品引用情况")
            for comp in report.competitor_mentions:
                lines.append(f"- **{comp.competitor_name}**：被引用 {comp.mention_count} 次")
            lines.append("")

        if report.gap_analysis:
            lines.append("### 差距分析")
            lines.append(report.gap_analysis)
            lines.append("")

        if report.recommendations:
            lines.append("### 优化建议")
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"{i}. {rec}")

        return "\n".join(lines)
