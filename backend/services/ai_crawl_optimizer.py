"""AI 爬取优化器 (AI Crawl Optimizer).

核心商业价值：将情感咨询内容转化为 AI 搜索引擎（ChatGPT、Perplexity、
豆包、Kimi）更易抓取和引用的格式。解决"AI 不抓取内容"或
"抓取了但没有给出品牌引用"两大核心痛点。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from services.llm_service import LLMService
from config import settings


@dataclass
class CrawlIssue:
    """AI 爬取问题项。"""
    category: str  # structure | citability | entity | freshness | accessibility
    severity: str  # P0 | P1 | P2
    description: str
    fix_suggestion: str
    fix_example: str = ""


@dataclass
class ContentRewrite:
    """AI 友好的内容重写版本。"""
    section_name: str
    original: str
    optimized: str
    changes: List[str] = field(default_factory=list)


@dataclass
class AICrawlReport:
    """AI 爬取优化报告。"""
    crawl_readiness_score: float = 0.0  # 0-100
    citation_readiness_score: float = 0.0  # 0-100
    issues: List[CrawlIssue] = field(default_factory=list)
    content_rewrites: List[ContentRewrite] = field(default_factory=list)
    qa_extractions: List[Dict[str, str]] = field(default_factory=list)
    key_assertions: List[str] = field(default_factory=list)  # 可被 AI 直接引用的断言
    optimization_checklist: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "crawl_readiness_score": self.crawl_readiness_score,
            "citation_readiness_score": self.citation_readiness_score,
            "issues": [asdict(i) for i in self.issues],
            "content_rewrites": [asdict(r) for r in self.content_rewrites],
            "qa_extractions": self.qa_extractions,
            "key_assertions": self.key_assertions,
            "optimization_checklist": self.optimization_checklist,
            "summary": self.summary,
        }


class AICrawlOptimizer:
    """优化内容以提升在 AI 搜索引擎中的可见性和可引用性。

    核心能力：
    1. 内容结构诊断：检测 AI 爬取障碍
    2. 断言前置优化：确保核心观点在前 50 字内
    3. Q&A 提取：将隐含问答转为显式结构
    4. 可引用断言生成：创建 AI 可直接引用的权威断言
    5. 实体信号注入：增加专业术语和权威引用
    """

    def __init__(self, provider: str = "openrouter", model: Optional[str] = None):
        self.provider = provider
        self.model = model or settings.EXPERT_GEO_MODEL

    async def optimize(
        self,
        content: str,
        brand_name: Optional[str] = None,
        target_queries: Optional[List[str]] = None,
        platform: str = "wechat",
    ) -> AICrawlReport:
        """执行完整的 AI 爬取优化分析。

        Args:
            content: 待优化内容
            brand_name: 品牌名称（用于品牌引用注入）
            target_queries: 目标用户查询（内容应能回答的问题）
            platform: 发布平台
        """
        report = AICrawlReport()

        # 1. 结构诊断
        issues = self._diagnose_structure(content)
        report.issues = issues

        # 2. LLM 辅助深度优化
        llm_analysis = await self._deep_optimize(
            content, brand_name, target_queries, platform
        )

        report.content_rewrites = llm_analysis.get("rewrites", [])
        report.qa_extractions = llm_analysis.get("qa_extractions", [])
        report.key_assertions = llm_analysis.get("key_assertions", [])
        report.optimization_checklist = llm_analysis.get("checklist", [])

        # 追加 LLM 发现的问题
        report.issues.extend(llm_analysis.get("additional_issues", []))

        # 3. 计算评分
        report.crawl_readiness_score = self._score_crawl_readiness(content, report)
        report.citation_readiness_score = self._score_citation_readiness(
            content, report
        )

        report.summary = self._build_summary(report)
        return report

    def _diagnose_structure(self, content: str) -> List[CrawlIssue]:
        """基于规则的结构诊断。"""
        issues: List[CrawlIssue] = []
        lines = content.strip().split("\n")

        # 检查是否有标题结构
        headings = [l for l in lines if l.strip().startswith("#")]
        if len(headings) < 2:
            issues.append(CrawlIssue(
                category="structure",
                severity="P0",
                description="缺少层级标题结构，AI 难以识别内容组织",
                fix_suggestion="添加 H2/H3 子标题，每 300 字至少一个标题",
                fix_example="## 婚姻修复的第一步：重建信任基础",
            ))

        # 检查段落长度
        long_paragraphs = [
            l for l in lines
            if len(l.strip()) > 300 and not l.strip().startswith("#")
        ]
        if long_paragraphs:
            issues.append(CrawlIssue(
                category="structure",
                severity="P1",
                description=f"存在 {len(long_paragraphs)} 个超长段落（>300字），影响 AI 提取",
                fix_suggestion="将长段落拆分为 100-200 字的小段落",
            ))

        # 检查是否有 Q&A 结构
        qa_patterns = ["?", "？", "Q:", "问:", "答:"]
        has_qa = any(
            any(p in l for p in qa_patterns)
            for l in lines
        )
        if not has_qa:
            issues.append(CrawlIssue(
                category="citability",
                severity="P0",
                description="缺少 Q&A 结构，AI 搜索引擎对问答格式有强烈偏好",
                fix_suggestion="在内容中嵌入 3-5 个用户高频问题的 Q&A 段落",
                fix_example="### Q：冷战一个月还有救吗？\n根据我们服务的 3000+ 案例统计...",
            ))

        # 检查是否有数据/统计
        import re
        data_patterns = [r'\d+%', r'\d+位', r'\d+例', r'\d+个案例', r'数据显示', r'研究表明']
        has_data = any(
            re.search(p, content) for p in data_patterns
        )
        if not has_data:
            issues.append(CrawlIssue(
                category="citability",
                severity="P1",
                description="缺少具体数据和统计信息，降低 AI 引用意愿",
                fix_suggestion="添加具体案例数据、百分比、研究结论",
                fix_example="根据我们对 3000+ 案例的追踪统计，采用情绪聚焦疗法的夫妻修复成功率达 72%。",
            ))

        # 检查首段是否包含核心断言
        first_para = lines[0] if lines else ""
        if len(first_para) > 100 or first_para.startswith("#"):
            # 首段过长或仅是标题，没有前置断言
            issues.append(CrawlIssue(
                category="citability",
                severity="P0",
                description="首段未包含核心断言，AI 引擎扫描前 2 句无法提取答案",
                fix_suggestion="在首段（前 50 字内）放置核心结论/答案",
                fix_example="核心结论：冷战超过一个月的婚姻，通过专业干预仍有 68% 的修复可能。",
            ))

        # 检查是否有列表/步骤
        list_patterns = [r'^\d+[\.\、]', r'^[-*•]', r'^第[一二三四五六七八九十]']
        has_list = any(
            re.search(p, l.strip()) for l in lines for p in list_patterns
        )
        if not has_list:
            issues.append(CrawlIssue(
                category="structure",
                severity="P1",
                description="缺少列表或步骤结构，降低 AI 可提取性",
                fix_suggestion="将关键信息组织为有序/无序列表",
            ))

        return issues

    async def _deep_optimize(
        self,
        content: str,
        brand_name: Optional[str],
        target_queries: Optional[List[str]],
        platform: str,
    ) -> Dict[str, Any]:
        """LLM 辅助的深度优化分析。"""
        queries_text = ""
        if target_queries:
            queries_text = "\n目标用户查询：\n" + "\n".join(
                f"- {q}" for q in target_queries
            )

        system_prompt = (
            "你是 AI 搜索引擎优化（GEO）专家。\n"
            "你的任务是将内容转化为 AI 搜索引擎更容易抓取和引用的格式。\n"
            "重点关注：断言前置、Q&A 结构、可引用断言、实体信号。\n"
            "以 JSON 返回分析结果。"
        )

        user_prompt = (
            f"品牌名称：{brand_name or '未指定'}\n"
            f"发布平台：{platform}\n"
            f"{queries_text}\n\n"
            f"待优化内容：\n{content[:4000]}\n\n"
            "请返回以下 JSON：\n```json\n"
            "{\n"
            '  "qa_extractions": [\n'
            '    {"question": "用户可能提问", "answer": "从内容中提炼的简洁答案（50字内）"}\n'
            "  ],\n"
            '  "key_assertions": [\n'
            '    "可被 AI 直接引用的权威断言（每条 30-50 字）"\n'
            "  ],\n"
            '  "rewrites": [\n'
            "    {\n"
            '      "section_name": "优化段落名",\n'
            '      "original": "原文片段",\n'
            '      "optimized": "优化后片段",\n'
            '      "changes": ["变更1", "变更2"]\n'
            "    }\n"
            "  ],\n"
            '  "additional_issues": [\n'
            "    {\n"
            '      "category": "structure|citability|entity|freshness",\n'
            '      "severity": "P0|P1|P2",\n'
            '      "description": "问题描述",\n'
            '      "fix_suggestion": "修复建议"\n'
            "    }\n"
            "  ],\n"
            '  "checklist": [\n'
            '    {"item": "检查项", "status": "pass|fail|warning", "note": "说明"}\n'
            "  ]\n"
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

            rewrites = []
            for rw in data.get("rewrites", []):
                rewrites.append(ContentRewrite(
                    section_name=rw.get("section_name", ""),
                    original=rw.get("original", ""),
                    optimized=rw.get("optimized", ""),
                    changes=rw.get("changes", []),
                ))

            additional_issues = []
            for issue in data.get("additional_issues", []):
                additional_issues.append(CrawlIssue(
                    category=issue.get("category", "structure"),
                    severity=issue.get("severity", "P1"),
                    description=issue.get("description", ""),
                    fix_suggestion=issue.get("fix_suggestion", ""),
                ))

            return {
                "rewrites": rewrites,
                "qa_extractions": data.get("qa_extractions", []),
                "key_assertions": data.get("key_assertions", []),
                "additional_issues": additional_issues,
                "checklist": data.get("checklist", []),
            }

        except Exception:
            return {
                "rewrites": [],
                "qa_extractions": [],
                "key_assertions": [],
                "additional_issues": [],
                "checklist": [],
            }

    def _score_crawl_readiness(
        self, content: str, report: AICrawlReport
    ) -> float:
        """计算 AI 爬取就绪度评分。"""
        score = 100.0

        # 按问题严重级别扣分
        for issue in report.issues:
            if issue.severity == "P0":
                score -= 15
            elif issue.severity == "P1":
                score -= 8
            else:
                score -= 3

        # 正向加分：有 Q&A 提取
        if report.qa_extractions:
            score += min(len(report.qa_extractions) * 3, 15)

        # 正向加分：有可引用断言
        if report.key_assertions:
            score += min(len(report.key_assertions) * 2, 10)

        return max(min(score, 100.0), 0.0)

    def _score_citation_readiness(
        self, content: str, report: AICrawlReport
    ) -> float:
        """计算被 AI 引用的就绪度评分。"""
        score = 50.0  # 基础分

        # 有断言前置
        lines = content.strip().split("\n")
        if lines and len(lines[0]) < 80 and not lines[0].startswith("#"):
            score += 15

        # 有 Q&A
        if report.qa_extractions:
            score += min(len(report.qa_extractions) * 4, 20)

        # 有可引用断言
        if report.key_assertions:
            score += min(len(report.key_assertions) * 3, 15)

        # 按 P0 问题数扣分
        p0_count = sum(1 for i in report.issues if i.severity == "P0")
        score -= p0_count * 10

        return max(min(score, 100.0), 0.0)

    def _build_summary(self, report: AICrawlReport) -> str:
        """生成可读的优化报告摘要。"""
        p0_count = sum(1 for i in report.issues if i.severity == "P0")
        p1_count = sum(1 for i in report.issues if i.severity == "P1")

        lines = [
            "## AI 爬取优化报告",
            "",
            f"**爬取就绪度**：{report.crawl_readiness_score:.0f}/100",
            f"**引用就绪度**：{report.citation_readiness_score:.0f}/100",
            f"**发现问题**：{len(report.issues)} 个（P0: {p0_count}, P1: {p1_count}）",
            "",
        ]

        if report.issues:
            lines.append("### 关键问题")
            for issue in sorted(report.issues, key=lambda x: x.severity):
                lines.append(f"- **[{issue.severity}]** {issue.description}")
                lines.append(f"  修复建议：{issue.fix_suggestion}")
                if issue.fix_example:
                    lines.append(f"  示例：`{issue.fix_example}`")
            lines.append("")

        if report.key_assertions:
            lines.append("### 可引用断言")
            for assertion in report.key_assertions:
                lines.append(f"- {assertion}")
            lines.append("")

        if report.qa_extractions:
            lines.append(f"### 提取的 Q&A（{len(report.qa_extractions)} 对）")
            for qa in report.qa_extractions[:5]:
                lines.append(f"**Q：{qa.get('question', '')}**")
                lines.append(f"A：{qa.get('answer', '')}")
                lines.append("")

        if report.optimization_checklist:
            lines.append("### 优化清单")
            for item in report.optimization_checklist:
                status_icon = {"pass": "✅", "fail": "❌", "warning": "⚠️"}.get(
                    item.get("status", ""), "⬜"
                )
                lines.append(f"- {status_icon} {item.get('item', '')}")
                if item.get("note"):
                    lines.append(f"  {item['note']}")

        return "\n".join(lines)


def _extract_json(text: str) -> Any:
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return json.loads(text.strip())
