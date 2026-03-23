"""Expert Agent Team orchestrator.

5-role pipeline: Chief Strategist → Data Analyst + GEO Optimizer (parallel)
→ Content Architect → Quality Reviewer.

Uses OpenRouter with Claude Sonnet 4.6 and Gemini 3.1 Pro.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from config import settings
from services.expert_prompts import build_expert_user_prompt, get_expert_system_prompt
from services.experience_service import (
    OptimizationExperience,
    build_experience_context,
    save_experience,
)
from services.geo_scorer import compute_geo_score, suggest_optimization_strategies
from services.geo_strategies import apply_strategy
from services.llm_service import LLMService


class ExpertRole(str, Enum):
    CHIEF_STRATEGIST = "chief_strategist"
    CONTENT_ARCHITECT = "content_architect"
    DATA_ANALYST = "data_analyst"
    QUALITY_REVIEWER = "quality_reviewer"
    GEO_OPTIMIZER = "geo_optimizer"


# Maps role → OpenRouter model.
ROLE_MODEL_MAP: Dict[str, str] = {
    ExpertRole.CHIEF_STRATEGIST: settings.EXPERT_STRATEGY_MODEL,
    ExpertRole.CONTENT_ARCHITECT: settings.EXPERT_CONTENT_MODEL,
    ExpertRole.DATA_ANALYST: settings.EXPERT_ANALYSIS_MODEL,
    ExpertRole.QUALITY_REVIEWER: settings.EXPERT_REVIEW_MODEL,
    ExpertRole.GEO_OPTIMIZER: settings.EXPERT_GEO_MODEL,
}

ROLE_LABELS: Dict[str, str] = {
    ExpertRole.CHIEF_STRATEGIST: "GEO 首席策略师",
    ExpertRole.CONTENT_ARCHITECT: "内容架构师",
    ExpertRole.DATA_ANALYST: "数据分析师",
    ExpertRole.QUALITY_REVIEWER: "质量审核官",
    ExpertRole.GEO_OPTIMIZER: "GEO 优化师",
}


@dataclass
class ExpertOutput:
    role: str
    label: str
    model: str
    content: str
    duration_ms: int = 0
    error: Optional[str] = None


@dataclass
class TeamReport:
    strategy: ExpertOutput
    analysis: ExpertOutput
    geo_optimization: ExpertOutput
    content: ExpertOutput
    review: ExpertOutput
    geo_scores: Dict[str, Any] = field(default_factory=dict)
    total_duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experts": {
                "chief_strategist": _output_dict(self.strategy),
                "data_analyst": _output_dict(self.analysis),
                "geo_optimizer": _output_dict(self.geo_optimization),
                "content_architect": _output_dict(self.content),
                "quality_reviewer": _output_dict(self.review),
            },
            "geo_scores": self.geo_scores,
            "total_duration_ms": self.total_duration_ms,
        }

    def to_markdown(self) -> str:
        sections = [
            "# GEO 专家团队分析报告\n",
            f"**总耗时**: {self.total_duration_ms / 1000:.1f}s\n",
            "---\n",
            f"## 一、GEO 首席策略师报告\n*模型: {self.strategy.model}*\n\n{self.strategy.content}\n",
            "---\n",
            f"## 二、数据分析师报告\n*模型: {self.analysis.model}*\n\n{self.analysis.content}\n",
            "---\n",
            f"## 三、GEO 优化师报告\n*模型: {self.geo_optimization.model}*\n\n{self.geo_optimization.content}\n",
            "---\n",
            f"## 四、内容架构师输出\n*模型: {self.content.model}*\n\n{self.content.content}\n",
            "---\n",
            f"## 五、质量审核官评审\n*模型: {self.review.model}*\n\n{self.review.content}\n",
        ]
        if self.geo_scores:
            sections.append("---\n")
            sections.append("## 六、GEO 评分卡\n")
            for key, val in self.geo_scores.items():
                sections.append(f"- **{key}**: {val}\n")
        return "\n".join(sections)


def _output_dict(output: ExpertOutput) -> Dict[str, Any]:
    return {
        "role": output.role,
        "label": output.label,
        "model": output.model,
        "content": output.content,
        "duration_ms": output.duration_ms,
        "error": output.error,
    }


async def _run_expert(
    role: str,
    payload: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    provider: str = "openrouter",
) -> ExpertOutput:
    """Run a single expert with its dedicated model and prompts."""
    model = ROLE_MODEL_MAP.get(role, settings.OPENROUTER_MODEL)
    label = ROLE_LABELS.get(role, role)
    system_prompt = get_expert_system_prompt(role, context)
    user_prompt = build_expert_user_prompt(role, payload)

    start = time.monotonic()
    try:
        async with LLMService(provider) as llm:
            content = await llm.generate(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=model,
                temperature=0.3,
                max_tokens=4000,
            )
        duration = int((time.monotonic() - start) * 1000)
        return ExpertOutput(
            role=role,
            label=label,
            model=model,
            content=content.strip(),
            duration_ms=duration,
        )
    except Exception as exc:
        duration = int((time.monotonic() - start) * 1000)
        return ExpertOutput(
            role=role,
            label=label,
            model=model,
            content=f"[专家 {label} 生成失败] {str(exc)}",
            duration_ms=duration,
            error=str(exc),
        )


async def run_expert_pipeline(
    brand_data: Dict[str, Any],
    keyword_layers: Dict[str, Any],
    gap_analysis: Dict[str, Any],
    recommendations: List[str],
    asset_texts: Optional[List[str]] = None,
    target_platforms: Optional[List[str]] = None,
    provider: str = "openrouter",
) -> TeamReport:
    """
    Run the full 5-expert pipeline:
    1. Chief Strategist → strategy report
    2. Data Analyst + GEO Optimizer (parallel)
    3. Content Architect → generates content based on 1+2
    4. Quality Reviewer → reviews output from 3
    """
    total_start = time.monotonic()

    base_payload = {
        "brand": brand_data,
        "keyword_layers": keyword_layers,
        "gap_analysis": gap_analysis,
        "recommendations": recommendations,
        "asset_summary": f"{len(asset_texts or [])} 篇素材",
        "target_platforms": target_platforms or ["wechat", "xiaohongshu", "zhihu", "video"],
    }

    context = {
        "brand_name": brand_data.get("name", ""),
        "industry": brand_data.get("industry", ""),
        "region": brand_data.get("region", ""),
    }

    # Inject historical optimization experience (if any).
    brand_id = brand_data.get("name", "default")
    platforms = target_platforms or ["wechat"]
    try:
        exp_context = await build_experience_context(brand_id, platforms[0])
        if exp_context:
            context["optimization_experience"] = exp_context
    except Exception:
        pass  # non-critical — proceed without experience

    # Step 1: Chief Strategist.
    strategy_output = await _run_expert(
        ExpertRole.CHIEF_STRATEGIST, base_payload, context, provider
    )

    # Inject prior insights for downstream experts.
    context["prior_insights"] = {
        "strategy_positioning": strategy_output.content[:300],
        "priority_actions_hint": "见战略报告",
    }

    # Step 2: Parallel — Data Analyst + GEO Optimizer.
    enriched_payload = {
        **base_payload,
        "strategy_report": strategy_output.content,
    }
    analysis_output, geo_output = await asyncio.gather(
        _run_expert(ExpertRole.DATA_ANALYST, enriched_payload, context, provider),
        _run_expert(ExpertRole.GEO_OPTIMIZER, enriched_payload, context, provider),
    )

    # Enrich context with Step 2 insights for downstream experts.
    context["prior_insights"]["data_coverage_gaps"] = analysis_output.content[:300]
    context["prior_insights"]["geo_weaknesses"] = geo_output.content[:300]

    # Step 3: Content Architect — uses all prior outputs.
    content_payload = {
        **base_payload,
        "strategy_report": strategy_output.content,
        "analysis_report": analysis_output.content,
        "geo_optimization_report": geo_output.content,
    }
    content_output = await _run_expert(
        ExpertRole.CONTENT_ARCHITECT, content_payload, context, provider
    )

    # Step 4: Quality Reviewer — reviews content output.
    review_payload = {
        "brand": brand_data,
        "content_to_review": content_output.content,
        "strategy_summary": strategy_output.content[:800],
        "target_platforms": target_platforms or ["wechat"],
    }
    review_output = await _run_expert(
        ExpertRole.QUALITY_REVIEWER, review_payload, context, provider
    )

    # Step 5: GEO scoring + auto-optimization feedback loop.
    keywords_flat: List[str] = []
    for layer_kws in (keyword_layers or {}).values():
        if isinstance(layer_kws, list):
            keywords_flat.extend(layer_kws)
    platforms = target_platforms or ["wechat"]

    score_card = compute_geo_score(
        content_output.content,
        keywords=keywords_flat[:10] if keywords_flat else None,
        platform=platforms[0] if platforms else None,
    )

    if (
        score_card.overall < settings.GEO_AUTO_OPTIMIZE_THRESHOLD
        and settings.GEO_AUTO_OPTIMIZE_MAX_ROUNDS > 0
    ):
        strategies = suggest_optimization_strategies(score_card)
        if strategies:
            optimized_content = content_output.content
            for strategy_name in strategies[:2]:
                try:
                    result = await apply_strategy(
                        strategy_name, optimized_content, provider=provider
                    )
                    optimized_content = result.optimized_text
                except Exception:
                    pass  # skip failed strategy, continue with others

            pre_score = score_card.overall
            score_card = compute_geo_score(
                optimized_content,
                keywords=keywords_flat[:10] if keywords_flat else None,
                platform=platforms[0] if platforms else None,
            )
            content_output = ExpertOutput(
                role=content_output.role,
                label=content_output.label + " (GEO优化版)",
                model=content_output.model,
                content=optimized_content,
                duration_ms=content_output.duration_ms,
            )

            # Save optimization experience for future reference.
            for s_name in strategies[:2]:
                try:
                    await save_experience(OptimizationExperience(
                        brand_id=brand_id,
                        platform=platforms[0],
                        industry=brand_data.get("industry", ""),
                        strategy_name=s_name,
                        score_before=pre_score,
                        score_after=score_card.overall,
                        improvement=score_card.overall - pre_score,
                        content_type="expert_pipeline",
                    ))
                except Exception:
                    pass  # non-critical

    total_duration = int((time.monotonic() - total_start) * 1000)

    return TeamReport(
        strategy=strategy_output,
        analysis=analysis_output,
        geo_optimization=geo_output,
        content=content_output,
        review=review_output,
        geo_scores=score_card.to_dict(),
        total_duration_ms=total_duration,
    )


async def run_single_expert(
    role: str,
    payload: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    provider: str = "openrouter",
) -> ExpertOutput:
    """Run a single expert for ad-hoc queries."""
    if role not in [e.value for e in ExpertRole]:
        raise ValueError(f"Unknown role: {role}. Available: {[e.value for e in ExpertRole]}")
    return await _run_expert(role, payload, context, provider)


def get_team_config() -> Dict[str, Any]:
    """Return the current expert team configuration."""
    return {
        "roles": [
            {
                "role": role.value,
                "label": ROLE_LABELS[role],
                "model": ROLE_MODEL_MAP[role],
                "provider": "openrouter",
            }
            for role in ExpertRole
        ],
        "pipeline_order": [
            "chief_strategist",
            "data_analyst + geo_optimizer (parallel)",
            "content_architect",
            "quality_reviewer",
        ],
        "feature_enabled": settings.FEATURE_EXPERT_TEAM,
    }
