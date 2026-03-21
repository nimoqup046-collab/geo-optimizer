"""Tests for platform template configuration."""

import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from services.template_manager import (
    PLATFORM_RULES,
    PLATFORM_STYLES,
    SUPPORTED_PLATFORMS,
    format_generation_prompt,
    get_platform_rule,
    get_platform_style,
)


class TestPlatformRules:
    def test_all_platforms_have_rules(self):
        for platform in SUPPORTED_PLATFORMS:
            rule = get_platform_rule(platform)
            assert "name" in rule
            assert "length" in rule
            assert "style" in rule

    def test_unknown_platform_falls_back_to_wechat(self):
        rule = get_platform_rule("unknown_platform")
        assert rule == PLATFORM_RULES["wechat"]

    def test_baijiahao_platform_exists(self):
        rule = get_platform_rule("baijiahao")
        assert "百家号" in rule["name"]


class TestPlatformStyles:
    def test_all_platforms_have_styles(self):
        for platform in SUPPORTED_PLATFORMS:
            style = get_platform_style(platform)
            assert "tone" in style
            assert "min_words" in style
            assert "max_words" in style
            assert "structure" in style
            assert "emoji_density" in style

    def test_xiaohongshu_high_emoji(self):
        style = get_platform_style("xiaohongshu")
        assert style["emoji_density"] == "high"

    def test_zhihu_no_emoji(self):
        style = get_platform_style("zhihu")
        assert style["emoji_density"] == "none"

    def test_word_count_ranges_are_valid(self):
        for platform in SUPPORTED_PLATFORMS:
            style = get_platform_style(platform)
            assert style["min_words"] < style["max_words"]
            assert style["min_words"] > 0

    def test_unknown_platform_falls_back(self):
        style = get_platform_style("nonexistent")
        assert style == PLATFORM_STYLES["wechat"]


class TestFormatGenerationPrompt:
    def test_basic_prompt_generation(self):
        prompt = format_generation_prompt(
            platform="wechat",
            topic="婚姻修复",
            brand_name="测试品牌",
            tone_of_voice="专业温暖",
            call_to_action="联系我们",
            banned_words="保证效果",
        )
        assert "婚姻修复" in prompt
        assert "测试品牌" in prompt
        assert "公众号文章" in prompt
        assert "语气调性" in prompt
        assert "内容结构" in prompt

    def test_prompt_with_industry(self):
        prompt = format_generation_prompt(
            platform="xiaohongshu",
            topic="分手挽回",
            brand_name="情感咨询",
            tone_of_voice="",
            call_to_action="",
            banned_words="",
            industry="emotional_counseling",
        )
        assert "分手挽回" in prompt
        assert "行业" in prompt

    def test_prompt_with_unknown_industry(self):
        # Should not crash with unknown industry.
        prompt = format_generation_prompt(
            platform="zhihu",
            topic="测试",
            brand_name="品牌",
            tone_of_voice="",
            call_to_action="",
            banned_words="",
            industry="nonexistent_industry",
        )
        assert "测试" in prompt

    def test_prompt_includes_structure(self):
        prompt = format_generation_prompt(
            platform="xiaohongshu",
            topic="test",
            brand_name="brand",
            tone_of_voice="",
            call_to_action="",
            banned_words="",
        )
        assert "封面标题" in prompt  # xiaohongshu structure
