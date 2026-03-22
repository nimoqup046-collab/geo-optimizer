from typing import Dict, Any
"""Platform-specific content templates and generation rules.

Each platform has two levels of configuration:

* **PLATFORM_RULES** -- concise rules injected into LLM prompts.
* **PLATFORM_STYLES** -- rich metadata used by the GEO scorer, UI, and
  quality checks (tone, length range, emoji density, structure template,
  example opening).
"""



# ---------------------------------------------------------------------------
# Concise rules for prompt injection (backward-compatible)
# ---------------------------------------------------------------------------

PLATFORM_RULES: Dict[str, Dict[str, Any]] = {
    "xiaohongshu": {
        "name": "小红书图文笔记",
        "length": "300-800 字",
        "min_chars": 300,
        "max_chars": 800,
        "style": "亲切具体，短段落，给明确步骤与避坑提示",
        "tone": "闺蜜式口语化，真诚分享，带个人体验感",
        "title_rules": {
            "method": "二极管标题法",
            "description": "使用正极性或负极性标题引发好奇与情绪共鸣",
            "positive_templates": [
                "天哪❗{topic}居然可以这样做，效果绝了",
                "后悔没早知道！{topic}的正确打开方式",
                "姐妹们冲！{topic}我终于找到最优解了",
            ],
            "negative_templates": [
                "求求了别再{wrong_approach}了！{topic}的避坑指南",
                "踩了3年的坑！{topic}千万别这样做",
                "{topic}翻车实录：这些错误90%的人都在犯",
            ],
            "rules": [
                "标题必须带emoji（1-3个）",
                "标题长度15-25字",
                "用问号或感叹号结尾",
                "包含数字更易吸引点击",
            ],
        },
        "structure_template": (
            "开头hook（1-2句抓眼球）\n"
            "痛点共鸣（你是不是也...）\n"
            "干货步骤（3-5步，每步配emoji）\n"
            "避坑提示（别踩这些雷）\n"
            "结尾互动（评论区告诉我...）"
        ),
        "forbidden_patterns": [
            "专业术语堆砌",
            "长段落（超过100字不分段）",
            "官方口吻",
            "没有emoji的纯文字",
        ],
        "emoji_density": "每100字2-4个emoji",
        "hashtag_rules": "3-6个话题标签，混合热门+精准长尾标签",
    },
    "wechat": {
        "name": "公众号文章",
        "length": "1200-2200 字",
        "min_chars": 1200,
        "max_chars": 2200,
        "style": "专业务实，结构完整，结论可引用",
        "tone": "专业权威但不冷漠，有温度的专家视角",
        "title_rules": {
            "method": "价值前置标题法",
            "description": "标题直接传递核心价值或信息增量",
            "templates": [
                "{topic}：{core_insight}（附{deliverable}）",
                "深度解析：{topic}的{number}个关键策略",
                "{audience}必看：{topic}完全指南（{year}版）",
            ],
            "rules": [
                "标题长度20-35字",
                "包含明确价值承诺",
                "避免标题党和夸大",
                "可加括号补充说明（附模板/含案例等）",
            ],
        },
        "structure_template": (
            "导语（核心结论前置，50字内给出可引用断言）\n"
            "## 背景/问题（为什么重要）\n"
            "## 核心分析（2-3个子标题，每段200-400字）\n"
            "  - 每个论点配数据或案例支撑\n"
            "  - 嵌入1-2个用户高频问题\n"
            "## 行动指南（具体可执行步骤）\n"
            "## 结论 + CTA（引导下一步行动）"
        ),
        "forbidden_patterns": [
            "无数据支撑的空泛结论",
            "口语化表达",
            "过多emoji",
            "段落超过400字不分段",
        ],
        "cta_rules": "文末引导关注/收藏/转发，或引导进入私域（添加微信/加群）",
    },
    "zhihu": {
        "name": "知乎回答/文章",
        "length": "800-1500 字",
        "min_chars": 800,
        "max_chars": 1500,
        "style": "先结论后论证，再给可执行清单",
        "tone": "理性专业，逻辑严密，数据驱动",
        "title_rules": {
            "method": "问题回答式",
            "description": "标题即为用户搜索问题，内容为权威回答",
            "templates": [
                "如何{action}？从{perspective}角度给出{number}个建议",
                "{topic}到底怎么做？这是我{experience}后的总结",
                "为什么{phenomenon}？{number}个关键因素解析",
            ],
            "rules": [
                "标题建议以问句形式呈现",
                "包含核心关键词",
                "避免情绪化表达",
            ],
        },
        "structure_template": (
            "**结论先行**（开头直接给出核心观点/答案）\n"
            "### 论据展开\n"
            "  - 论点1 + 数据/引用支撑\n"
            "  - 论点2 + 案例佐证\n"
            "  - 论点3 + 对比分析\n"
            "### 可执行清单（3-5条具体建议）\n"
            "### 延伸阅读/思考（可选）"
        ),
        "forbidden_patterns": [
            "无逻辑跳跃",
            "情绪化宣泄",
            "没有引用来源的数据",
            "过于口语化",
        ],
        "citation_rules": "每300字至少1个数据引用或权威来源",
    },
    "video": {
        "name": "短视频脚本",
        "length": "60-90 秒口播时长",
        "min_seconds": 60,
        "max_seconds": 90,
        "style": "开头钩子 + 主体三点 + 结尾 CTA，带镜头提示",
        "tone": "自然口语化，节奏紧凑，信息密度高",
        "title_rules": {
            "method": "悬念钩子法",
            "description": "前3秒必须抓住注意力",
            "hook_templates": [
                "你知道{topic}最大的误区是什么吗？",
                "{number}秒告诉你{topic}的核心秘密",
                "所有人都在做{wrong_thing}，但正确答案是...",
            ],
            "rules": [
                "标题/开场白必须3秒内制造悬念",
                "包含具体数字",
                "引发好奇心或痛点共鸣",
            ],
        },
        "structure_template": (
            "【0-5秒】Hook钩子：一句话制造悬念/痛点\n"
            "【5-15秒】Pain痛点放大：描述目标受众的困境\n"
            "【15-50秒】Solution解决方案：\n"
            "  - 要点1（15-25秒）\n"
            "  - 要点2（25-35秒）\n"
            "  - 要点3（35-50秒）\n"
            "【50-60秒】CTA行动号召：关注/评论/私信\n"
            "【镜头提示】每段标注景别和动作"
        ),
        "forbidden_patterns": [
            "长句子（超过20字的单句）",
            "书面语表达",
            "没有节奏变化的平铺直叙",
            "超过90秒的脚本",
        ],
        "pacing_rules": "每10秒一个信息点，总计6-9个信息点",
    },
}

# Industry-specific overlays that can be merged with platform rules.
INDUSTRY_OVERLAYS: Dict[str, Dict[str, Any]] = {
    "emotion_consulting": {
        "tone_modifier": "温暖共情，避免说教，多用「我理解」「这很正常」",
        "banned_topics": ["道德审判", "绝对化承诺", "保证结果"],
        "recommended_hooks": ["情感痛点", "真实案例", "常见误区"],
    },
    "tech": {
        "tone_modifier": "专业严谨，注重数据和技术细节",
        "banned_topics": ["缺乏依据的对比", "过度承诺性能"],
        "recommended_hooks": ["技术趋势", "性能对比", "解决方案"],
    },
    "education": {
        "tone_modifier": "耐心引导，循序渐进，重视学习路径",
        "banned_topics": ["贩卖焦虑", "保过承诺"],
        "recommended_hooks": ["学习痛点", "方法论", "成功案例"],
    },
    "health": {
        "tone_modifier": "科学严谨，引用权威来源，不做医疗建议",
        "banned_topics": ["替代医学宣传", "保证疗效", "未经验证的偏方"],
        "recommended_hooks": ["健康误区", "研究发现", "专家建议"],
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


def get_platform_rule(platform: str) -> Dict[str, Any]:
    return PLATFORM_RULES.get(platform, PLATFORM_RULES["wechat"])


def get_platform_title_guidance(platform: str, topic: str) -> str:
    """Generate title writing guidance for a specific platform."""
    rule = get_platform_rule(platform)
    title_rules = rule.get("title_rules", {})
    if not title_rules:
        return ""

    method = title_rules.get("method", "")
    description = title_rules.get("description", "")
    rules = title_rules.get("rules", [])

    guidance = f"标题方法：{method}\n说明：{description}\n"
    if rules:
        guidance += "标题规则：\n"
        for r in rules:
            guidance += f"  - {r}\n"

    # Show example templates with topic substitution.
    templates = title_rules.get("templates") or title_rules.get(
        "positive_templates"
    ) or title_rules.get("hook_templates", [])
    if templates:
        guidance += "标题示例：\n"
        fmt_kwargs = dict(
            topic=topic, core_insight='核心洞察', number=3, deliverable='模板',
            audience='从业者', year='2026', action='做好', perspective='实战',
            experience='深入研究', phenomenon='这种情况', wrong_approach='这样做', wrong_thing='这件事',
        )
        for t in templates[:2]:
            guidance += f"  - {t.format(**fmt_kwargs)}\n"

    return guidance


def get_industry_overlay(industry: str) -> Dict[str, Any]:
    """Get industry-specific content modifiers."""
    return INDUSTRY_OVERLAYS.get(industry, {})
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
    industry: str = "",
) -> str:
    rule = get_platform_rule(platform)
    title_guidance = get_platform_title_guidance(platform, topic)
    structure = rule.get("structure_template", "")
    forbidden = rule.get("forbidden_patterns", [])
    tone = rule.get("tone", rule.get("style", ""))

    prompt = (
        f"请围绕主题「{topic}」生成一篇{rule['name']}。\n"
        f"目标长度：{rule['length']}\n"
        f"风格要求：{rule['style']}\n"
        f"语气风格：{tone}\n"
        f"品牌：{brand_name}\n"
        f"语气：{tone_of_voice or '专业、温和、可执行'}\n"
        f"CTA：{call_to_action or '引导用户提交具体场景进行咨询'}\n"
        f"禁用项：{banned_words or '夸大承诺、道德审判、绝对化表述'}\n\n"
    )

    if title_guidance:
        prompt += f"## 标题撰写指南\n{title_guidance}\n"

    if structure:
        prompt += f"## 内容结构模板\n{structure}\n\n"

    if forbidden:
        prompt += "## 禁止事项\n"
        for f in forbidden:
            prompt += f"- {f}\n"
        prompt += "\n"

    # Add industry overlay if available.
    if industry:
        overlay = get_industry_overlay(industry)
        if overlay:
            modifier = overlay.get("tone_modifier", "")
            if modifier:
                prompt += f"## 行业特殊要求\n语气调整：{modifier}\n"
            banned = overlay.get("banned_topics", [])
            if banned:
                prompt += f"额外禁忌：{', '.join(banned)}\n"
            hooks = overlay.get("recommended_hooks", [])
            if hooks:
                prompt += f"推荐切入角度：{', '.join(hooks)}\n"
            prompt += "\n"

    return prompt
