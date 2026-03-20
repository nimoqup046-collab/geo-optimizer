"""Pluggable GEO optimization strategies.

Inspired by GEO-optim and AutoGEO — each strategy transforms content
to improve AI search engine visibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from services.llm_service import LLMService
from config import settings


@dataclass
class StrategyResult:
    strategy_name: str
    original_text: str
    optimized_text: str
    changes_made: List[str]
    estimated_improvement: str


STRATEGY_PROMPTS: Dict[str, str] = {
    "citation_enhancement": (
        "请对以下内容进行「引用增强」优化。\n"
        "要求：\n"
        "1. 每 300 字至少添加 1 个可信引用（行业报告、研究数据、专家观点）\n"
        "2. 引用必须与上下文自然融合，不能生硬插入\n"
        "3. 使用「根据XX研究/报告」「XX数据显示」等引用句式\n"
        "4. 保持原文核心观点不变\n\n"
        "输出格式：\n"
        "## 优化后内容\n[完整优化后内容]\n\n"
        "## 变更说明\n[列出每处引用增强的位置和内容]"
    ),
    "statistics_addition": (
        "请对以下内容进行「数据统计增强」优化。\n"
        "要求：\n"
        "1. 将模糊描述替换为具体数据（百分比、数字、时间周期）\n"
        "2. 添加行业统计数据和研究结论\n"
        "3. 确保数据合理可信（不编造不存在的研究）\n"
        "4. 数据点均匀分布在全文中\n\n"
        "输出格式：\n"
        "## 优化后内容\n[完整优化后内容]\n\n"
        "## 变更说明\n[列出每处数据增强的位置和内容]"
    ),
    "qa_structuring": (
        "请对以下内容进行「问答结构化」优化。\n"
        "要求：\n"
        "1. 识别内容中隐含的 3-5 个用户高频问题\n"
        "2. 在适当位置嵌入 Q&A 格式的子标题\n"
        "3. 确保每个问题的回答简洁、具体、可被 AI 直接引用\n"
        "4. 保持原文信息完整性\n\n"
        "输出格式：\n"
        "## 优化后内容\n[完整优化后内容]\n\n"
        "## 变更说明\n[列出嵌入的问题及其位置]"
    ),
    "answer_frontloading": (
        "请对以下内容进行「断言前置」优化。\n"
        "要求：\n"
        "1. 将核心结论/答案移到文章开头（前 50 字内）\n"
        "2. 使用 TL;DR 或「核心结论：」格式\n"
        "3. 确保 AI 搜索引擎扫描前 2 句即可提取答案\n"
        "4. 后续内容作为支撑论证\n\n"
        "输出格式：\n"
        "## 优化后内容\n[完整优化后内容]\n\n"
        "## 变更说明\n[说明前置了哪些核心断言]"
    ),
    "entity_enrichment": (
        "请对以下内容进行「实体丰富」优化。\n"
        "要求：\n"
        "1. 增加专业术语、机构名、方法论名称等命名实体\n"
        "2. 自然地引入行业权威机构和标准\n"
        "3. 使用术语时给出简短释义，便于理解\n"
        "4. 提升内容的专业性和可信度\n\n"
        "输出格式：\n"
        "## 优化后内容\n[完整优化后内容]\n\n"
        "## 变更说明\n[列出添加的实体和术语]"
    ),
}

AVAILABLE_STRATEGIES = list(STRATEGY_PROMPTS.keys())


async def apply_strategy(
    strategy_name: str,
    content: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> StrategyResult:
    """Apply a single GEO optimization strategy to content."""
    if strategy_name not in STRATEGY_PROMPTS:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available: {AVAILABLE_STRATEGIES}")

    system_prompt = (
        "你是 GEO 优化专家，专注于提升内容在 AI 搜索引擎中的可见性。"
        "严格按照要求的输出格式返回结果。"
    )
    user_prompt = f"{STRATEGY_PROMPTS[strategy_name]}\n\n待优化内容：\n{content}"

    use_provider = provider or "openrouter"
    use_model = model or settings.EXPERT_GEO_MODEL

    async with LLMService(use_provider) as llm:
        result = await llm.generate(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=use_model,
            temperature=0.3,
            max_tokens=3000,
        )

    # Parse the output.
    optimized = result
    changes: List[str] = []

    if "## 优化后内容" in result and "## 变更说明" in result:
        parts = result.split("## 变更说明")
        optimized = parts[0].replace("## 优化后内容", "").strip()
        if len(parts) > 1:
            changes = [
                line.strip().lstrip("- ").lstrip("* ")
                for line in parts[1].strip().splitlines()
                if line.strip() and not line.startswith("#")
            ]

    return StrategyResult(
        strategy_name=strategy_name,
        original_text=content,
        optimized_text=optimized,
        changes_made=changes,
        estimated_improvement=_estimate_improvement(strategy_name),
    )


async def apply_multiple_strategies(
    strategies: List[str],
    content: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> List[StrategyResult]:
    """Apply multiple strategies sequentially, each building on the previous output."""
    results: List[StrategyResult] = []
    current_content = content
    for strategy in strategies:
        result = await apply_strategy(strategy, current_content, provider, model)
        results.append(result)
        current_content = result.optimized_text
    return results


def _estimate_improvement(strategy_name: str) -> str:
    estimates = {
        "citation_enhancement": "可见性提升约 30-40%（基于 GEO-optim 研究）",
        "statistics_addition": "可见性提升约 25-35%（基于 GEO-optim 研究）",
        "qa_structuring": "AI 引用概率提升约 20-30%",
        "answer_frontloading": "AI 提取准确率提升约 25-35%",
        "entity_enrichment": "内容专业性评分提升约 15-25%",
    }
    return estimates.get(strategy_name, "预期有显著提升")
