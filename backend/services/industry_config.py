"""Pluggable industry configuration system.

Each industry pack bundles:

* **seed_keywords** -- starter keyword list for GEO analysis.
* **banned_words** -- terms to avoid in generated content.
* **default_tone** -- recommended content tone.
* **platform_hints** -- per-platform opening / CTA suggestions.
* **display_name** -- human-readable label.

Architecture note
-----------------
Industry packs are plain dictionaries today but are designed to be
loaded from a database or YAML file in a future iteration so that
operators can add new industries without code changes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Built-in industry packs
# ---------------------------------------------------------------------------

INDUSTRY_CONFIGS: Dict[str, Dict[str, Any]] = {
    "emotional_counseling": {
        "id": "emotional_counseling",
        "display_name": "情感咨询/婚姻修复",
        "description": "覆盖分手挽回、婚姻修复、情感挽回、恋爱咨询等细分领域",
        "seed_keywords": [
            "分手挽回",
            "婚姻修复",
            "情感咨询",
            "挽回前任",
            "夫妻关系修复",
            "冷暴力",
            "出轨修复",
            "依恋理论",
            "情感疏导",
            "恋爱咨询",
            "二次吸引",
            "断联挽回",
            "情绪管理",
            "亲密关系",
            "沟通技巧",
        ],
        "banned_words": [
            "保证挽回",
            "100%成功",
            "包复合",
            "小三",
            "PUA",
            "道德审判",
            "绝对化表述",
            "夸大承诺",
            "心理操控",
            "情感绑架",
        ],
        "default_tone": "专业温暖、共情但不迎合、有数据支撑、引导行动",
        "platform_hints": {
            "xiaohongshu": {
                "opening_style": "姐妹们！我花了3个月终于挽回了他...",
                "cta": "评论区留下你的情况，我帮你分析",
                "tags": ["情感挽回", "分手挽回", "婚姻修复", "恋爱心理"],
            },
            "wechat": {
                "opening_style": "在过去一年的咨询案例中，我们发现一个普遍规律...",
                "cta": "点击阅读原文，获取免费情感评估",
                "tags": ["情感咨询", "心理学", "婚姻"],
            },
            "zhihu": {
                "opening_style": "从依恋理论和情绪聚焦疗法（EFT）视角来看...",
                "cta": "如果你正在经历类似困境，欢迎私信咨询",
                "tags": ["心理学", "情感", "亲密关系", "婚姻"],
            },
            "video": {
                "opening_style": "分手后最容易犯的3个错误，第2个90%的人都在做...",
                "cta": "关注我，每天一个情感干货",
                "tags": ["情感", "挽回", "恋爱"],
            },
            "baijiahao": {
                "opening_style": "据中国婚姻家庭研究会最新数据显示...",
                "cta": "了解更多专业情感咨询服务",
                "tags": ["情感", "婚姻", "心理健康"],
            },
        },
    },
    "education": {
        "id": "education",
        "display_name": "教育培训",
        "description": "覆盖K12教育、职业培训、考试辅导、留学咨询等领域",
        "seed_keywords": [
            "高考备考",
            "考研辅导",
            "英语培训",
            "在线教育",
            "职业技能",
            "留学咨询",
            "学习方法",
            "课外辅导",
            "素质教育",
            "编程教育",
        ],
        "banned_words": [
            "保过",
            "包过",
            "100%提分",
            "高考移民",
            "代写",
            "替考",
            "抄袭",
            "泄题",
        ],
        "default_tone": "专业权威、循循善诱、数据驱动、注重实效",
        "platform_hints": {
            "xiaohongshu": {
                "opening_style": "学霸都在用的3个学习法，最后一个绝了！",
                "cta": "收藏起来慢慢看，评论区告诉我你的成绩目标",
                "tags": ["学习方法", "备考", "提分", "教育"],
            },
            "wechat": {
                "opening_style": "教育部最新政策解读及家长应对策略...",
                "cta": "回复关键词获取完整学习资料包",
                "tags": ["教育", "升学", "学习"],
            },
            "zhihu": {
                "opening_style": "结合认知科学的最新研究成果来看...",
                "cta": "欢迎关注，持续分享教育干货",
                "tags": ["教育", "学习方法", "认知科学"],
            },
        },
    },
    "ecommerce": {
        "id": "ecommerce",
        "display_name": "电商零售",
        "description": "覆盖电商运营、品牌推广、直播带货、私域流量等领域",
        "seed_keywords": [
            "电商运营",
            "直播带货",
            "私域流量",
            "品牌推广",
            "用户增长",
            "转化率优化",
            "内容电商",
            "社交电商",
            "供应链管理",
            "选品策略",
        ],
        "banned_words": [
            "刷单",
            "假货",
            "山寨",
            "仿品",
            "虚假宣传",
            "绝对化用语",
        ],
        "default_tone": "专业实用、案例驱动、数据说话、注重ROI",
        "platform_hints": {
            "xiaohongshu": {
                "opening_style": "小店月销百万的秘密，老板娘自述...",
                "cta": "想了解更多运营技巧？关注我",
                "tags": ["电商运营", "私域", "直播带货"],
            },
            "wechat": {
                "opening_style": "2024年电商行业趋势报告深度解析...",
                "cta": "扫码加入电商运营交流群",
                "tags": ["电商", "运营", "增长"],
            },
        },
    },
}

SUPPORTED_INDUSTRIES = list(INDUSTRY_CONFIGS.keys())


def get_industry_config(industry_id: str) -> Optional[Dict[str, Any]]:
    """Return the configuration pack for the given industry, or ``None``."""
    return INDUSTRY_CONFIGS.get(industry_id)


def list_industries() -> List[Dict[str, str]]:
    """Return a summary list of all available industry packs."""
    return [
        {
            "id": cfg["id"],
            "display_name": cfg["display_name"],
            "description": cfg["description"],
        }
        for cfg in INDUSTRY_CONFIGS.values()
    ]


def get_industry_keywords(industry_id: str) -> List[str]:
    """Return seed keywords for the given industry."""
    cfg = get_industry_config(industry_id)
    if cfg is None:
        return []
    return list(cfg["seed_keywords"])


def get_industry_platform_hints(
    industry_id: str, platform: str
) -> Optional[Dict[str, Any]]:
    """Return platform-specific hints for the given industry + platform."""
    cfg = get_industry_config(industry_id)
    if cfg is None:
        return None
    return cfg.get("platform_hints", {}).get(platform)
