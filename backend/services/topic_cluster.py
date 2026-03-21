"""Topic Cluster mapping engine.

Inspired by seo-geo-claude-skills topic-clusters skill — generates pillar pages
and cluster page mappings with internal linking strategies.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from services.llm_service import LLMService
from config import settings


@dataclass
class ClusterPage:
    title: str
    target_keyword: str
    content_type: str  # 指南/教程/问答/对比/清单/案例
    search_intent: str  # 信息型/交易型/导航型
    link_anchor_text: str = ""


@dataclass
class PillarPage:
    title: str
    core_keyword: str
    description: str = ""
    word_count_target: int = 2000


@dataclass
class TopicCluster:
    pillar: PillarPage
    cluster_pages: List[ClusterPage] = field(default_factory=list)
    internal_link_strategy: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pillar": asdict(self.pillar),
            "cluster_pages": [asdict(p) for p in self.cluster_pages],
            "internal_link_strategy": self.internal_link_strategy,
        }


@dataclass
class ClusterMapResult:
    topic: str
    clusters: List[TopicCluster] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "clusters": [c.to_dict() for c in self.clusters],
            "summary": self.summary,
        }


def _extract_json(text: str) -> Any:
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return json.loads(text.strip())


class TopicClusterEngine:
    """Generates Topic Cluster mappings: pillar pages + cluster pages + linking strategy."""

    def __init__(self, provider: str = "openrouter", model: Optional[str] = None):
        self.provider = provider
        self.model = model or settings.EXPERT_STRATEGY_MODEL

    async def build_clusters(
        self,
        topic: str,
        keywords: Optional[List[str]] = None,
        brand_context: Optional[Dict[str, Any]] = None,
        max_clusters: int = 3,
    ) -> ClusterMapResult:
        """Build topic clusters from a topic and optional keyword list."""
        ctx = brand_context or {}
        brand = ctx.get("brand_name", "")
        industry = ctx.get("industry", "")

        kw_section = ""
        if keywords:
            kw_section = f"\n已有关键词列表：{', '.join(keywords[:30])}\n"

        prompt = (
            f"请为主题「{topic}」构建 {max_clusters} 个 Topic Cluster（主题聚类）。\n"
            f"行业：{industry or '通用'}，品牌：{brand or '未指定'}\n"
            f"{kw_section}\n"
            "每个 Cluster 包含：\n"
            "1. 一个支柱页面（Pillar Page）— 全面覆盖核心主题的长文\n"
            "2. 5-8 个集群页面（Cluster Pages）— 深入探讨子话题\n"
            "3. 内链策略 — 如何在集群页面间建立链接\n\n"
            "以 JSON 数组返回，每项结构：\n"
            "```json\n"
            "[\n"
            "  {\n"
            '    "pillar": {\n'
            '      "title": "支柱页面标题",\n'
            '      "core_keyword": "核心关键词",\n'
            '      "description": "页面描述",\n'
            '      "word_count_target": 2000\n'
            "    },\n"
            '    "cluster_pages": [\n'
            "      {\n"
            '        "title": "集群页面标题",\n'
            '        "target_keyword": "目标关键词",\n'
            '        "content_type": "指南/教程/问答/对比/清单/案例",\n'
            '        "search_intent": "信息型/交易型/导航型",\n'
            '        "link_anchor_text": "链接到支柱页面的锚文本"\n'
            "      }\n"
            "    ],\n"
            '    "internal_link_strategy": "内链策略描述"\n'
            "  }\n"
            "]\n"
            "```\n"
            "只返回 JSON 数组，不要其他内容。"
        )

        try:
            async with LLMService(self.provider) as llm:
                result = await llm.generate(
                    messages=[
                        {"role": "system", "content": "你是 SEO 内容架构专家，擅长 Topic Cluster 策略。只返回 JSON 数组。"},
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=0.4,
                    max_tokens=3000,
                )

            items = _extract_json(result)
            clusters = []
            for item in items[:max_clusters]:
                pillar_data = item.get("pillar", {})
                pillar = PillarPage(
                    title=pillar_data.get("title", ""),
                    core_keyword=pillar_data.get("core_keyword", ""),
                    description=pillar_data.get("description", ""),
                    word_count_target=pillar_data.get("word_count_target", 2000),
                )
                pages = []
                for page_data in item.get("cluster_pages", []):
                    pages.append(ClusterPage(
                        title=page_data.get("title", ""),
                        target_keyword=page_data.get("target_keyword", ""),
                        content_type=page_data.get("content_type", "指南"),
                        search_intent=page_data.get("search_intent", "信息型"),
                        link_anchor_text=page_data.get("link_anchor_text", ""),
                    ))
                clusters.append(TopicCluster(
                    pillar=pillar,
                    cluster_pages=pages,
                    internal_link_strategy=item.get("internal_link_strategy", ""),
                ))

            result_obj = ClusterMapResult(topic=topic, clusters=clusters)
            result_obj.summary = self._build_summary(result_obj)
            return result_obj

        except Exception:
            return ClusterMapResult(topic=topic, summary="Topic Cluster 分析暂时不可用，请稍后重试。")

    def _build_summary(self, result: ClusterMapResult) -> str:
        if not result.clusters:
            return "未生成任何聚类结果。"

        total_pages = sum(len(c.cluster_pages) for c in result.clusters)
        lines = [
            f"## Topic Cluster 映射报告 — {result.topic}",
            "",
            f"共生成 **{len(result.clusters)}** 个主题聚类，包含 **{total_pages}** 个集群页面。",
            "",
        ]
        for i, cluster in enumerate(result.clusters, 1):
            lines.append(f"### 聚类 {i}：{cluster.pillar.title}")
            lines.append(f"- 核心关键词：{cluster.pillar.core_keyword}")
            lines.append(f"- 支柱页面目标字数：{cluster.pillar.word_count_target}")
            lines.append(f"- 集群页面数：{len(cluster.cluster_pages)}")
            if cluster.internal_link_strategy:
                lines.append(f"- 内链策略：{cluster.internal_link_strategy}")
            lines.append("")

        return "\n".join(lines)
