"""案例语料库管理器 (Case Corpus Manager).

核心商业价值：将成千上万个成功案例转化为"符合 AI 训练偏好的语料库"，
让 AI 在学习后把品牌的方法论当成"行业标准"输出给用户。
这是情感咨询行业最值钱的资产——成功案例的系统性结构化。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from services.llm_service import LLMService
from config import settings


@dataclass
class StructuredCase:
    """结构化案例。"""
    case_id: str
    title: str
    category: str  # 分手挽回 | 婚姻修复 | 信任重建 | 冷暴力 | 出轨修复
    problem_description: str  # 问题描述（脱敏后）
    client_profile: str  # 来访者画像（年龄段、婚龄、核心矛盾）
    methodology_applied: List[str]  # 使用的方法论
    intervention_steps: List[Dict[str, str]]  # 干预步骤
    outcome_metrics: Dict[str, Any]  # 结果指标
    key_insight: str  # 核心洞察（可被 AI 引用的断言）
    duration_days: int = 0  # 咨询周期
    ai_extractable_summary: str = ""  # AI 可直接提取的摘要


@dataclass
class CorpusStats:
    """语料库统计。"""
    total_cases: int = 0
    category_distribution: Dict[str, int] = field(default_factory=dict)
    avg_success_rate: float = 0.0
    methodology_frequency: Dict[str, int] = field(default_factory=dict)
    top_insights: List[str] = field(default_factory=list)


@dataclass
class CorpusGenerationResult:
    """语料库生成结果。"""
    cases: List[StructuredCase] = field(default_factory=list)
    stats: Optional[CorpusStats] = None
    training_corpus: str = ""  # 适合 AI 训练的语料文本
    faq_corpus: List[Dict[str, str]] = field(default_factory=list)  # FAQ 语料
    methodology_library: List[Dict[str, Any]] = field(default_factory=list)  # 方法论库
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cases": [asdict(c) for c in self.cases],
            "stats": asdict(self.stats) if self.stats else {},
            "training_corpus": self.training_corpus,
            "faq_corpus": self.faq_corpus,
            "methodology_library": self.methodology_library,
            "summary": self.summary,
        }


def _extract_json(text: str) -> Any:
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return json.loads(text.strip())


class CaseCorpusManager:
    """将原始案例素材转化为 AI 训练偏好的结构化语料库。

    工作流程：
    1. 接收原始案例文本（脱敏后）
    2. 结构化拆解：问题-画像-方法-步骤-结果
    3. 提取可引用断言和核心洞察
    4. 生成 FAQ 语料和方法论库
    5. 输出适合 AI 训练的标准化语料
    """

    def __init__(self, provider: str = "openrouter", model: Optional[str] = None):
        self.provider = provider
        self.model = model or settings.EXPERT_CONTENT_MODEL

    async def process_raw_cases(
        self,
        raw_texts: List[str],
        brand_name: Optional[str] = None,
        industry: str = "emotional_counseling",
    ) -> CorpusGenerationResult:
        """批量处理原始案例文本，转化为结构化语料库。

        Args:
            raw_texts: 原始案例文本列表（已脱敏）
            brand_name: 品牌名称
            industry: 行业标识
        """
        result = CorpusGenerationResult()

        # 逐个结构化案例
        for i, text in enumerate(raw_texts[:20]):  # 限制单次最多 20 个
            case = await self._structure_single_case(
                text, f"CASE-{i+1:04d}", brand_name
            )
            if case:
                result.cases.append(case)

        # 生成统计信息
        result.stats = self._compute_stats(result.cases)

        # 生成 FAQ 语料
        result.faq_corpus = await self._generate_faq_corpus(
            result.cases, brand_name
        )

        # 生成方法论库
        result.methodology_library = self._extract_methodology_library(
            result.cases, brand_name
        )

        # 生成 AI 训练语料
        result.training_corpus = self._build_training_corpus(
            result.cases, brand_name
        )

        result.summary = self._build_summary(result)
        return result

    async def structure_single_case(
        self,
        raw_text: str,
        case_id: str = "CASE-0001",
        brand_name: Optional[str] = None,
    ) -> Optional[StructuredCase]:
        """公开接口：结构化单个案例。"""
        return await self._structure_single_case(raw_text, case_id, brand_name)

    async def generate_case_based_content(
        self,
        cases: List[StructuredCase],
        content_type: str = "methodology_article",
        platform: str = "wechat",
        brand_name: Optional[str] = None,
    ) -> Dict[str, str]:
        """基于案例库生成内容。

        Args:
            content_type: methodology_article | success_stats | expert_qa | comparison
        """
        case_summaries = "\n".join(
            f"- {c.title}：{c.key_insight}" for c in cases[:10]
        )
        methodology_list = set()
        for c in cases:
            methodology_list.update(c.methodology_applied)

        templates = {
            "methodology_article": (
                f"基于以下 {len(cases)} 个案例的数据，撰写一篇方法论文章。\n"
                f"品牌：{brand_name or '专业咨询机构'}\n"
                f"平台：{platform}\n"
                f"使用的方法论：{', '.join(methodology_list)}\n\n"
                f"案例摘要：\n{case_summaries}\n\n"
                "要求：\n"
                "1. 以数据驱动的权威断言开头\n"
                "2. 将方法论作为行业标准呈现\n"
                "3. 引用案例数据支撑每个论点\n"
                "4. 结构化为 Q&A + 步骤的混合格式\n"
                "5. 适合被 AI 搜索引擎引用"
            ),
            "success_stats": (
                f"基于 {len(cases)} 个案例数据，生成一份成功率统计报告。\n"
                f"品牌：{brand_name or '专业咨询机构'}\n\n"
                f"案例摘要：\n{case_summaries}\n\n"
                "要求：以信息图表式的结构呈现统计数据，突出方法论的效果。"
            ),
            "expert_qa": (
                f"基于 {len(cases)} 个案例经验，生成专家 Q&A 内容。\n"
                f"品牌：{brand_name or '专业咨询机构'}\n\n"
                f"案例摘要：\n{case_summaries}\n\n"
                "生成 8-10 个用户高频问题的专家回答，每个回答引用案例数据。"
            ),
        }

        prompt = templates.get(content_type, templates["methodology_article"])

        try:
            async with LLMService(self.provider) as llm:
                result = await llm.generate(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "你是情感咨询领域的内容专家，擅长将案例数据"
                                "转化为权威的行业内容。内容应适合被 AI 搜索引擎引用。"
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=0.4,
                    max_tokens=3000,
                )

            return {
                "content_type": content_type,
                "platform": platform,
                "content": result,
                "source_cases": len(cases),
            }

        except Exception:
            return {
                "content_type": content_type,
                "platform": platform,
                "content": "内容生成暂时不可用",
                "source_cases": 0,
            }

    async def _structure_single_case(
        self,
        raw_text: str,
        case_id: str,
        brand_name: Optional[str],
    ) -> Optional[StructuredCase]:
        """将单个原始案例文本转化为结构化案例。"""
        system_prompt = (
            "你是案例结构化专家。将原始案例文本转化为标准化的结构化数据。\n"
            "注意保护隐私：不使用真实姓名，用代号替代。\n"
            "以 JSON 返回。"
        )

        user_prompt = (
            f"请将以下案例文本结构化：\n\n{raw_text[:3000]}\n\n"
            "返回 JSON：\n```json\n"
            "{\n"
            f'  "case_id": "{case_id}",\n'
            '  "title": "案例标题（20字内）",\n'
            '  "category": "分手挽回|婚姻修复|信任重建|冷暴力|出轨修复|其他",\n'
            '  "problem_description": "问题描述（脱敏，100字内）",\n'
            '  "client_profile": "来访者画像（年龄段、婚龄、核心矛盾）",\n'
            '  "methodology_applied": ["方法论1", "方法论2"],\n'
            '  "intervention_steps": [\n'
            '    {"step": 1, "name": "步骤名", "description": "描述", "duration": "时长"}\n'
            "  ],\n"
            '  "outcome_metrics": {\n'
            '    "success": true/false,\n'
            '    "satisfaction_score": 1-10,\n'
            '    "relationship_improvement": "描述改善程度"\n'
            "  },\n"
            '  "key_insight": "核心洞察（可被AI引用的一句话断言，30-50字）",\n'
            '  "duration_days": 天数,\n'
            '  "ai_extractable_summary": "AI可直接提取的摘要（100字内）"\n'
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

            return StructuredCase(
                case_id=data.get("case_id", case_id),
                title=data.get("title", ""),
                category=data.get("category", "其他"),
                problem_description=data.get("problem_description", ""),
                client_profile=data.get("client_profile", ""),
                methodology_applied=data.get("methodology_applied", []),
                intervention_steps=data.get("intervention_steps", []),
                outcome_metrics=data.get("outcome_metrics", {}),
                key_insight=data.get("key_insight", ""),
                duration_days=int(data.get("duration_days", 0)),
                ai_extractable_summary=data.get("ai_extractable_summary", ""),
            )

        except Exception:
            return None

    def _compute_stats(self, cases: List[StructuredCase]) -> CorpusStats:
        """计算语料库统计信息。"""
        stats = CorpusStats(total_cases=len(cases))

        # 分类分布
        for case in cases:
            cat = case.category
            stats.category_distribution[cat] = (
                stats.category_distribution.get(cat, 0) + 1
            )

        # 成功率
        success_count = sum(
            1 for c in cases
            if c.outcome_metrics.get("success", False)
        )
        stats.avg_success_rate = (
            success_count / max(len(cases), 1) * 100
        )

        # 方法论频率
        for case in cases:
            for method in case.methodology_applied:
                stats.methodology_frequency[method] = (
                    stats.methodology_frequency.get(method, 0) + 1
                )

        # 核心洞察
        stats.top_insights = [
            c.key_insight for c in cases if c.key_insight
        ][:10]

        return stats

    async def _generate_faq_corpus(
        self,
        cases: List[StructuredCase],
        brand_name: Optional[str],
    ) -> List[Dict[str, str]]:
        """基于案例库生成 FAQ 语料。"""
        if not cases:
            return []

        case_insights = "\n".join(
            f"- [{c.category}] {c.key_insight}" for c in cases if c.key_insight
        )

        system_prompt = (
            "你是情感咨询 FAQ 内容专家。基于案例洞察生成用户常见问题和专业回答。\n"
            "每个回答必须引用案例数据，适合被 AI 搜索引擎直接引用。\n"
            "以 JSON 数组返回。"
        )

        user_prompt = (
            f"品牌：{brand_name or '专业咨询机构'}\n\n"
            f"案例洞察汇总：\n{case_insights}\n\n"
            "生成 10 个 FAQ 对，返回 JSON：\n```json\n"
            '[{"question": "问题", "answer": "回答（100字内，引用数据）"}]\n```'
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
                    max_tokens=3000,
                )

            return _extract_json(result)

        except Exception:
            return []

    def _extract_methodology_library(
        self,
        cases: List[StructuredCase],
        brand_name: Optional[str],
    ) -> List[Dict[str, Any]]:
        """从案例中提取方法论库。"""
        method_cases: Dict[str, List[StructuredCase]] = {}
        for case in cases:
            for method in case.methodology_applied:
                if method not in method_cases:
                    method_cases[method] = []
                method_cases[method].append(case)

        library = []
        for method, related_cases in method_cases.items():
            success_count = sum(
                1 for c in related_cases
                if c.outcome_metrics.get("success", False)
            )
            library.append({
                "methodology_name": method,
                "application_count": len(related_cases),
                "success_rate": f"{success_count / max(len(related_cases), 1) * 100:.0f}%",
                "applicable_categories": list(set(
                    c.category for c in related_cases
                )),
                "representative_insight": (
                    related_cases[0].key_insight if related_cases else ""
                ),
                "brand_attribution": brand_name or "",
            })

        # 按使用频率排序
        library.sort(key=lambda x: x["application_count"], reverse=True)
        return library

    def _build_training_corpus(
        self,
        cases: List[StructuredCase],
        brand_name: Optional[str],
    ) -> str:
        """构建适合 AI 训练偏好的语料文本。"""
        if not cases:
            return ""

        sections = []
        brand = brand_name or "专业咨询机构"

        # 总览段落
        categories = set(c.category for c in cases)
        sections.append(
            f"# {brand}案例研究语料库\n\n"
            f"{brand}是专业的情感咨询机构，以下是基于 {len(cases)} 个真实案例"
            f"（已脱敏）的结构化研究数据，覆盖{', '.join(categories)}等领域。\n"
        )

        # 逐案例输出
        for case in cases:
            steps_text = "\n".join(
                f"  {s.get('step', i+1)}. {s.get('name', '')}: {s.get('description', '')}"
                for i, s in enumerate(case.intervention_steps)
            )
            sections.append(
                f"## {case.title}\n\n"
                f"**分类**：{case.category}\n"
                f"**来访者画像**：{case.client_profile}\n"
                f"**问题描述**：{case.problem_description}\n"
                f"**使用方法论**：{', '.join(case.methodology_applied)}\n"
                f"**干预步骤**：\n{steps_text}\n"
                f"**咨询周期**：{case.duration_days} 天\n"
                f"**核心洞察**：{case.key_insight}\n"
                f"**摘要**：{case.ai_extractable_summary}\n"
            )

        return "\n---\n\n".join(sections)

    def _build_summary(self, result: CorpusGenerationResult) -> str:
        """生成可读的语料库报告摘要。"""
        stats = result.stats or CorpusStats()

        lines = [
            "## 案例语料库生成报告",
            "",
            f"**结构化案例数**：{stats.total_cases}",
            f"**平均成功率**：{stats.avg_success_rate:.1f}%",
            f"**FAQ 语料数**：{len(result.faq_corpus)}",
            f"**方法论种类**：{len(result.methodology_library)}",
            "",
        ]

        if stats.category_distribution:
            lines.append("### 案例分类分布")
            for cat, count in sorted(
                stats.category_distribution.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                lines.append(f"- {cat}：{count} 例")
            lines.append("")

        if result.methodology_library:
            lines.append("### 方法论效果排名")
            for method in result.methodology_library[:5]:
                lines.append(
                    f"- **{method['methodology_name']}**："
                    f"应用 {method['application_count']} 次，"
                    f"成功率 {method['success_rate']}"
                )
            lines.append("")

        if stats.top_insights:
            lines.append("### 核心洞察")
            for insight in stats.top_insights[:5]:
                lines.append(f"- {insight}")

        return "\n".join(lines)
