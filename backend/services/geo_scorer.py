"""GEO semantic scoring engine.

Computes content quality metrics inspired by GEO-Analyzer:
- Claim Density: factual assertions per 100 words
- Citability Score: proportion of quotable content
- Extractability Score: ease of AI answer extraction
- Readability Score: structural clarity for AI parsing
- Overall GEO Score: weighted composite
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class GEOScoreCard:
    claim_density: float = 0.0
    citability: float = 0.0
    extractability: float = 0.0
    readability: float = 0.0
    overall: float = 0.0
    details: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, float | Dict[str, str]]:
        return {
            "claim_density": round(self.claim_density, 1),
            "citability": round(self.citability, 1),
            "extractability": round(self.extractability, 1),
            "readability": round(self.readability, 1),
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


def compute_geo_score(text: str) -> GEOScoreCard:
    """Compute all GEO metrics and the weighted overall score."""
    claim = compute_claim_density(text)
    cite = compute_citability(text)
    extract = compute_extractability(text)
    read = compute_readability(text)

    # Weighted: Citability 30%, ClaimDensity 25%, Extractability 25%, Readability 20%.
    overall = cite * 0.30 + claim * 0.25 + extract * 0.25 + read * 0.20

    word_count = _count_words(text)
    details = {
        "word_count": str(word_count),
        "claim_density_note": f"每100字断言数: {round(claim / 25, 1)}",
        "scoring_weights": "citability×0.30 + claim_density×0.25 + extractability×0.25 + readability×0.20",
    }

    return GEOScoreCard(
        claim_density=claim,
        citability=cite,
        extractability=extract,
        readability=read,
        overall=overall,
        details=details,
    )
