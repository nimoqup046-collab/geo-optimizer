"""GEO semantic scoring engine.

Computes content quality metrics inspired by GEO-Analyzer and Princeton KDD 2024:
- Authority Citation (权威性引用): credibility via expert/institutional references
- Structured Data (结构化数据): Schema markup, FAQ, tables, lists
- Keyword Coverage (关键词覆盖度): keyword + long-tail + related term coverage
- Credibility Signals (可信度信号): specific numbers, cases, source attribution
- Platform Fitness (平台适配度): style match to target platform conventions
- Freshness (更新时效性): recency of information and temporal signals

Legacy dimensions retained for backward compatibility:
- Claim Density, Citability, Extractability, Readability
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class GEOScoreCard:
    claim_density: float = 0.0
    citability: float = 0.0
    extractability: float = 0.0
    readability: float = 0.0
    # -- new 6-dimension scores --
    authority_citation: float = 0.0
    structured_data: float = 0.0
    keyword_coverage: float = 0.0
    credibility_signals: float = 0.0
    platform_fitness: float = 0.0
    freshness: float = 0.0
    overall: float = 0.0
    details: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, float | Dict[str, str]]:
        return {
            "claim_density": round(self.claim_density, 1),
            "citability": round(self.citability, 1),
            "extractability": round(self.extractability, 1),
            "readability": round(self.readability, 1),
            "authority_citation": round(self.authority_citation, 1),
            "structured_data": round(self.structured_data, 1),
            "keyword_coverage": round(self.keyword_coverage, 1),
            "credibility_signals": round(self.credibility_signals, 1),
            "platform_fitness": round(self.platform_fitness, 1),
            "freshness": round(self.freshness, 1),
            "overall": round(self.overall, 1),
            "details": self.details,
        }


# Patterns that indicate factual claims / assertions.
_CLAIM_PATTERNS = [
    r"\d+%",  # percentages
    r"\d+\s*[万亿千百]",  # chinese number units
    r"研究表明|数据显示|调查发现|根据",  # research indicators
    r"第[一二三四五六七八九十\d]+",  # ordinal markers
    r"步骤\s*[：:]|方法\s*[：:]",  # step indicators
    r"结论[：:]|核心观点[：:]",  # conclusion markers
    r"\d{4}\s*年",  # year references
    r"平均|中位数|增长率|比例|占比",  # statistics terms
]

# Patterns indicating structured / extractable content.
_STRUCTURE_PATTERNS = [
    r"^#{1,4}\s+",  # markdown headings
    r"^\d+[\.\)、]\s+",  # numbered lists
    r"^[-*]\s+",  # bullet lists
    r"\|.*\|.*\|",  # table rows
    r"[？?]",  # questions (Q&A structure)
]

# Indicators of high citability.
_CITABILITY_PATTERNS = [
    r"^>",  # blockquotes
    r'「.*?」|\u201c.*?\u201d',  # quoted text (Chinese quotes)
    r"根据.{2,20}(的|发布的)",  # attribution phrases
    r"来源[：:]|引用[：:]|参考[：:]",  # source markers
    r"\d+%|\d+\.\d+",  # specific numbers
]


def _count_words(text: str) -> int:
    """Count words: Chinese characters count individually, latin words by spaces."""
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[a-zA-Z]+", text))
    return chinese + latin


def _count_pattern_matches(text: str, patterns: List[str]) -> int:
    total = 0
    for pattern in patterns:
        total += len(re.findall(pattern, text, re.MULTILINE))
    return total


def _sentence_lengths(text: str) -> List[int]:
    """Split text into sentences and return word counts per sentence."""
    sentences = re.split(r"[。！？\.\!\?；;]+", text)
    return [_count_words(s) for s in sentences if s.strip()]


def compute_claim_density(text: str) -> float:
    """Claims per 100 words, mapped to 0-100 score."""
    word_count = _count_words(text)
    if word_count == 0:
        return 0.0
    claims = _count_pattern_matches(text, _CLAIM_PATTERNS)
    density = (claims / word_count) * 100
    # Target: 4+ claims per 100 words = 100 score.
    score = min(100.0, (density / 4.0) * 100)
    return score


def compute_citability(text: str) -> float:
    """Score based on presence of quotable, attributable content."""
    word_count = _count_words(text)
    if word_count == 0:
        return 0.0
    matches = _count_pattern_matches(text, _CITABILITY_PATTERNS)
    # Also count specific data points.
    data_points = len(re.findall(r"\d+[\.\d]*[%％]|\d+\s*[万亿]", text))
    total = matches + data_points
    # Target: 1 citability indicator per 150 words = 100 score.
    expected = max(1, word_count / 150)
    score = min(100.0, (total / expected) * 100)
    return score


def compute_extractability(text: str) -> float:
    """Score based on structure friendliness for AI extraction."""
    lines = text.strip().splitlines()
    if not lines:
        return 0.0

    score = 50.0  # baseline

    # Heading presence.
    headings = sum(1 for line in lines if re.match(r"^#{1,4}\s+", line))
    if headings >= 3:
        score += 15
    elif headings >= 1:
        score += 8

    # List items.
    list_items = sum(
        1 for line in lines if re.match(r"^\s*(\d+[\.\)、]|[-*])\s+", line)
    )
    if list_items >= 5:
        score += 15
    elif list_items >= 2:
        score += 8

    # Answer frontloading: first 100 chars contain a claim.
    first_chunk = text[:150]
    if _count_pattern_matches(first_chunk, _CLAIM_PATTERNS) > 0:
        score += 10

    # Table presence.
    if re.search(r"\|.*\|.*\|", text):
        score += 10

    return min(100.0, score)


def compute_readability(text: str) -> float:
    """Score based on sentence length distribution and paragraph structure."""
    lengths = _sentence_lengths(text)
    if not lengths:
        return 0.0

    avg_len = sum(lengths) / len(lengths)
    score = 50.0

    # Ideal sentence length: 15-25 words.
    if 15 <= avg_len <= 25:
        score += 25
    elif 10 <= avg_len <= 35:
        score += 15
    elif avg_len > 50:
        score -= 10

    # Variety (not all same length).
    if len(lengths) > 2:
        length_set = set(lengths)
        if len(length_set) > len(lengths) * 0.5:
            score += 10

    # Paragraph breaks.
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) >= 3:
        score += 15
    elif len(paragraphs) >= 2:
        score += 8

    return min(100.0, max(0.0, score))


_EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001F9FF\u2600-\u26FF\u2700-\u27BF]"
)

_AUTHORITY_PATTERNS = [
    r"根据.{2,30}(研究|报告|调查|数据)",  # "according to ... study/report/survey/data"
    r"(教授|博士|专家|学者|院士).{0,10}(指出|认为|表示|建议)",
    r"(大学|研究院|实验室|学会|协会).{0,15}(发现|发布|报告)",
    r"(世界卫生组织|WHO|联合国|国务院|教育部)",  # institutional references
    r"(Nature|Science|Lancet|JAMA|柳叶刀|新英格兰)",  # journal names
    r"SCI|SSCI|CSSCI|核心期刊",  # academic index references
    r"(行业报告|白皮书|蓝皮书|年度报告)",
]

_FRESHNESS_PATTERNS = [
    r"202[3-9]\s*年",  # recent years
    r"最新|最近|近期|今年|本年度|上半年|下半年",
    r"第[一二三四]季度|Q[1-4]",
    r"截至\s*\d{4}",
    r"最新数据|最新研究|最新报告",
    r"更新于|发布于|日期",
]

_CREDIBILITY_PATTERNS = [
    r"\d+\.?\d*[%％]",  # percentages
    r"\d+\s*(例|位|人|名|家|个案例)",  # specific counts
    r"案例[：:].{5,}",  # case descriptions
    r"来源[：:]|出处[：:]|数据来源",  # source attribution
    r"实证|循证|对照|随机|双盲",  # evidence-based terms
    r"P\s*[<>]\s*0\.\d+",  # statistical significance
]


def compute_authority_citation(text: str) -> float:
    """Score based on presence of authoritative references and expert citations."""
    word_count = _count_words(text)
    if word_count == 0:
        return 0.0
    matches = _count_pattern_matches(text, _AUTHORITY_PATTERNS)
    # Target: 1 authority marker per 200 words = 100 score.
    expected = max(1, word_count / 200)
    score = min(100.0, (matches / expected) * 100)
    return score


def compute_structured_data(text: str) -> float:
    """Score based on structured data elements (Schema-ready, FAQ, tables, lists)."""
    lines = text.strip().splitlines()
    if not lines:
        return 0.0

    score = 30.0  # baseline

    # FAQ / Q&A patterns.
    qa_patterns = sum(
        1 for line in lines if re.match(r"^\s*(Q[：:]|问[：:]|[？?])", line)
    )
    if qa_patterns >= 3:
        score += 20
    elif qa_patterns >= 1:
        score += 10

    # Table presence.
    table_rows = sum(1 for line in lines if re.match(r"\s*\|.*\|.*\|", line))
    if table_rows >= 3:
        score += 20
    elif table_rows >= 1:
        score += 10

    # Numbered / bullet lists.
    list_items = sum(
        1 for line in lines if re.match(r"^\s*(\d+[\.\)、]|[-*✅❌⚠️])\s+", line)
    )
    if list_items >= 5:
        score += 15
    elif list_items >= 2:
        score += 8

    # Headings (markdown).
    headings = sum(1 for line in lines if re.match(r"^#{1,4}\s+", line))
    if headings >= 3:
        score += 15
    elif headings >= 1:
        score += 8

    return min(100.0, score)


def compute_keyword_coverage(
    text: str, keywords: Optional[List[str]] = None
) -> float:
    """Score based on keyword and related term coverage.

    If *keywords* is ``None`` the score is based on structural keyword
    density heuristics only.
    """
    word_count = _count_words(text)
    if word_count == 0:
        return 0.0

    if keywords:
        found = sum(1 for kw in keywords if kw.lower() in text.lower())
        coverage_ratio = found / len(keywords) if keywords else 0
        score = min(100.0, coverage_ratio * 100)
    else:
        # Heuristic: evaluate keyword-like density via bold / header terms.
        bold_count = len(re.findall(r"\*\*(.+?)\*\*", text))
        header_count = len(re.findall(r"^#{1,4}\s+(.+)", text, re.MULTILINE))
        total_markers = bold_count + header_count
        expected = max(1, word_count / 200)
        score = min(100.0, (total_markers / expected) * 100)

    return score


def compute_credibility_signals(text: str) -> float:
    """Score based on specific data, cases, and source attribution."""
    word_count = _count_words(text)
    if word_count == 0:
        return 0.0
    matches = _count_pattern_matches(text, _CREDIBILITY_PATTERNS)
    data_points = len(re.findall(r"\d+[\.\d]*[%％]|\d+\s*[万亿]", text))
    total = matches + data_points
    expected = max(1, word_count / 150)
    score = min(100.0, (total / expected) * 100)
    return score


def compute_platform_fitness(
    text: str, platform: Optional[str] = None
) -> float:
    """Score how well the content matches the target platform conventions.

    Without a *platform* hint the score is based on generic quality
    heuristics.  When a platform is given, length / emoji / structure
    checks are applied.
    """
    word_count = _count_words(text)
    if word_count == 0:
        return 0.0

    score = 50.0  # baseline

    platform_checks = {
        "xiaohongshu": {
            "min_words": 300, "max_words": 800,
            "emoji_expected": True, "short_paragraphs": True,
        },
        "wechat": {
            "min_words": 1200, "max_words": 2200,
            "emoji_expected": False, "short_paragraphs": False,
        },
        "zhihu": {
            "min_words": 800, "max_words": 1500,
            "emoji_expected": False, "short_paragraphs": False,
        },
        "video": {
            "min_words": 100, "max_words": 500,
            "emoji_expected": False, "short_paragraphs": True,
        },
    }

    if platform and platform in platform_checks:
        spec = platform_checks[platform]
        if spec["min_words"] <= word_count <= spec["max_words"]:
            score += 25
        elif word_count < spec["min_words"] * 0.5 or word_count > spec["max_words"] * 1.5:
            score -= 10

        emoji_count = len(_EMOJI_PATTERN.findall(text))
        if spec["emoji_expected"] and emoji_count >= 3:
            score += 15
        elif not spec["emoji_expected"] and emoji_count == 0:
            score += 10

        paragraphs = [p for p in text.split("\n") if p.strip()]
        avg_para_len = (
            sum(_count_words(p) for p in paragraphs) / len(paragraphs)
            if paragraphs else 0
        )
        if spec["short_paragraphs"] and avg_para_len <= 80:
            score += 10
        elif not spec["short_paragraphs"] and avg_para_len >= 40:
            score += 10
    else:
        # Generic quality heuristics.
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        if 3 <= len(paragraphs) <= 15:
            score += 20
        headings = len(re.findall(r"^#{1,4}\s+", text, re.MULTILINE))
        if headings >= 2:
            score += 15

    return min(100.0, max(0.0, score))


def compute_freshness(text: str) -> float:
    """Score based on temporal signals and information recency."""
    word_count = _count_words(text)
    if word_count == 0:
        return 0.0
    matches = _count_pattern_matches(text, _FRESHNESS_PATTERNS)
    score = 40.0  # baseline for content without explicit dates
    if matches >= 4:
        score += 60
    elif matches >= 2:
        score += 40
    elif matches >= 1:
        score += 20
    return min(100.0, score)


def compute_geo_score(
    text: str,
    keywords: Optional[List[str]] = None,
    platform: Optional[str] = None,
) -> GEOScoreCard:
    """Compute all GEO metrics and the weighted overall score.

    The 6-dimension model follows the Princeton KDD 2024 paper with
    practical enhancements:

    * 权威性引用 (Authority Citation)   – 20 %
    * 结构化数据 (Structured Data)       – 15 %
    * 关键词覆盖度 (Keyword Coverage)    – 20 %
    * 可信度信号 (Credibility Signals)   – 15 %
    * 平台适配度 (Platform Fitness)      – 15 %
    * 更新时效性 (Freshness)             – 15 %
    """
    # Legacy dimensions (still useful for detailed diagnostics).
    claim = compute_claim_density(text)
    cite = compute_citability(text)
    extract = compute_extractability(text)
    read = compute_readability(text)

    # New 6-dimension scores.
    authority = compute_authority_citation(text)
    structured = compute_structured_data(text)
    kw_coverage = compute_keyword_coverage(text, keywords)
    credibility = compute_credibility_signals(text)
    p_fitness = compute_platform_fitness(text, platform)
    fresh = compute_freshness(text)

    # 6-dimension weighted overall score.
    overall = (
        authority * 0.20
        + structured * 0.15
        + kw_coverage * 0.20
        + credibility * 0.15
        + p_fitness * 0.15
        + fresh * 0.15
    )

    word_count = _count_words(text)
    details = {
        "word_count": str(word_count),
        "claim_density_note": f"每100字断言数: {round(claim / 25, 1) if claim else 0}",
        "scoring_model": "6-dimension (Princeton KDD 2024 enhanced)",
        "scoring_weights": (
            "authority_citation×0.20 + structured_data×0.15 "
            "+ keyword_coverage×0.20 + credibility_signals×0.15 "
            "+ platform_fitness×0.15 + freshness×0.15"
        ),
    }

    scorecard = GEOScoreCard(
        claim_density=claim,
        citability=cite,
        extractability=extract,
        readability=read,
        authority_citation=authority,
        structured_data=structured,
        keyword_coverage=kw_coverage,
        credibility_signals=credibility,
        platform_fitness=p_fitness,
        freshness=fresh,
        overall=overall,
        details=details,
    )

    # Inject strategy suggestions based on weak dimensions.
    strategies = suggest_optimization_strategies(scorecard)
    if strategies:
        details["suggested_strategies"] = ", ".join(strategies)
    weak_dims = [
        dim for dim in _GEO_DIMENSIONS
        if getattr(scorecard, dim) < 65.0
    ]
    if weak_dims:
        details["weakest_dimensions"] = ", ".join(weak_dims)

    return scorecard


# ---------------------------------------------------------------------------
# Dimension → optimization strategy mapping (for feedback loop)
# ---------------------------------------------------------------------------

_GEO_DIMENSIONS = [
    "authority_citation", "structured_data", "keyword_coverage",
    "credibility_signals", "platform_fitness", "freshness",
]

DIMENSION_STRATEGY_MAP: Dict[str, List[str]] = {
    "authority_citation": ["citation_enhancement"],
    "structured_data": ["qa_structuring"],
    "keyword_coverage": ["topic_cluster_alignment", "entity_enrichment"],
    "credibility_signals": ["statistics_addition", "citation_enhancement"],
    "platform_fitness": [],  # requires regeneration, not patch optimization
    "freshness": ["statistics_addition"],
}


def suggest_optimization_strategies(
    scorecard: GEOScoreCard,
    threshold: float = 65.0,
) -> List[str]:
    """Suggest optimization strategies based on the weakest scoring dimensions.

    Returns an ordered, deduplicated list of strategy names targeting the
    3 weakest dimensions below *threshold*.
    """
    weak_dimensions = []
    for dim in _GEO_DIMENSIONS:
        score = getattr(scorecard, dim)
        if score < threshold:
            weak_dimensions.append((dim, score))

    weak_dimensions.sort(key=lambda x: x[1])  # weakest first

    strategies: List[str] = []
    for dim, _ in weak_dimensions[:3]:
        strategies.extend(DIMENSION_STRATEGY_MAP.get(dim, []))

    # Deduplicate while preserving order.
    return list(dict.fromkeys(strategies))
