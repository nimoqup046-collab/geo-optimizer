"""Tests for pluggable industry configuration system."""

import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from services.industry_config import (
    SUPPORTED_INDUSTRIES,
    get_industry_config,
    get_industry_keywords,
    get_industry_platform_hints,
    list_industries,
)


class TestIndustryConfig:
    def test_emotional_counseling_exists(self):
        cfg = get_industry_config("emotional_counseling")
        assert cfg is not None
        assert cfg["display_name"] == "情感咨询/婚姻修复"

    def test_unknown_industry_returns_none(self):
        cfg = get_industry_config("nonexistent")
        assert cfg is None

    def test_all_industries_have_required_fields(self):
        for industry_id in SUPPORTED_INDUSTRIES:
            cfg = get_industry_config(industry_id)
            assert cfg is not None
            assert "id" in cfg
            assert "display_name" in cfg
            assert "description" in cfg
            assert "seed_keywords" in cfg
            assert "banned_words" in cfg
            assert "default_tone" in cfg
            assert "platform_hints" in cfg

    def test_seed_keywords_are_non_empty(self):
        for industry_id in SUPPORTED_INDUSTRIES:
            keywords = get_industry_keywords(industry_id)
            assert len(keywords) >= 5

    def test_unknown_industry_keywords_empty(self):
        keywords = get_industry_keywords("nonexistent")
        assert keywords == []


class TestListIndustries:
    def test_returns_list(self):
        industries = list_industries()
        assert isinstance(industries, list)
        assert len(industries) >= 3  # emotional_counseling, education, ecommerce

    def test_each_item_has_id_and_name(self):
        for item in list_industries():
            assert "id" in item
            assert "display_name" in item
            assert "description" in item


class TestPlatformHints:
    def test_emotional_counseling_xiaohongshu_hints(self):
        hints = get_industry_platform_hints("emotional_counseling", "xiaohongshu")
        assert hints is not None
        assert "opening_style" in hints
        assert "cta" in hints
        assert "tags" in hints

    def test_unknown_industry_returns_none(self):
        hints = get_industry_platform_hints("nonexistent", "wechat")
        assert hints is None

    def test_unknown_platform_returns_none(self):
        hints = get_industry_platform_hints("emotional_counseling", "tiktok")
        assert hints is None
