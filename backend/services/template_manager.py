"""Platform-specific content templates and generation rules.

Each platform has two levels of configuration:

* **PLATFORM_RULES** -- concise rules injected into LLM prompts.
* **PLATFORM_STYLES** -- rich metadata used by the GEO scorer, UI, and
  quality checks (tone, length range, emoji density, structure template,
  example opening).
"""

from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Concise rules for prompt injection (backward-compatible)
# ---------------------------------------------------------------------------

PLATFORM_RULES: Dict[str, Dict[str, str]] = {
    "xiaohongshu": {
        "name": "小红书图文笔记",
        "length": "300-800 字",
        "style": "亲切具体，短段落，给明确步骤与避坑提示",
    },
    "wechat": {
        "name": "公众号文章",
        "length": "1200-2200 字",
        "style": "专业务实，结构完整，结论可引用",
    },
    "zhihu": {
        "name": "知乎回答/文章",
        "length": "800-1500 字",
        "style": "先结论后论证，再给可执行清单",
    },
    "video": {
        "name": "短视频脚本",
        "length": "60-90 秒口播时长",
        "style": "开头钩子 + 主体三点 + 结尾 CTA，带镜头提示",
    },
    "baijiahao": {
        "name": "百家号文章",
        "length": "1000-2000 字",
        "style": "信息量大、标题吸引、段落清晰、适合搜索分发",
    },
}


# ---------------------------------------------------------------------------
# Rich platform style metadata (used by GEO scorer & UI)
# ---------------------------------------------------------------------------

PLATFORM_STYLES: Dict[str, Dict[str, Any]] = {
    "wechat": {
        "tone": "深度专业、有温度感",
        "min_words": 1200,
        "max_words": 2200,
        "structure": "标题→引言→正文(3-5段)→总结→引导关注",
        "emoji_density": "low",
        "example_opening": (
            "情感咨询领域：以案例故事开篇→心理学原理分析→实操建议"
        ),
    },
    "xiaohongshu": {
        "tone": "闺蜜聊天、真实分享感",
        "min_words": 300,
        "max_words": 800,
        "structure": "封面标题→痛点共鸣→干货分享→互动引导",
        "emoji_density": "high",
        "example_opening": "姐妹们！分手后千万别做这3件事😭...",
    },
    "zhihu": {
        "tone": "理性客观、数据支撑",
        "min_words": 800,
        "max_words": 1500,
        "structure": "观点→论据→案例→引用→总结",
        "emoji_density": "none",
        "example_opening": (
            "从依恋理论视角分析，婚姻修复的核心在于..."
        ),
    },
    "video": {
        "tone": "口语化、节奏感强",
        "min_words": 100,
        "max_words": 500,
        "structure": "Hook(3秒)→痛点→解决方案→CTA",
        "emoji_density": "low",
        "format": "分镜表：画面|台词|字幕|BGM",
        "example_opening": "你知道吗？90%的人分手后都会犯这个错...",
    },
    "baijiahao": {
        "tone": "客观权威、信息密集",
        "min_words": 1000,
        "max_words": 2000,
        "structure": "新闻标题→导语→正文→总结→延伸阅读",
        "emoji_density": "none",
        "example_opening": (
            "近年来情感咨询行业快速发展，据行业数据显示..."
        ),
    },
}

SUPPORTED_PLATFORMS = list(PLATFORM_STYLES.keys())


def get_platform_rule(platform: str) -> Dict[str, str]:
    return PLATFORM_RULES.get(platform, PLATFORM_RULES["wechat"])


def get_platform_style(platform: str) -> Dict[str, Any]:
    """Return the rich style metadata for *platform*."""
    return PLATFORM_STYLES.get(platform, PLATFORM_STYLES["wechat"])


def format_generation_prompt(
    platform: str,
    topic: str,
    brand_name: str,
    tone_of_voice: str,
    call_to_action: str,
    banned_words: str,
    industry: Optional[str] = None,
) -> str:
    rule = get_platform_rule(platform)
    style = get_platform_style(platform)

    industry_hint = ""
    if industry:
        # Lazy import to avoid circular dependency.
        from services.industry_config import get_industry_config

        cfg = get_industry_config(industry)
        if cfg:
            industry_hint = (
                f"行业：{cfg['display_name']}\n"
                f"行业调性：{cfg['default_tone']}\n"
                f"行业禁用项：{'、'.join(cfg['banned_words'][:5])}\n"
            )

    return (
        f"请围绕主题“{topic}”生成一篇{rule['name']}。\n"
        f"目标长度：{rule['length']}\n"
        f"风格要求：{rule['style']}\n"
        f"语气调性：{style['tone']}\n"
        f"内容结构：{style['structure']}\n"
        f"品牌：{brand_name}\n"
        f"语气：{tone_of_voice or '专业、温和、可执行'}\n"
        f"CTA：{call_to_action or '引导用户提交具体场景进行咨询'}\n"
        f"禁用项：{banned_words or '夸大承诺、道德审判、绝对化表述'}\n"
        f"{industry_hint}\n"
        "输出格式：\n"
        "# 标题\n"
        "正文内容...\n"
    )
