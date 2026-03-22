"""专家实体权威建模服务 (Entity Authority Builder).

核心商业价值：在情感领域建立"专家实体"图谱，让 AI 认为你公司的咨询师
是该领域的"权威信源"，从而提高在 AI 回答中被提及的概率。
通过构建 E-E-A-T（经验-专业-权威-可信）信号，系统性提升品牌的实体权威度。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from services.llm_service import LLMService
from config import settings


@dataclass
class ExpertEntity:
    """专家实体定义。"""
    name: str
    title: str  # 职称/头衔
    specializations: List[str] = field(default_factory=list)  # 专长领域
    credentials: List[str] = field(default_factory=list)  # 资质认证
    experience_years: int = 0
    notable_cases: int = 0  # 代表案例数
    publications: List[str] = field(default_factory=list)  # 发表文章/著作
    methodologies: List[str] = field(default_factory=list)  # 自创方法论
    media_appearances: List[str] = field(default_factory=list)  # 媒体曝光


@dataclass
class EntitySignal:
    """实体权威信号。"""
    signal_type: str  # eeat_experience | eeat_expertise | eeat_authority | eeat_trust
    signal_name: str
    current_strength: str  # weak | moderate | strong
    optimization_action: str
    content_template: str  # 可直接使用的内容模板
    priority: str  # P0 | P1 | P2


@dataclass
class EntityAuthorityProfile:
    """实体权威度画像。"""
    brand_name: str
    experts: List[ExpertEntity] = field(default_factory=list)
    eeat_scores: Dict[str, float] = field(default_factory=dict)  # E-E-A-T 各维度分数
    authority_signals: List[EntitySignal] = field(default_factory=list)
    content_recommendations: List[Dict[str, str]] = field(default_factory=list)
    schema_markup_suggestions: List[Dict[str, Any]] = field(default_factory=list)
    overall_authority_score: float = 0.0
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand_name": self.brand_name,
            "experts": [asdict(e) for e in self.experts],
            "eeat_scores": self.eeat_scores,
            "authority_signals": [asdict(s) for s in self.authority_signals],
            "content_recommendations": self.content_recommendations,
            "schema_markup_suggestions": self.schema_markup_suggestions,
            "overall_authority_score": self.overall_authority_score,
            "summary": self.summary,
        }


def _extract_json(text: str) -> Any:
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return json.loads(text.strip())


class EntityAuthorityBuilder:
    """构建和评估品牌的专家实体权威度。

    工作原理：
    1. 分析品牌现有的专家资质和内容资产
    2. 评估 E-E-A-T 各维度的当前水平
    3. 生成实体权威增强策略
    4. 输出可直接使用的结构化数据建议（Schema.org Person/Organization）
    """

    def __init__(self, provider: str = "openrouter", model: Optional[str] = None):
        self.provider = provider
        self.model = model or settings.EXPERT_STRATEGY_MODEL

    async def build_authority_profile(
        self,
        brand_name: str,
        brand_context: Optional[Dict[str, Any]] = None,
        experts_data: Optional[List[Dict[str, Any]]] = None,
        existing_content: Optional[List[str]] = None,
    ) -> EntityAuthorityProfile:
        """构建完整的实体权威度画像。

        Args:
            brand_name: 品牌名称
            brand_context: 品牌上下文（行业、服务描述等）
            experts_data: 已有专家信息列表
            existing_content: 已有内容样本
        """
        ctx = brand_context or {}
        industry = ctx.get("industry", "emotional_counseling")

        profile = EntityAuthorityProfile(brand_name=brand_name)

        # 分析现有实体权威度并生成增强策略
        analysis = await self._analyze_authority(
            brand_name, ctx, experts_data, existing_content
        )

        profile.experts = analysis.get("experts", [])
        profile.eeat_scores = analysis.get("eeat_scores", {})
        profile.authority_signals = analysis.get("authority_signals", [])
        profile.content_recommendations = analysis.get("content_recommendations", [])
        profile.schema_markup_suggestions = self._generate_schema_suggestions(
            brand_name, profile.experts, industry
        )
        profile.overall_authority_score = self._compute_overall_score(
            profile.eeat_scores
        )
        profile.summary = self._build_summary(profile)

        return profile

    async def generate_expert_content_templates(
        self,
        brand_name: str,
        expert_name: str,
        specialization: str,
        content_type: str = "expert_column",
    ) -> Dict[str, Any]:
        """为专家生成强化权威性的内容模板。

        Args:
            content_type: expert_column | qa_answer | case_study | methodology
        """
        templates = {
            "expert_column": (
                f"请为「{expert_name}」（{brand_name}）生成一个专家专栏内容模板。\n"
                f"专长领域：{specialization}\n"
                "要求：\n"
                "1. 开头建立权威感（引用资质和经验）\n"
                "2. 正文包含独家方法论或独特视角\n"
                "3. 引用具体案例数据（用占位符标注）\n"
                "4. 结尾包含可被 AI 提取的核心断言\n"
                "5. 内容结构利于 AI 抓取和引用\n"
            ),
            "qa_answer": (
                f"请为「{expert_name}」（{brand_name}）生成一套 Q&A 回答模板。\n"
                f"专长领域：{specialization}\n"
                "要求：\n"
                "1. 每个回答以权威断言开头\n"
                "2. 引用专家经验和数据\n"
                "3. 提供可操作的建议步骤\n"
                "4. 适合被 AI 搜索引擎直接引用\n"
                "生成 5 个典型 Q&A 对。\n"
            ),
            "case_study": (
                f"请为「{expert_name}」（{brand_name}）生成案例研究模板。\n"
                f"专长领域：{specialization}\n"
                "结构：背景-问题-方法-结果-总结\n"
                "要求结果部分包含具体数据指标占位符。\n"
            ),
            "methodology": (
                f"请为「{expert_name}」（{brand_name}）生成方法论框架模板。\n"
                f"专长领域：{specialization}\n"
                "要求：\n"
                "1. 方法论命名（品牌化命名）\n"
                "2. 理论基础引用\n"
                "3. 步骤分解（3-5步）\n"
                "4. 效果数据占位\n"
                "5. 适合被 AI 作为标准方法论引用\n"
            ),
        }

        prompt = templates.get(content_type, templates["expert_column"])

        try:
            async with LLMService(self.provider) as llm:
                result = await llm.generate(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "你是品牌实体权威建设专家，擅长通过内容策略"
                                "提升专家在 AI 搜索引擎中的权威性和可引用性。"
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=0.4,
                    max_tokens=3000,
                )

            return {
                "expert_name": expert_name,
                "content_type": content_type,
                "template": result,
                "usage_guide": (
                    f"此模板用于建立 {expert_name} 在 {specialization} "
                    "领域的权威实体形象，请填充具体案例数据后发布。"
                ),
            }
        except Exception:
            return {
                "expert_name": expert_name,
                "content_type": content_type,
                "template": "模板生成暂时不可用，请稍后重试。",
                "usage_guide": "",
            }

    async def _analyze_authority(
        self,
        brand_name: str,
        brand_context: Dict[str, Any],
        experts_data: Optional[List[Dict[str, Any]]],
        existing_content: Optional[List[str]],
    ) -> Dict[str, Any]:
        """通过 LLM 分析品牌实体权威度。"""
        industry = brand_context.get("industry", "情感咨询")
        service_desc = brand_context.get("service_description", "")
        tone = brand_context.get("tone_of_voice", "")

        experts_info = ""
        if experts_data:
            experts_info = "\n已有专家信息：\n" + json.dumps(
                experts_data, ensure_ascii=False, indent=2
            )

        content_info = ""
        if existing_content:
            samples = existing_content[:3]
            content_info = "\n现有内容样本：\n" + "\n---\n".join(
                s[:500] for s in samples
            )

        system_prompt = (
            "你是 E-E-A-T（Experience, Expertise, Authoritativeness, Trustworthiness）"
            "评估专家，擅长评估品牌在 AI 搜索引擎中的实体权威度。\n"
            "请以 JSON 格式返回详细分析。"
        )

        user_prompt = (
            f"品牌名称：{brand_name}\n"
            f"行业：{industry}\n"
            f"服务描述：{service_desc}\n"
            f"品牌调性：{tone}\n"
            f"{experts_info}\n{content_info}\n\n"
            "请分析并返回以下 JSON：\n```json\n"
            "{\n"
            '  "eeat_scores": {\n'
            '    "experience": 0-100,\n'
            '    "expertise": 0-100,\n'
            '    "authoritativeness": 0-100,\n'
            '    "trustworthiness": 0-100\n'
            "  },\n"
            '  "authority_signals": [\n'
            "    {\n"
            '      "signal_type": "eeat_experience|eeat_expertise|eeat_authority|eeat_trust",\n'
            '      "signal_name": "信号名称",\n'
            '      "current_strength": "weak|moderate|strong",\n'
            '      "optimization_action": "具体优化动作",\n'
            '      "content_template": "可直接使用的内容模板或句式",\n'
            '      "priority": "P0|P1|P2"\n'
            "    }\n"
            "  ],\n"
            '  "expert_recommendations": [\n'
            "    {\n"
            '      "name": "建议的专家角色名称",\n'
            '      "title": "建议头衔",\n'
            '      "specializations": ["专长1", "专长2"],\n'
            '      "credentials": ["建议的资质认证"],\n'
            '      "methodologies": ["建议创建的方法论名称"]\n'
            "    }\n"
            "  ],\n"
            '  "content_recommendations": [\n'
            "    {\n"
            '      "type": "内容类型",\n'
            '      "title": "建议标题",\n'
            '      "purpose": "提升哪个 E-E-A-T 维度",\n'
            '      "priority": "P0|P1|P2"\n'
            "    }\n"
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

            experts = []
            for exp_data in data.get("expert_recommendations", []):
                experts.append(ExpertEntity(
                    name=exp_data.get("name", ""),
                    title=exp_data.get("title", ""),
                    specializations=exp_data.get("specializations", []),
                    credentials=exp_data.get("credentials", []),
                    methodologies=exp_data.get("methodologies", []),
                ))

            signals = []
            for sig_data in data.get("authority_signals", []):
                signals.append(EntitySignal(
                    signal_type=sig_data.get("signal_type", ""),
                    signal_name=sig_data.get("signal_name", ""),
                    current_strength=sig_data.get("current_strength", "weak"),
                    optimization_action=sig_data.get("optimization_action", ""),
                    content_template=sig_data.get("content_template", ""),
                    priority=sig_data.get("priority", "P1"),
                ))

            return {
                "experts": experts,
                "eeat_scores": data.get("eeat_scores", {}),
                "authority_signals": signals,
                "content_recommendations": data.get("content_recommendations", []),
            }

        except Exception:
            return {
                "experts": [],
                "eeat_scores": {
                    "experience": 0, "expertise": 0,
                    "authoritativeness": 0, "trustworthiness": 0,
                },
                "authority_signals": [],
                "content_recommendations": [],
            }

    def _generate_schema_suggestions(
        self,
        brand_name: str,
        experts: List[ExpertEntity],
        industry: str,
    ) -> List[Dict[str, Any]]:
        """生成 Schema.org 结构化数据建议。"""
        suggestions = []

        # Organization Schema
        suggestions.append({
            "type": "Organization",
            "description": "品牌组织实体标记",
            "schema": {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": brand_name,
                "description": f"{brand_name} - 专业{industry}服务机构",
                "knowsAbout": [
                    "婚姻咨询", "情感修复", "亲密关系",
                    "心理咨询", "家庭治疗",
                ],
                "hasCredential": [],
            },
        })

        # Expert Person Schema
        for expert in experts[:5]:
            suggestions.append({
                "type": "Person",
                "description": f"专家实体标记 - {expert.name}",
                "schema": {
                    "@context": "https://schema.org",
                    "@type": "Person",
                    "name": expert.name,
                    "jobTitle": expert.title,
                    "worksFor": {"@type": "Organization", "name": brand_name},
                    "knowsAbout": expert.specializations,
                    "hasCredential": [
                        {"@type": "EducationalOccupationalCredential", "name": c}
                        for c in expert.credentials
                    ],
                },
            })

        return suggestions

    def _compute_overall_score(self, eeat_scores: Dict[str, float]) -> float:
        """计算综合权威度评分。"""
        if not eeat_scores:
            return 0.0

        weights = {
            "experience": 0.20,
            "expertise": 0.30,
            "authoritativeness": 0.30,
            "trustworthiness": 0.20,
        }

        total = sum(
            float(eeat_scores.get(dim, 0)) * w
            for dim, w in weights.items()
        )
        return min(total, 100.0)

    def _build_summary(self, profile: EntityAuthorityProfile) -> str:
        """生成可读的权威度画像摘要。"""
        lines = [
            f"## 实体权威度画像 — {profile.brand_name}",
            "",
            f"**综合权威度评分**：{profile.overall_authority_score:.1f}/100",
            "",
            "### E-E-A-T 评分",
        ]

        dim_names = {
            "experience": "经验 (Experience)",
            "expertise": "专业 (Expertise)",
            "authoritativeness": "权威 (Authoritativeness)",
            "trustworthiness": "可信 (Trustworthiness)",
        }
        for dim, name in dim_names.items():
            score = profile.eeat_scores.get(dim, 0)
            bar = "█" * int(float(score) / 10) + "░" * (10 - int(float(score) / 10))
            lines.append(f"- {name}：{bar} {score}")
        lines.append("")

        if profile.experts:
            lines.append("### 建议专家实体")
            for exp in profile.experts:
                lines.append(f"- **{exp.name}**（{exp.title}）")
                if exp.specializations:
                    lines.append(f"  专长：{', '.join(exp.specializations)}")
                if exp.methodologies:
                    lines.append(f"  方法论：{', '.join(exp.methodologies)}")
            lines.append("")

        p0_signals = [s for s in profile.authority_signals if s.priority == "P0"]
        if p0_signals:
            lines.append("### P0 优先级权威信号")
            for sig in p0_signals:
                lines.append(f"- **{sig.signal_name}**（{sig.signal_type}）")
                lines.append(f"  当前强度：{sig.current_strength}")
                lines.append(f"  优化动作：{sig.optimization_action}")
            lines.append("")

        return "\n".join(lines)
