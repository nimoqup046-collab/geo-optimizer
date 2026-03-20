"""
Expert Agent Team for GEO Optimizer.

Each agent represents a specialized expert role with its own system prompt and
preferred model.  When OpenRouter is available and FEATURE_AGENT_TEAM is
enabled, the analysis pipeline dispatches tasks to each agent in parallel and
assembles a structured multi-section report.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from config import settings
from services.llm_service import LLMService


# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------

@dataclass
class AgentSpec:
    """Specification for one expert agent."""

    name: str
    role_key: str
    model: str
    system_prompt: str
    section_heading: str
    max_tokens: int = 1800
    temperature: float = 0.25


def _analysis_model() -> str:
    """Return the preferred deep-analysis model (OpenRouter-routed)."""
    return settings.OPENROUTER_ANALYSIS_MODEL


def _content_model() -> str:
    """Return the preferred content-generation / data-synthesis model."""
    return settings.OPENROUTER_CONTENT_MODEL


AGENT_SPECS: list[AgentSpec] = [
    AgentSpec(
        name="GEO策略专家",
        role_key="geo_strategist",
        model=_analysis_model(),
        section_heading="## 一、GEO 策略分析（AI 搜索可见性优化）",
        system_prompt=(
            "你是顶级 GEO（Generative Engine Optimization）策略专家。"
            "专注于提升品牌内容在 ChatGPT、Perplexity、Gemini、Claude 等 AI 搜索引擎中的可引用率与权威度。\n"
            "分析框架：\n"
            "1. AI 可见性诊断：评估现有内容被 AI 引用的结构性障碍。\n"
            "2. 实体权威建设：识别需要强化的命名实体、数据锚点和权威引用。\n"
            "3. 问答对齐：将关键词映射为 AI 搜索中的高概率问题，并给出答案结构建议。\n"
            "4. 内容分层策略：品牌词→行业词→长尾问题 的三层 GEO 覆盖路径。\n"
            "5. 可执行动作：每条动作包含平台、优先级（高/中/低）、预期 GEO 增益。\n"
            "输出要求：仅用中文，Markdown 结构，每条建议必须可直接执行，禁止空话。"
        ),
        max_tokens=2000,
        temperature=0.2,
    ),
    AgentSpec(
        name="内容质量专家",
        role_key="content_quality",
        model=_content_model(),
        section_heading="## 二、内容质量与工坊优化建议",
        system_prompt=(
            "你是内容质量与传播策略专家，擅长多平台内容结构优化、可引用性提升和用户转化路径设计。\n"
            "分析维度：\n"
            "1. 内容结构审计：标题力、开篇钩子、段落逻辑、CTA 有效性。\n"
            "2. 平台适配评分：各平台（公众号/小红书/知乎/短视频）内容匹配度打分（0-10）。\n"
            "3. 可引用性优化：增加数据点、案例、步骤清单，提升被 AI 截取概率。\n"
            "4. 内容工坊提示词优化建议：针对现有模板给出具体改写方向。\n"
            "5. 内容日历建议：基于关键词分层给出 4 周内容排期框架。\n"
            "输出要求：仅用中文，Markdown 结构，评分需附简短理由，建议需附示例片段。"
        ),
        max_tokens=1800,
        temperature=0.3,
    ),
    AgentSpec(
        name="数据分析专家",
        role_key="data_analytics",
        model=_analysis_model(),
        section_heading="## 三、数据洞察与效果预测",
        system_prompt=(
            "你是内容营销数据分析专家，擅长从关键词覆盖数据、内容缺口和竞品对比中提炼可量化的增长路径。\n"
            "分析框架：\n"
            "1. 覆盖率基准：当前覆盖率与行业平均的差距量化。\n"
            "2. 关键词优先级矩阵：按（GEO分×难度倒数）排序，标注 TOP 5 高杠杆词。\n"
            "3. 内容-关键词映射热力图描述：哪些关键词簇缺少对应内容。\n"
            "4. 30 天增长预测：若执行建议，预期覆盖率/引用率提升幅度（保守/乐观区间）。\n"
            "5. 监测指标体系：给出 5 个 KPI 及采集方法。\n"
            "输出要求：仅用中文，Markdown 结构，数据预测需标注假设前提，禁止虚构具体数字。"
        ),
        max_tokens=1600,
        temperature=0.15,
    ),
    AgentSpec(
        name="竞品情报专家",
        role_key="competitor_intel",
        model=_content_model(),
        section_heading="## 四、竞品情报与差异化定位",
        system_prompt=(
            "你是竞品情报与品牌差异化定位专家，专注于在 AI 搜索时代建立不可替代的内容护城河。\n"
            "分析框架：\n"
            "1. 竞品关键词侵占分析：竞品在哪些高价值词上已建立优势。\n"
            "2. 差异化切入点：品牌独特方法论、服务边界、结果指标的提炼。\n"
            "3. 对比内容策略：针对每个竞品词设计 '对比型' 内容角度。\n"
            "4. 护城河建设路径：如何通过专有数据、案例库、行业报告建立不可复制的 GEO 优势。\n"
            "5. 风险预警：竞品可能的反制动作与应对策略。\n"
            "输出要求：仅用中文，Markdown 结构，竞品词分析需具体，禁止空泛表述。"
        ),
        max_tokens=1600,
        temperature=0.25,
    ),
]


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------

@dataclass
class AgentReport:
    """Result produced by one agent."""

    agent_name: str
    role_key: str
    section_heading: str
    content: str
    model_used: str
    error: Optional[str] = None


async def _run_agent(agent: AgentSpec, payload: Dict[str, Any]) -> AgentReport:
    """Run a single agent against the analysis payload."""
    user_prompt = (
        "请根据以下 GEO 分析数据，严格按照你的专业职责输出分析报告章节。\n"
        "要求：中文输出，Markdown，每条建议可直接执行。\n\n"
        f"分析数据：\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
    messages = [
        {"role": "system", "content": agent.system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        async with LLMService(provider="openrouter") as llm:
            content = await llm.generate(
                messages=messages,
                model=agent.model,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens,
            )
        return AgentReport(
            agent_name=agent.name,
            role_key=agent.role_key,
            section_heading=agent.section_heading,
            content=(content or "").strip(),
            model_used=agent.model,
        )
    except Exception as exc:
        return AgentReport(
            agent_name=agent.name,
            role_key=agent.role_key,
            section_heading=agent.section_heading,
            content="",
            model_used=agent.model,
            error=str(exc),
        )


async def run_agent_team(
    payload: Dict[str, Any],
    roles: Optional[list[str]] = None,
) -> list[AgentReport]:
    """
    Run all (or a subset of) expert agents concurrently and return their reports.

    Args:
        payload: The same dict passed to the regular analysis LLM call.
        roles:   Optional list of role_key strings to restrict which agents run.
                 If None, all four agents run.
    """
    import asyncio

    selected = [a for a in AGENT_SPECS if roles is None or a.role_key in roles]
    if not selected:
        selected = AGENT_SPECS

    tasks = [_run_agent(agent, payload) for agent in selected]
    return list(await asyncio.gather(*tasks))


def assemble_team_report(reports: list[AgentReport]) -> str:
    """
    Assemble the per-agent reports into a single structured Markdown document.
    """
    lines: list[str] = [
        "# GEO 专家团队综合分析报告\n",
        "> 本报告由四位顶级专家 Agent 协作生成，覆盖 GEO 策略、内容质量、数据洞察与竞品情报。\n",
    ]
    for report in reports:
        lines.append(f"\n{report.section_heading}\n")
        if report.error:
            lines.append(f"> ⚠️ 专家 [{report.agent_name}] 分析失败：{report.error}\n")
        elif report.content:
            lines.append(report.content)
        else:
            lines.append("> 暂无输出。\n")
        lines.append(f"\n*模型：{report.model_used}*\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GEO scoring helpers (enhanced)
# ---------------------------------------------------------------------------

def compute_geo_score(
    keyword: str,
    intent: str,
    difficulty: str,
    covered: bool,
    has_qa_structure: bool = False,
    has_entity: bool = False,
) -> float:
    """
    Enhanced GEO score that factors in:
    - keyword intent and difficulty (existing)
    - whether the keyword is already covered in the content corpus
    - whether the content uses Q&A structure (high AI-citation probability)
    - whether the keyword maps to a named entity (brand/product/person)
    """
    score = 50.0

    # Intent bonus
    intent_bonus = {"brand": 22.0, "long_tail": 12.0, "competitor": 6.0, "industry": 4.0}
    score += intent_bonus.get(intent, 0.0)

    # Difficulty adjustment
    if difficulty == "low":
        score += 14.0
    elif difficulty == "high":
        score -= 10.0

    # AI-search quality signals
    if has_qa_structure:
        score += 8.0   # Q&A format → higher AI citation rate
    if has_entity:
        score += 5.0   # Named entity → AI trusts authoritative answers

    # Coverage gap penalty/bonus
    if covered:
        score += 5.0
    else:
        score -= 3.0   # Missing content = GEO risk

    # Long-keyword penalty
    if len(keyword.strip()) > 20:
        score -= 3.0

    return max(1.0, min(100.0, score))
