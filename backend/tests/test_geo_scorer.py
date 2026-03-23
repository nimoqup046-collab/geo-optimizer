"""Tests for the GEO scoring engine."""

import sys
from pathlib import Path

# Allow imports from the backend package when running via ``pytest`` from
# the repo root or the ``backend/`` directory.
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from services.geo_scorer import (
    GEOScoreCard,
    compute_authority_citation,
    compute_claim_density,
    compute_citability,
    compute_credibility_signals,
    compute_extractability,
    compute_freshness,
    compute_geo_score,
    compute_keyword_coverage,
    compute_platform_fitness,
    compute_readability,
    compute_structured_data,
    suggest_optimization_strategies,
)


# ---------------------------------------------------------------------------
# Legacy dimensions
# ---------------------------------------------------------------------------


class TestClaimDensity:
    def test_empty_text(self):
        assert compute_claim_density("") == 0.0

    def test_text_with_percentages(self):
        text = "研究表明 60% 的用户在 2024 年选择了新方案，增长率达到 35%。"
        score = compute_claim_density(text)
        assert score > 0

    def test_text_without_claims(self):
        text = "这是一段普通的文字，没有任何数据或引用。"
        score = compute_claim_density(text)
        assert score == 0.0


class TestCitability:
    def test_empty_text(self):
        assert compute_citability("") == 0.0

    def test_text_with_quotes_and_sources(self):
        text = (
            "根据哈佛大学发布的研究，婚姻满意度在结婚 7 年后下降 23%。\n"
            "来源：Harvard Family Research, 2024"
        )
        score = compute_citability(text)
        assert score > 0


class TestExtractability:
    def test_empty_text(self):
        assert compute_extractability("") == 0.0

    def test_structured_text(self):
        text = (
            "# 主标题\n\n"
            "## 第一部分\n\n"
            "1. 第一步\n"
            "2. 第二步\n"
            "3. 第三步\n\n"
            "## 第二部分\n\n"
            "| 指标 | 数值 | 说明 |\n"
            "|------|------|------|\n"
            "| A    | 10   | 好   |\n"
        )
        score = compute_extractability(text)
        assert score >= 70  # well-structured content should score high


class TestReadability:
    def test_empty_text(self):
        assert compute_readability("") == 0.0

    def test_well_structured_text(self):
        text = (
            "婚姻修复需要双方共同努力。\n\n"
            "首先要建立有效的沟通渠道。\n\n"
            "其次需要理解对方的需求和感受。\n\n"
            "最后制定切实可行的改善计划。"
        )
        score = compute_readability(text)
        assert score > 0


# ---------------------------------------------------------------------------
# New 6-dimension scores
# ---------------------------------------------------------------------------


class TestAuthorityCitation:
    def test_empty_text(self):
        assert compute_authority_citation("") == 0.0

    def test_text_with_authority_markers(self):
        text = (
            "根据中国婚姻家庭研究会的调查报告，2024 年离婚率同比下降 5%。\n"
            "心理学教授张三指出，依恋理论在婚姻修复中的应用效果显著。\n"
            "北京大学心理学实验室发现，情绪聚焦疗法的有效率达到 78%。"
        )
        score = compute_authority_citation(text)
        assert score > 30

    def test_text_without_authority(self):
        text = "今天天气很好，我们出去走走吧。"
        score = compute_authority_citation(text)
        assert score == 0.0


class TestStructuredData:
    def test_empty_text(self):
        assert compute_structured_data("") == 0.0

    def test_with_qa_and_table(self):
        text = (
            "Q：分手后多久可以联系前任？\n"
            "A：建议至少等待 30 天。\n\n"
            "Q：如何判断对方是否还有感情？\n"
            "A：观察这 3 个信号。\n\n"
            "Q：挽回的最佳时机是什么？\n"
            "A：在冷静期结束后。\n\n"
            "| 阶段 | 时间 | 行动 |\n"
            "|------|------|------|\n"
            "| 冷静期 | 1-4周 | 自我提升 |\n"
            "| 破冰期 | 5-8周 | 轻度联系 |\n"
        )
        score = compute_structured_data(text)
        assert score >= 60

    def test_with_list_items(self):
        text = (
            "1. 第一步：停止纠缠\n"
            "2. 第二步：自我反思\n"
            "3. 第三步：提升自我\n"
            "4. 第四步：重建联系\n"
            "5. 第五步：创造新记忆\n"
        )
        score = compute_structured_data(text)
        assert score > 40


class TestKeywordCoverage:
    def test_empty_text(self):
        assert compute_keyword_coverage("") == 0.0

    def test_with_keywords(self):
        keywords = ["分手挽回", "婚姻修复", "情感咨询"]
        text = "分手挽回是一个需要耐心的过程，专业的情感咨询可以帮助你。"
        score = compute_keyword_coverage(text, keywords)
        # 2 out of 3 keywords found → ~66.7
        assert 60 <= score <= 70

    def test_without_keywords(self):
        text = "**重点1**\n\n**重点2**\n\n# 标题一\n\n# 标题二"
        score = compute_keyword_coverage(text)
        assert score > 0  # heuristic should pick up bold/headers


class TestCredibilitySignals:
    def test_empty_text(self):
        assert compute_credibility_signals("") == 0.0

    def test_with_data_and_cases(self):
        text = (
            "在我们 1200 例案例中，78.5% 的夫妻在 6 个月内关系改善。\n"
            "数据来源：内部咨询记录统计\n"
            "其中循证实践组的效果优于对照组（P < 0.05）。"
        )
        score = compute_credibility_signals(text)
        assert score > 30


class TestPlatformFitness:
    def test_empty_text(self):
        assert compute_platform_fitness("") == 0.0

    def test_xiaohongshu_good_fit(self):
        # ~400 words (Chinese chars), has emojis, short paragraphs
        text = (
            "姐妹们！分手后千万别做这3件事😭\n\n"
            "1️⃣ 不要反复纠缠对方\n\n"
            "2️⃣ 不要在朋友圈发伤感内容\n\n"
            "3️⃣ 不要通过共同好友打听\n\n"
            "正确的做法是：\n"
            "✅ 给自己一个冷静期\n"
            "✅ 提升自己的价值\n"
            "✅ 用二次吸引的方法\n\n"
            "关注我，教你科学挽回💪"
        )
        score = compute_platform_fitness(text, "xiaohongshu")
        assert score >= 50

    def test_generic_without_platform(self):
        text = (
            "# 标题\n\n"
            "第一段内容。\n\n"
            "第二段内容。\n\n"
            "第三段内容。"
        )
        score = compute_platform_fitness(text)
        assert score > 40


class TestFreshness:
    def test_empty_text(self):
        assert compute_freshness("") == 0.0

    def test_text_with_recent_dates(self):
        text = "2025年最新研究表明，截至2025第三季度，行业增长率创新高。"
        score = compute_freshness(text)
        assert score >= 80

    def test_text_without_dates(self):
        text = "情感修复需要时间和耐心。"
        score = compute_freshness(text)
        assert score == 40.0  # baseline only


# ---------------------------------------------------------------------------
# Overall GEO score
# ---------------------------------------------------------------------------


class TestComputeGEOScore:
    def test_empty_text(self):
        card = compute_geo_score("")
        assert card.overall == 0.0

    def test_returns_score_card(self):
        text = (
            "# 2025年婚姻修复完整指南\n\n"
            "根据中国婚姻家庭研究会的最新数据，2025年婚姻咨询需求增长 35%。\n\n"
            "## 第一步：理解问题根源\n\n"
            "心理学专家指出，80% 的婚姻问题源于沟通不畅。\n\n"
            "Q：什么时候需要寻求专业帮助？\n"
            "A：当双方无法独立解决冲突超过 3 个月时。\n\n"
            "## 第二步：建立有效沟通\n\n"
            "1. 练习非暴力沟通（NVC）\n"
            "2. 每周安排至少 2 小时的深度对话\n"
            "3. 避免使用指责性语言\n\n"
            "来源：北京大学心理学研究院 2024 年度报告"
        )
        card = compute_geo_score(text)
        assert isinstance(card, GEOScoreCard)
        assert card.overall > 0
        assert card.authority_citation > 0
        assert card.structured_data > 0
        assert card.freshness > 0

    def test_with_keywords_and_platform(self):
        text = "婚姻修复是一个需要专业情感咨询的过程。2025年最新研究表明，依恋理论在夫妻治疗中效果显著。"
        keywords = ["婚姻修复", "情感咨询", "依恋理论"]
        card = compute_geo_score(text, keywords=keywords, platform="wechat")
        assert card.keyword_coverage > 0
        assert card.platform_fitness > 0

    def test_to_dict_has_new_fields(self):
        card = compute_geo_score("测试文本")
        d = card.to_dict()
        assert "authority_citation" in d
        assert "structured_data" in d
        assert "keyword_coverage" in d
        assert "credibility_signals" in d
        assert "platform_fitness" in d
        assert "freshness" in d
        assert "scoring_model" in d["details"]

    def test_overall_is_weighted_sum(self):
        text = "简单测试内容。"
        card = compute_geo_score(text)
        expected = (
            card.authority_citation * 0.20
            + card.structured_data * 0.15
            + card.keyword_coverage * 0.20
            + card.credibility_signals * 0.15
            + card.platform_fitness * 0.15
            + card.freshness * 0.15
        )
        assert abs(card.overall - expected) < 0.1


class TestSuggestOptimizationStrategies:
    def test_returns_weak_dimensions_strategies_in_order(self):
        card = GEOScoreCard(
            authority_citation=20,
            structured_data=35,
            keyword_coverage=90,
            credibility_signals=30,
            platform_fitness=80,
            freshness=75,
        )
        strategies = suggest_optimization_strategies(card, threshold=65)
        assert strategies == [
            "citation_enhancement",
            "statistics_addition",
            "qa_structuring",
        ]

    def test_deduplicates_preserving_order(self):
        card = GEOScoreCard(
            authority_citation=20,
            structured_data=90,
            keyword_coverage=95,
            credibility_signals=10,
            platform_fitness=90,
            freshness=90,
        )
        strategies = suggest_optimization_strategies(card, threshold=80)
        assert strategies == ["statistics_addition", "citation_enhancement"]

    def test_respects_threshold(self):
        card = GEOScoreCard(
            authority_citation=70,
            structured_data=72,
            keyword_coverage=71,
            credibility_signals=73,
            platform_fitness=74,
            freshness=75,
        )
        strategies = suggest_optimization_strategies(card, threshold=65)
        assert strategies == []
