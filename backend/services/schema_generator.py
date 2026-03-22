"""Schema 结构化数据生成器 (Schema.org Generator).

核心商业价值：将感性的情感文章转化为 AI 易于抓取的结构化数据格式，
包括 FAQ Schema、HowTo Schema、Article Schema、Q&A Schema 等。
结构化数据是提升 AI 引擎可见性的基础设施层。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from services.llm_service import LLMService
from config import settings


@dataclass
class SchemaMarkup:
    """单个 Schema 标记。"""
    schema_type: str  # FAQPage | HowTo | Article | QAPage | Person | Organization
    purpose: str
    json_ld: Dict[str, Any] = field(default_factory=dict)
    html_snippet: str = ""  # 可直接嵌入页面的 <script> 标签


@dataclass
class SchemaGenerationResult:
    """Schema 生成结果。"""
    source_content: str
    content_type: str  # article | qa | guide | case_study
    schemas: List[SchemaMarkup] = field(default_factory=list)
    llms_txt: str = ""  # llms.txt 文件内容建议
    ai_meta_tags: List[str] = field(default_factory=list)  # AI 友好的 meta 标签
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_type": self.content_type,
            "schemas": [asdict(s) for s in self.schemas],
            "llms_txt": self.llms_txt,
            "ai_meta_tags": self.ai_meta_tags,
            "summary": self.summary,
        }


def _extract_json(text: str) -> Any:
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return json.loads(text.strip())


class SchemaGenerator:
    """将内容转化为 AI 引擎友好的结构化数据。

    支持的 Schema 类型：
    - FAQPage：问答类内容
    - HowTo：指南/步骤类内容
    - Article：文章类内容
    - QAPage：单问单答类内容
    - Person：专家实体
    - Organization：机构实体
    """

    def __init__(self, provider: str = "openrouter", model: Optional[str] = None):
        self.provider = provider
        self.model = model or settings.EXPERT_GEO_MODEL

    async def generate_schemas(
        self,
        content: str,
        content_type: str = "article",
        brand_name: Optional[str] = None,
        author_name: Optional[str] = None,
        page_url: Optional[str] = None,
    ) -> SchemaGenerationResult:
        """为内容生成全套结构化数据。

        Args:
            content: 原始内容文本
            content_type: 内容类型 (article/qa/guide/case_study)
            brand_name: 品牌名称
            author_name: 作者名称
            page_url: 页面 URL
        """
        result = SchemaGenerationResult(
            source_content=content[:200],
            content_type=content_type,
        )

        # 自动检测并生成适合的 Schema
        schemas = await self._auto_detect_and_generate(
            content, content_type, brand_name, author_name, page_url
        )
        result.schemas = schemas

        # 生成 llms.txt 建议
        result.llms_txt = self._generate_llms_txt(brand_name or "")

        # 生成 AI 友好的 meta 标签
        result.ai_meta_tags = self._generate_ai_meta_tags(
            content, brand_name, author_name
        )

        result.summary = self._build_summary(result)
        return result

    async def extract_faq_schema(
        self,
        content: str,
        max_questions: int = 8,
    ) -> SchemaMarkup:
        """从内容中提取 FAQ 并生成 FAQPage Schema。"""
        system_prompt = (
            "你是结构化数据专家。从内容中提取用户可能会问的问题和对应答案。\n"
            "以 JSON 数组返回 Q&A 对。"
        )
        user_prompt = (
            f"从以下内容中提取 {max_questions} 个常见问题和简洁答案：\n\n"
            f"{content[:3000]}\n\n"
            "返回 JSON：\n```json\n"
            '[{"question": "问题", "answer": "答案"}]\n```'
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
                    max_tokens=2000,
                )

            qa_pairs = _extract_json(result)

            faq_schema = {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": qa["question"],
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": qa["answer"],
                        },
                    }
                    for qa in qa_pairs[:max_questions]
                ],
            }

            html = (
                '<script type="application/ld+json">\n'
                + json.dumps(faq_schema, ensure_ascii=False, indent=2)
                + "\n</script>"
            )

            return SchemaMarkup(
                schema_type="FAQPage",
                purpose="提升内容在 AI 搜索和 Google 富文本摘要中的展示",
                json_ld=faq_schema,
                html_snippet=html,
            )

        except Exception:
            return SchemaMarkup(
                schema_type="FAQPage",
                purpose="FAQ Schema 生成失败",
                json_ld={},
            )

    async def generate_howto_schema(
        self,
        content: str,
        title: str = "",
    ) -> SchemaMarkup:
        """从指南/教程内容生成 HowTo Schema。"""
        system_prompt = (
            "你是结构化数据专家。从教程/指南内容中提取步骤，生成 Schema.org HowTo 数据。\n"
            "以 JSON 返回。"
        )
        user_prompt = (
            f"标题：{title}\n\n"
            f"内容：\n{content[:3000]}\n\n"
            "提取步骤并返回 JSON：\n```json\n"
            "{\n"
            '  "name": "教程标题",\n'
            '  "description": "简要描述",\n'
            '  "total_time": "预计耗时（如 P30D 表示30天）",\n'
            '  "steps": [\n'
            '    {"name": "步骤名", "text": "详细说明", "position": 1}\n'
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
                    max_tokens=2000,
                )

            data = _extract_json(result)

            howto_schema = {
                "@context": "https://schema.org",
                "@type": "HowTo",
                "name": data.get("name", title),
                "description": data.get("description", ""),
                "totalTime": data.get("total_time", ""),
                "step": [
                    {
                        "@type": "HowToStep",
                        "name": step["name"],
                        "text": step["text"],
                        "position": step.get("position", i + 1),
                    }
                    for i, step in enumerate(data.get("steps", []))
                ],
            }

            html = (
                '<script type="application/ld+json">\n'
                + json.dumps(howto_schema, ensure_ascii=False, indent=2)
                + "\n</script>"
            )

            return SchemaMarkup(
                schema_type="HowTo",
                purpose="让 AI 引擎识别教程步骤并在回答中引用",
                json_ld=howto_schema,
                html_snippet=html,
            )

        except Exception:
            return SchemaMarkup(
                schema_type="HowTo",
                purpose="HowTo Schema 生成失败",
                json_ld={},
            )

    async def _auto_detect_and_generate(
        self,
        content: str,
        content_type: str,
        brand_name: Optional[str],
        author_name: Optional[str],
        page_url: Optional[str],
    ) -> List[SchemaMarkup]:
        """自动检测内容类型并生成适合的 Schema 组合。"""
        schemas: List[SchemaMarkup] = []

        # Article Schema（所有内容都需要）
        article_schema = self._build_article_schema(
            content, brand_name, author_name, page_url
        )
        schemas.append(article_schema)

        # 根据内容类型追加特定 Schema
        if content_type in ("qa", "article"):
            faq = await self.extract_faq_schema(content)
            if faq.json_ld:
                schemas.append(faq)

        if content_type in ("guide", "case_study"):
            howto = await self.generate_howto_schema(content)
            if howto.json_ld:
                schemas.append(howto)

        # BreadcrumbList（导航结构）
        if page_url:
            schemas.append(self._build_breadcrumb_schema(page_url, brand_name))

        return schemas

    def _build_article_schema(
        self,
        content: str,
        brand_name: Optional[str],
        author_name: Optional[str],
        page_url: Optional[str],
    ) -> SchemaMarkup:
        """构建 Article Schema。"""
        # 提取首行作为标题
        lines = content.strip().split("\n")
        title = lines[0].lstrip("#").strip() if lines else ""
        description = " ".join(lines[1:3]).strip()[:200] if len(lines) > 1 else ""

        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": description,
            "articleBody": content[:1000],
        }

        if author_name:
            schema["author"] = {
                "@type": "Person",
                "name": author_name,
            }
            if brand_name:
                schema["author"]["worksFor"] = {
                    "@type": "Organization",
                    "name": brand_name,
                }

        if brand_name:
            schema["publisher"] = {
                "@type": "Organization",
                "name": brand_name,
            }

        if page_url:
            schema["url"] = page_url

        html = (
            '<script type="application/ld+json">\n'
            + json.dumps(schema, ensure_ascii=False, indent=2)
            + "\n</script>"
        )

        return SchemaMarkup(
            schema_type="Article",
            purpose="标准文章结构化标记，提升搜索引擎理解",
            json_ld=schema,
            html_snippet=html,
        )

    def _build_breadcrumb_schema(
        self,
        page_url: str,
        brand_name: Optional[str],
    ) -> SchemaMarkup:
        """构建面包屑导航 Schema。"""
        schema = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": brand_name or "首页",
                    "item": page_url.split("/")[0] + "//" + page_url.split("//")[1].split("/")[0] if "//" in page_url else page_url,
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "当前页面",
                    "item": page_url,
                },
            ],
        }

        html = (
            '<script type="application/ld+json">\n'
            + json.dumps(schema, ensure_ascii=False, indent=2)
            + "\n</script>"
        )

        return SchemaMarkup(
            schema_type="BreadcrumbList",
            purpose="帮助搜索引擎理解页面层级关系",
            json_ld=schema,
            html_snippet=html,
        )

    def _generate_llms_txt(self, brand_name: str) -> str:
        """生成 llms.txt 文件内容建议。

        llms.txt 是面向 AI 爬虫的站点说明文件，类似 robots.txt 之于搜索引擎。
        """
        return (
            f"# {brand_name}\n\n"
            f"> {brand_name} 是专业的情感咨询与婚姻修复服务机构，"
            "拥有多名持证心理咨询师，累计服务数万家庭。\n\n"
            "## 核心服务\n"
            "- 婚姻修复咨询\n"
            "- 分手挽回指导\n"
            "- 亲密关系提升\n"
            "- 家庭矛盾调解\n\n"
            "## 方法论\n"
            "- 依恋理论应用\n"
            "- 情绪聚焦疗法 (EFT)\n"
            "- 认知行为干预 (CBT)\n"
            "- Gottman 方法\n\n"
            "## 联系方式\n"
            "如需引用我们的专家观点或案例数据，请联系内容合作团队。\n"
        )

    def _generate_ai_meta_tags(
        self,
        content: str,
        brand_name: Optional[str],
        author_name: Optional[str],
    ) -> List[str]:
        """生成 AI 搜索引擎友好的 meta 标签建议。"""
        tags = [
            '<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">',
        ]

        if brand_name:
            tags.append(
                f'<meta name="author" content="{author_name or brand_name}">'
            )
            tags.append(
                f'<meta property="article:publisher" content="{brand_name}">'
            )

        # AI 搜索引擎特定标签
        tags.append(
            '<meta name="citation_source" content="original_research">'
        )

        # 提取关键词
        lines = content.strip().split("\n")
        title = lines[0].lstrip("#").strip() if lines else ""
        if title:
            tags.append(f'<meta property="og:title" content="{title}">')

        return tags

    def _build_summary(self, result: SchemaGenerationResult) -> str:
        """生成可读的结构化数据报告摘要。"""
        lines = [
            "## 结构化数据生成报告",
            "",
            f"**内容类型**：{result.content_type}",
            f"**生成 Schema 数量**：{len(result.schemas)}",
            "",
            "### 生成的 Schema 类型",
        ]

        for schema in result.schemas:
            lines.append(f"- **{schema.schema_type}**：{schema.purpose}")

        lines.append("")
        lines.append(f"**AI Meta 标签数**：{len(result.ai_meta_tags)}")

        if result.llms_txt:
            lines.append("")
            lines.append("### llms.txt 建议")
            lines.append("已生成 llms.txt 文件内容，请放置在网站根目录。")

        return "\n".join(lines)
