from typing import Dict


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
}


def get_platform_rule(platform: str) -> Dict[str, str]:
    return PLATFORM_RULES.get(platform, PLATFORM_RULES["wechat"])


def format_generation_prompt(
    platform: str,
    topic: str,
    brand_name: str,
    tone_of_voice: str,
    call_to_action: str,
    banned_words: str,
) -> str:
    rule = get_platform_rule(platform)
    return (
        f"请围绕主题“{topic}”生成一篇{rule['name']}。\n"
        f"目标长度：{rule['length']}\n"
        f"风格要求：{rule['style']}\n"
        f"品牌：{brand_name}\n"
        f"语气：{tone_of_voice or '专业、温和、可执行'}\n"
        f"CTA：{call_to_action or '引导用户提交具体场景进行咨询'}\n"
        f"禁用项：{banned_words or '夸大承诺、道德审判、绝对化表述'}\n\n"
        "输出格式：\n"
        "# 标题\n"
        "正文内容...\n"
    )
