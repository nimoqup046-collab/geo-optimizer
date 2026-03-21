"""Content calendar generator.

Inspired by seo-geo-claude-skills content-calendar skill — generates
prioritized content publishing schedules based on keyword research.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from services.llm_service import LLMService
from config import settings


@dataclass
class CalendarEntry:
    priority: str  # P0/P1/P2
    content_topic: str
    target_keywords: List[str] = field(default_factory=list)
    content_type: str = ""  # 白皮书/对比评测/指南/教程/工具清单/问答/案例
    target_platform: str = ""  # wechat/xiaohongshu/zhihu/video
    suggested_week: int = 0  # 建议发布周次（1-4）
    brief: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContentCalendarResult:
    topic: str
    entries: List[CalendarEntry] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "entries": [e.to_dict() for e in self.entries],
            "summary": self.summary,
        }


def _extract_json(text: str) -> Any:
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return json.loads(text.strip())


class ContentCalendarGenerator:
    """Generates prioritized content calendars based on keyword research and brand strategy."""

    def __init__(self, provider: str = "openrouter", model: Optional[str] = None):
        self.provider = provider
        self.model = model or settings.EXPERT_STRATEGY_MODEL

    async def generate(
        self,
        topic: str,
        keywords: Optional[List[str]] = None,
        brand_context: Optional[Dict[str, Any]] = None,
        weeks: int = 4,
    ) -> ContentCalendarResult:
        """Generate a content calendar for the given topic."""
        ctx = brand_context or {}
        brand = ctx.get("brand_name", "")
        industry = ctx.get("industry", "")

        kw_section = ""
        if keywords:
            kw_section = f"\n已有关键词列表：{', '.join(keywords[:20])}\n"

        prompt = (
            f"请为主题「{topic}」生成 {weeks} 周的内容日历排期。\n"
            f"行业：{industry or '通用'}，品牌：{brand or '未指定'}\n"
            f"{kw_section}\n"
            "要求：\n"
            "1. 按 P0（必做）/P1（重要）/P2（可选）优先级排序\n"
            "2. 覆盖多个平台：公众号(wechat)/小红书(xiaohongshu)/知乎(zhihu)/短视频(video)\n"
            "3. 内容类型多样化：白皮书/对比评测/指南/教程/工具清单/问答/案例\n"
            "4. 每周 2-4 篇内容\n\n"
            "以 JSON 数组返回，每项包含：\n"
            "```json\n"
            "[\n"
            "  {\n"
            '    "priority": "P0/P1/P2",\n'
            '    "content_topic": "内容主题",\n'
            '    "target_keywords": ["关键词1", "关键词2"],\n'
            '    "content_type": "指南/教程/问答/对比/清单/案例/白皮书",\n'
            '    "target_platform": "wechat/xiaohongshu/zhihu/video",\n'
            '    "suggested_week": 1,\n'
            '    "brief": "一句话内容概要"\n'
            "  }\n"
            "]\n"
            "```\n"
            "只返回 JSON 数组。"
        )

        try:
            async with LLMService(self.provider) as llm:
                result = await llm.generate(
                    messages=[
                        {"role": "system", "content": "你是内容营销规划专家。只返回 JSON 数组。"},
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=0.5,
                    max_tokens=3000,
                )

            items = _extract_json(result)
            entries = []
            for item in items:
                entries.append(CalendarEntry(
                    priority=item.get("priority", "P1"),
                    content_topic=item.get("content_topic", ""),
                    target_keywords=item.get("target_keywords", []),
                    content_type=item.get("content_type", ""),
                    target_platform=item.get("target_platform", ""),
                    suggested_week=item.get("suggested_week", 0),
                    brief=item.get("brief", ""),
                ))

            # Sort by priority
            priority_order = {"P0": 0, "P1": 1, "P2": 2}
            entries.sort(key=lambda e: (priority_order.get(e.priority, 9), e.suggested_week))

            cal = ContentCalendarResult(topic=topic, entries=entries)
            cal.summary = self._build_summary(cal)
            return cal

        except Exception:
            return ContentCalendarResult(topic=topic, summary="内容日历生成暂时不可用，请稍后重试。")

    def _build_summary(self, cal: ContentCalendarResult) -> str:
        if not cal.entries:
            return "未生成任何日历条目。"

        p0 = [e for e in cal.entries if e.priority == "P0"]
        p1 = [e for e in cal.entries if e.priority == "P1"]
        p2 = [e for e in cal.entries if e.priority == "P2"]

        platforms = {}
        for e in cal.entries:
            platforms[e.target_platform] = platforms.get(e.target_platform, 0) + 1

        lines = [
            f"## 内容日历摘要 — {cal.topic}",
            "",
            f"共规划 **{len(cal.entries)}** 篇内容：P0({len(p0)}) / P1({len(p1)}) / P2({len(p2)})",
            "",
            "### 平台分布",
        ]
        platform_names = {"wechat": "公众号", "xiaohongshu": "小红书", "zhihu": "知乎", "video": "短视频"}
        for plat, count in platforms.items():
            lines.append(f"- {platform_names.get(plat, plat)}：{count} 篇")

        if p0:
            lines.append("\n### P0 必做内容")
            for e in p0[:5]:
                lines.append(f"- 第{e.suggested_week}周 | {e.content_topic}（{e.content_type}）")

        return "\n".join(lines)
