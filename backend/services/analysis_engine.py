import json
import logging
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from config import settings
from services.llm_service import generate_content

logger = logging.getLogger(__name__)


LONG_TAIL_HINTS = [
    "how",
    "what",
    "why",
    "best",
    "guide",
    "steps",
    "vs",
    "comparison",
    "case",
    "plan",
    "怎么",
    "如何",
    "为什么",
    "哪个好",
]

# Additional hints that indicate Q&A-structured content with high AI-citation potential.
QA_STRUCTURE_HINTS = [
    "?",
    "？",
    "怎么",
    "如何",
    "为什么",
    "什么是",
    "how to",
    "what is",
    "why does",
    "guide",
    "教程",
    "方法",
    "步骤",
]

STOP_WORDS = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "this",
    "from",
    "your",
    "have",
    "will",
    "you",
    "are",
    "our",
    "我们",
    "你们",
    "他们",
    "这个",
    "那个",
}


def classify_keyword(keyword: str, brand_name: str, competitors: List[str]) -> str:
    key = keyword.lower().strip()
    if brand_name and brand_name.lower() in key:
        return "brand"
    for competitor in competitors:
        if competitor and competitor.lower() in key:
            return "competitor"
    if len(key) >= 12 or any(hint in key for hint in LONG_TAIL_HINTS):
        return "long_tail"
    return "industry"


def estimate_difficulty(keyword: str, competition_score: Optional[float] = None) -> str:
    # Use real competition data when available.
    if competition_score is not None:
        if competition_score >= 70:
            return "high"
        if competition_score >= 40:
            return "medium"
        return "low"
    size = len(keyword.strip())
    if size <= 4:
        return "high"
    if size <= 8:
        return "medium"
    return "low"


def score_keyword(
    keyword: str,
    intent: str,
    difficulty: str,
    covered: bool = False,
    has_qa_structure: bool = False,
    has_entity: bool = False,
    search_volume: int = 0,
    ai_citation_potential: float = 0.0,
) -> float:
    if settings.FEATURE_AGENT_TEAM:
        from services.agent_team import compute_geo_score
        return compute_geo_score(
            keyword=keyword,
            intent=intent,
            difficulty=difficulty,
            covered=covered,
            has_qa_structure=has_qa_structure,
            has_entity=has_entity,
        )

    # 本地评分逻辑（不依赖 agent_team）.
    score = 50.0
    if intent == "brand":
        score += 15
    elif intent == "long_tail":
        score += 10
    elif intent == "competitor":
        score += 5
    if difficulty == "low":
        score += 10
    elif difficulty == "high":
        score -= 5
    if has_qa_structure:
        score += 15
    if has_entity:
        score += 5
    if not covered:
        score += 5
    # Data enrichment bonus (when real data is available).
    if search_volume > 5000:
        score += 5
    elif search_volume > 1000:
        score += 2
    if ai_citation_potential > 70:
        score += 8
    elif ai_citation_potential > 40:
        score += 3
    return min(max(score, 0), 100)


def has_qa_structure(keyword: str) -> bool:
    """Return True if the keyword matches Q&A-style patterns (high AI-citation signal)."""
    key = keyword.lower().strip()
    return any(hint.lower() in key for hint in QA_STRUCTURE_HINTS)


def extract_topic_terms(text: str) -> List[str]:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text.lower())
    words = [part.strip() for part in cleaned.split() if len(part.strip()) >= 2]
    return [word for word in words if word not in STOP_WORDS]


def build_data_layer_summary(asset_texts: List[str], keywords: List[str]) -> Dict[str, Any]:
    terms: List[str] = []
    corpus = "\n".join(asset_texts).lower()
    for text in asset_texts:
        terms.extend(extract_topic_terms(text))

    frequencies = Counter(terms)
    top_terms = [term for term, _ in frequencies.most_common(30)]

    covered_keywords: List[str] = []
    for keyword in keywords:
        pieces = [piece for piece in re.split(r"\s+", keyword.lower()) if piece]
        if not pieces:
            continue
        exact_hit = keyword.lower() in corpus
        token_hit = any(piece in corpus or piece in top_terms for piece in pieces)
        if exact_hit or token_hit:
            covered_keywords.append(keyword)

    missing_keywords = [keyword for keyword in keywords if keyword not in covered_keywords]

    # Compute Q&A structure signals for better GEO awareness.
    qa_keywords = [kw for kw in keywords if has_qa_structure(kw)]

    return {
        "asset_count": len(asset_texts),
        "top_terms": top_terms,
        "covered_keywords": covered_keywords,
        "missing_keywords": missing_keywords,
        "coverage_ratio": round(len(covered_keywords) / max(1, len(keywords)), 4),
        "qa_structure_keywords": qa_keywords,
        "geo_visibility_score": round(
            (len(covered_keywords) / max(1, len(keywords))) * 0.6
            + (len(qa_keywords) / max(1, len(keywords))) * 0.4,
            4,
        ),
    }


def build_recommendations(
    keyword_layers: Dict[str, List[Dict[str, Any]]],
    data_layer: Dict[str, Any],
) -> List[str]:
    recommendations: List[str] = []
    missing_keywords = data_layer.get("missing_keywords", [])
    covered_keywords = data_layer.get("covered_keywords", [])
    geo_visibility = data_layer.get("geo_visibility_score", 0)
    qa_kws = data_layer.get("qa_structure_keywords", [])

    if data_layer["coverage_ratio"] < 0.5:
        top_missing = "、".join(missing_keywords[:5]) if missing_keywords else "核心关键词"
        recommendations.append(f"先补齐缺失关键词内容：优先覆盖 {top_missing}，再扩大发布。")
    elif covered_keywords:
        top_covered = "、".join(covered_keywords[:3])
        recommendations.append(f"已覆盖关键词可继续扩写：{top_covered}，用于形成专题矩阵。")

    if keyword_layers.get("competitor"):
        recommendations.append("针对竞品词制作对比型内容，突出服务差异与方法论边界。")

    if keyword_layers.get("long_tail"):
        recommendations.append("长尾问题采用问答式结构，提高在 AI 搜索中的可引用概率。")

    if geo_visibility < 0.4:
        recommendations.append(
            "GEO 可见性偏低（当前得分 {:.0%}）：建议将核心内容改写为问答格式，"
            "增加数据锚点和可引用结论，提升 AI 搜索引用率。".format(geo_visibility)
        )
    elif qa_kws:
        top_qa = "、".join(qa_kws[:3])
        recommendations.append(
            f"已有问答型关键词（{top_qa}）具备较高 GEO 潜力，优先为这些词生成结构化问答内容。"
        )

    recommendations.append("建立固定发布节奏：每周 1 个主话题 + 2 个平台改写版本。")
    recommendations.append("每篇内容增加结论句、步骤清单和风险提示，提升可读性和转化。")

    return recommendations


def _fallback_summary(payload: Dict[str, Any]) -> str:
    gap = payload.get("gap_analysis", {})
    recommendations = payload.get("recommendations", [])
    missing = gap.get("missing_keywords", [])
    top_terms = gap.get("top_terms", [])[:8]
    brand = payload.get("brand", {}).get("name", "当前品牌")
    geo_visibility = gap.get("geo_visibility_score", 0)

    lines = [
        f"# {brand} GEO 分析摘要",
        "",
        "## 1. 核心结论",
        f"- 当前关键词覆盖率：{gap.get('coverage_ratio', 0)}",
        f"- GEO 可见性综合得分：{geo_visibility:.1%}",
        f"- 待补齐关键词数：{len(missing)}",
        f"- 高相关主题词：{', '.join(top_terms) if top_terms else '暂无'}",
        "",
        "## 2. 优先动作（按优先级）",
    ]

    for idx, item in enumerate(recommendations[:5], start=1):
        lines.append(f"{idx}. {item}（优先级：高）")

    lines.extend(
        [
            "",
            "## 3. 下一轮验证指标",
            "- 7 天内缺失关键词覆盖率提升到 0.7+",
            "- GEO 可见性得分提升至 0.6+",
            "- 主平台内容完成率 >= 90%",
            "- 发布后 48 小时互动率与线索率持续追踪",
        ]
    )
    return "\n".join(lines)


def _is_summary_actionable(payload: Dict[str, Any], text: str) -> bool:
    if not text:
        return False
    required_sections = ["## 1.", "## 2.", "## 3.", "## 4.", "## 5."]
    if any(section not in text for section in required_sections):
        return False

    keywords: List[str] = []
    for layer in ("brand", "industry", "long_tail", "competitor"):
        for item in payload.get("keyword_layers", {}).get(layer, []):
            keyword = str(item.get("keyword", "")).strip()
            if keyword:
                keywords.append(keyword)
    if not keywords:
        return True

    hit = 0
    lowered = text.lower()
    for keyword in keywords[:8]:
        if keyword.lower() in lowered:
            hit += 1
    # At least 2 keyword hits (or all hits if less than 2 keywords).
    required_hits = min(2, len(keywords))
    return hit >= required_hits


async def build_llm_summary(
    payload: Dict[str, Any],
    model: Optional[str] = None,
) -> str:
    prompt = (
        "你是 GEO 策略分析师。请仅使用中文输出 Markdown 报告。"
        "不要输出英文段落，不要空话。\n"
        "必须包含以下固定章节：\n"
        "## 1. 核心结论（3条）\n"
        "## 2. 关键词分层与缺口（品牌词/行业词/长尾词/竞品词）\n"
        "## 3. 平台动作计划（公众号/小红书/知乎/短视频）\n"
        "## 4. 本周执行清单（5条可执行动作，每条包含优先级）\n"
        "## 5. 风险与合规提示（2条）\n\n"
        f"输入数据：\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    try:
        content = await generate_content(
            prompt=prompt,
            role="analysis_strategist",
            temperature=0.25,
            max_tokens=1800,
            model=model or None,
        )
        text = (content or "").strip()
        if not text:
            return _fallback_summary(payload)
        if not _is_summary_actionable(payload, text):
            return _fallback_summary(payload)
        return text
    except Exception:
        logger.exception("LLM summary generation failed, using fallback")
        return _fallback_summary(payload)


async def build_agent_team_summary(
    payload: Dict[str, Any],
    roles: Optional[List[str]] = None,
) -> str:
    """
    Run the expert agent team and assemble a multi-section comprehensive report.

    Priority order:
    1. agent_team (V2, FEATURE_AGENT_TEAM=True) — legacy multi-agent pipeline
    2. expert_team (MVP, FEATURE_EXPERT_TEAM=True) — 5-role expert pipeline
    3. _fallback_summary — offline template
    """
    # 路径1：agent_team（V2，默认关闭）
    if settings.OPENROUTER_API_KEY and settings.FEATURE_AGENT_TEAM:
        try:
            from services.agent_team import run_agent_team, assemble_team_report
            reports = await run_agent_team(payload, roles=roles)
            assembled = assemble_team_report(reports)
            if assembled and assembled.strip():
                return assembled
        except Exception:
            pass  # fall through to expert_team

    # 路径2：expert_team（MVP 默认路径）
    if settings.OPENROUTER_API_KEY and settings.FEATURE_EXPERT_TEAM:
        try:
            from services.expert_team import run_expert_pipeline
            report = await run_expert_pipeline(
                brand_data=payload.get("brand", {}),
                keyword_layers=payload.get("keyword_layers", {}),
                gap_analysis=payload.get("gap_analysis", {}),
                recommendations=payload.get("recommendations", []),
            )
            md = report.to_markdown()
            if md and md.strip():
                return md
        except Exception:
            pass

    return _fallback_summary(payload)
