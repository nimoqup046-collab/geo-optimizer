"""Page-level SEO audit service.

Inspired by seo-geo-claude-skills on-page-seo-auditor skill — provides
technical SEO scoring and actionable recommendations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import httpx

from services.llm_service import LLMService
from config import settings


@dataclass
class SEOIssue:
    severity: str  # P0/P1/P2
    category: str  # title/meta/headings/content/schema/performance
    current_state: str
    suggestion: str
    code_example: str = ""


@dataclass
class SEORecommendation:
    priority: int  # 1-5
    category: str
    action: str
    expected_impact: str


@dataclass
class SEOScoreCard:
    title_optimization: int = 0  # 0-100
    meta_description: int = 0
    heading_structure: int = 0
    content_quality: int = 0
    technical_seo: int = 0
    overall: int = 0

    def compute_overall(self) -> None:
        self.overall = int(
            self.title_optimization * 0.20
            + self.meta_description * 0.15
            + self.heading_structure * 0.20
            + self.content_quality * 0.30
            + self.technical_seo * 0.15
        )


@dataclass
class SEOAuditReport:
    target_url: str
    page_type: str = "unknown"
    scores: SEOScoreCard = field(default_factory=SEOScoreCard)
    strengths: List[str] = field(default_factory=list)
    issues: List[SEOIssue] = field(default_factory=list)
    recommendations: List[SEORecommendation] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_url": self.target_url,
            "page_type": self.page_type,
            "scores": asdict(self.scores),
            "strengths": self.strengths,
            "issues": [asdict(i) for i in self.issues],
            "recommendations": [asdict(r) for r in self.recommendations],
            "summary": self.summary,
        }


@dataclass
class ParsedPage:
    title: str = ""
    meta_description: str = ""
    meta_keywords: str = ""
    h1_tags: List[str] = field(default_factory=list)
    h2_tags: List[str] = field(default_factory=list)
    h3_tags: List[str] = field(default_factory=list)
    has_schema: bool = False
    schema_types: List[str] = field(default_factory=list)
    canonical_url: str = ""
    has_viewport: bool = False
    has_robots: bool = False
    word_count: int = 0
    img_count: int = 0
    img_without_alt: int = 0
    internal_links: int = 0
    external_links: int = 0


class SEOAuditor:
    """Page-level SEO audit service with code-level scoring and LLM-assisted evaluation."""

    def __init__(self, provider: str = "openrouter", model: Optional[str] = None):
        self.provider = provider
        self.model = model or settings.EXPERT_ANALYSIS_MODEL

    async def audit(self, url: str, page_type: str = "article") -> SEOAuditReport:
        """Audit a URL for SEO health."""
        report = SEOAuditReport(target_url=url, page_type=page_type)

        try:
            html = await self._fetch_page(url)
        except Exception as e:
            report.summary = f"无法抓取页面：{e}"
            return report

        parsed = self._parse_html(html)
        self._score_technical(report, parsed)
        await self._score_with_llm(report, parsed, html[:5000])
        report.scores.compute_overall()
        report.summary = self._build_summary(report)
        return report

    async def _fetch_page(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; GEOOptimizer/1.0; SEO Audit)"
            })
            resp.raise_for_status()
            return resp.text

    def _parse_html(self, html: str) -> ParsedPage:
        parsed = ParsedPage()

        # Title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if title_match:
            parsed.title = title_match.group(1).strip()

        # Meta description
        meta_desc = re.search(
            r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']',
            html, re.IGNORECASE
        )
        if not meta_desc:
            meta_desc = re.search(
                r'<meta\s+[^>]*content=["\'](.*?)["\'][^>]*name=["\']description["\']',
                html, re.IGNORECASE
            )
        if meta_desc:
            parsed.meta_description = meta_desc.group(1).strip()

        # Meta keywords
        meta_kw = re.search(
            r'<meta\s+[^>]*name=["\']keywords["\'][^>]*content=["\'](.*?)["\']',
            html, re.IGNORECASE
        )
        if meta_kw:
            parsed.meta_keywords = meta_kw.group(1).strip()

        # Headings
        parsed.h1_tags = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        parsed.h2_tags = re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.IGNORECASE | re.DOTALL)
        parsed.h3_tags = re.findall(r"<h3[^>]*>(.*?)</h3>", html, re.IGNORECASE | re.DOTALL)
        # Strip HTML tags from heading content
        tag_re = re.compile(r"<[^>]+>")
        parsed.h1_tags = [tag_re.sub("", h).strip() for h in parsed.h1_tags]
        parsed.h2_tags = [tag_re.sub("", h).strip() for h in parsed.h2_tags]
        parsed.h3_tags = [tag_re.sub("", h).strip() for h in parsed.h3_tags]

        # Schema
        schema_matches = re.findall(
            r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html, re.IGNORECASE | re.DOTALL
        )
        parsed.has_schema = len(schema_matches) > 0
        for sm in schema_matches:
            type_match = re.findall(r'"@type"\s*:\s*"([^"]+)"', sm)
            parsed.schema_types.extend(type_match)

        # Canonical
        canonical = re.search(
            r'<link\s+[^>]*rel=["\']canonical["\'][^>]*href=["\'](.*?)["\']',
            html, re.IGNORECASE
        )
        if canonical:
            parsed.canonical_url = canonical.group(1).strip()

        # Viewport
        parsed.has_viewport = bool(re.search(r'name=["\']viewport["\']', html, re.IGNORECASE))

        # Robots
        parsed.has_robots = bool(re.search(r'name=["\']robots["\']', html, re.IGNORECASE))

        # Word count (strip tags)
        text_content = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL)
        text_content = re.sub(r"<style[^>]*>.*?</style>", "", text_content, flags=re.IGNORECASE | re.DOTALL)
        text_content = re.sub(r"<[^>]+>", " ", text_content)
        text_content = re.sub(r"\s+", " ", text_content).strip()
        # Count both Chinese characters and English words
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text_content))
        english_words = len(re.findall(r"[a-zA-Z]+", text_content))
        parsed.word_count = chinese_chars + english_words

        # Images
        imgs = re.findall(r"<img\s+[^>]*>", html, re.IGNORECASE)
        parsed.img_count = len(imgs)
        parsed.img_without_alt = sum(1 for img in imgs if not re.search(r'alt=["\'][^"\']+["\']', img))

        # Links
        links = re.findall(r'<a\s+[^>]*href=["\'](.*?)["\']', html, re.IGNORECASE)
        for link in links:
            if link.startswith("http") and not link.startswith("#"):
                parsed.external_links += 1
            elif not link.startswith(("javascript:", "mailto:", "#")):
                parsed.internal_links += 1

        return parsed

    def _score_technical(self, report: SEOAuditReport, parsed: ParsedPage) -> None:
        # Title scoring
        title_score = 0
        if parsed.title:
            title_score += 40
            title_len = len(parsed.title)
            if 30 <= title_len <= 65:
                title_score += 40
            elif 20 <= title_len <= 80:
                title_score += 20
            if parsed.title != parsed.title.upper():
                title_score += 20
        report.scores.title_optimization = min(title_score, 100)

        if not parsed.title:
            report.issues.append(SEOIssue(
                severity="P0", category="title",
                current_state="页面缺少 <title> 标签",
                suggestion="添加包含目标关键词的 title 标签，长度控制在 30-65 字符",
                code_example="<title>目标关键词 - 品牌名</title>",
            ))
        elif len(parsed.title) > 65:
            report.issues.append(SEOIssue(
                severity="P1", category="title",
                current_state=f"标题过长（{len(parsed.title)} 字符）",
                suggestion="缩短到 30-65 字符以避免搜索结果中被截断",
            ))

        # Meta description scoring
        meta_score = 0
        if parsed.meta_description:
            meta_score += 50
            desc_len = len(parsed.meta_description)
            if 120 <= desc_len <= 160:
                meta_score += 50
            elif 80 <= desc_len <= 200:
                meta_score += 25
        report.scores.meta_description = min(meta_score, 100)

        if not parsed.meta_description:
            report.issues.append(SEOIssue(
                severity="P0", category="meta",
                current_state="缺少 meta description",
                suggestion="添加 120-160 字符的 meta description，包含目标关键词和行动号召",
                code_example='<meta name="description" content="您的页面描述...">',
            ))

        # Heading structure scoring
        heading_score = 0
        if parsed.h1_tags:
            if len(parsed.h1_tags) == 1:
                heading_score += 40
            else:
                heading_score += 20
                report.issues.append(SEOIssue(
                    severity="P1", category="headings",
                    current_state=f"页面有 {len(parsed.h1_tags)} 个 H1 标签",
                    suggestion="每个页面应只有 1 个 H1 标签",
                ))
        else:
            report.issues.append(SEOIssue(
                severity="P0", category="headings",
                current_state="页面缺少 H1 标签",
                suggestion="添加一个包含核心关键词的 H1 标签",
            ))
        if parsed.h2_tags:
            heading_score += 30
        if parsed.h3_tags:
            heading_score += 15
        if parsed.h2_tags and parsed.h3_tags:
            heading_score += 15
        report.scores.heading_structure = min(heading_score, 100)

        # Technical SEO scoring
        tech_score = 0
        if parsed.has_viewport:
            tech_score += 20
        else:
            report.issues.append(SEOIssue(
                severity="P1", category="technical",
                current_state="缺少 viewport meta 标签",
                suggestion="添加移动端适配 viewport 标签",
                code_example='<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            ))
        if parsed.canonical_url:
            tech_score += 20
        if parsed.has_schema:
            tech_score += 25
            report.strengths.append(f"已使用结构化数据（{', '.join(parsed.schema_types[:3])}）")
        else:
            report.issues.append(SEOIssue(
                severity="P1", category="schema",
                current_state="未检测到 Schema Markup",
                suggestion="添加 JSON-LD 结构化数据以增强搜索结果展示",
                code_example='<script type="application/ld+json">{"@context":"https://schema.org","@type":"Article",...}</script>',
            ))
        if parsed.img_without_alt == 0 and parsed.img_count > 0:
            tech_score += 15
            report.strengths.append("所有图片都有 alt 属性")
        elif parsed.img_without_alt > 0:
            report.issues.append(SEOIssue(
                severity="P2", category="images",
                current_state=f"{parsed.img_without_alt}/{parsed.img_count} 张图片缺少 alt 属性",
                suggestion="为所有图片添加描述性 alt 文本",
            ))
        if parsed.internal_links >= 3:
            tech_score += 10
        if parsed.word_count >= 300:
            tech_score += 10
        report.scores.technical_seo = min(tech_score, 100)

        # Strengths
        if parsed.title and 30 <= len(parsed.title) <= 65:
            report.strengths.append(f"标题长度合适（{len(parsed.title)} 字符）")
        if parsed.meta_description and 120 <= len(parsed.meta_description) <= 160:
            report.strengths.append("Meta description 长度合适")
        if parsed.word_count >= 1000:
            report.strengths.append(f"内容丰富（约 {parsed.word_count} 字）")

    async def _score_with_llm(self, report: SEOAuditReport, parsed: ParsedPage, html_excerpt: str) -> None:
        """Use LLM to evaluate content quality (the dimension hardest to score with code)."""
        prompt = (
            "请评估以下网页内容的 SEO 质量，给出 0-100 的内容质量评分。\n\n"
            f"页面标题：{parsed.title}\n"
            f"Meta Description：{parsed.meta_description}\n"
            f"H1：{', '.join(parsed.h1_tags[:3])}\n"
            f"H2：{', '.join(parsed.h2_tags[:5])}\n"
            f"字数：约 {parsed.word_count}\n\n"
            "评分维度：\n"
            "1. 内容与标题的相关性\n"
            "2. 信息深度和实用性\n"
            "3. 内容结构清晰度\n"
            "4. 可读性\n\n"
            '仅返回一个 JSON：{"score": 75, "reason": "简要理由"}'
        )
        try:
            async with LLMService(self.provider) as llm:
                result = await llm.generate(
                    messages=[
                        {"role": "system", "content": "你是 SEO 内容质量评估专家。只返回 JSON。"},
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=0.2,
                    max_tokens=200,
                )
            import json
            if "```" in result:
                result = result.split("```json")[-1].split("```")[0] if "```json" in result else result.split("```")[1].split("```")[0]
            data = json.loads(result.strip())
            report.scores.content_quality = min(max(data.get("score", 50), 0), 100)
        except Exception:
            report.scores.content_quality = 50

        # Generate recommendations based on issues
        for i, issue in enumerate(report.issues[:5]):
            report.recommendations.append(SEORecommendation(
                priority=i + 1,
                category=issue.category,
                action=issue.suggestion,
                expected_impact="高" if issue.severity == "P0" else "中" if issue.severity == "P1" else "低",
            ))

    def _build_summary(self, report: SEOAuditReport) -> str:
        overall = report.scores.overall
        grade = "A" if overall >= 85 else "B" if overall >= 70 else "C" if overall >= 55 else "D" if overall >= 40 else "F"

        p0_count = sum(1 for i in report.issues if i.severity == "P0")
        p1_count = sum(1 for i in report.issues if i.severity == "P1")

        lines = [
            f"## SEO 审计报告 — {report.target_url}",
            "",
            f"**综合评分：{overall}/100（等级 {grade}）**",
            "",
            f"| 维度 | 得分 |",
            f"|------|------|",
            f"| 标题优化 | {report.scores.title_optimization}/100 |",
            f"| Meta Description | {report.scores.meta_description}/100 |",
            f"| 标题结构 | {report.scores.heading_structure}/100 |",
            f"| 内容质量 | {report.scores.content_quality}/100 |",
            f"| 技术 SEO | {report.scores.technical_seo}/100 |",
            "",
            f"发现 **{p0_count}** 个严重问题（P0）和 **{p1_count}** 个一般问题（P1）。",
        ]

        if report.strengths:
            lines.append(f"\n### 优势")
            for s in report.strengths:
                lines.append(f"- {s}")

        return "\n".join(lines)
