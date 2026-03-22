"""WeChat Rich Post generation service.

Generates a complete WeChat Official Account article package:
- Title (following wechat title rules from template_manager)
- Body text (1200-2200 chars, structured for authority + readability)
- Image directives (descriptions for cover + in-article images)
- HTML and Markdown export artifacts
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.llm_service import generate_content
from services.template_manager import (
    format_generation_prompt,
)

logger = logging.getLogger(__name__)

WECHAT_ARTICLE_SYSTEM_PROMPT = """\
你是一位资深公众号内容创作专家，擅长写深度专业、有温度感的公众号图文。
你的输出必须严格按照 JSON 格式返回，包含以下字段：

{
  "title": "文章标题（20-35字，价值前置）",
  "summary": "导语摘要（50字内，核心结论前置，可被AI引用）",
  "sections": [
    {
      "heading": "小标题",
      "body": "段落正文（200-400字）",
      "image_directive": "配图描述指令（描述这一段需要什么样的配图，风格、内容、情绪）"
    }
  ],
  "cover_image_directive": "封面配图指令（描述封面图的风格、主题元素、色调）",
  "tags": ["标签1", "标签2", "标签3"],
  "cta": "文末行动号召语"
}

写作要求：
- 标题遵循「价值前置标题法」，直接传递核心价值
- 导语50字内，核心结论前置，可被AI引用为权威断言
- 正文分3-5个小节，每节200-400字，配数据或案例
- 每个小节提供配图描述指令，说明需要什么样的配图
- 封面图指令要具体：描述主题元素、色调、风格
- 文末引导关注/收藏/转发或引导进入私域
- 全文1200-2200字
- 专业权威但有温度，避免口语化和过多emoji
- 确保输出是合法JSON，不要包含```json标记
"""


@dataclass
class ImageDirective:
    """Description of an image to be created or selected."""
    position: str  # "cover" | "section_1" | "section_2" etc.
    description: str
    style_hint: str = ""


@dataclass
class WechatArticle:
    """Complete WeChat article package."""
    title: str
    summary: str
    sections: List[Dict[str, str]]  # [{heading, body, image_directive}]
    cover_image_directive: str
    tags: List[str]
    cta: str
    image_directives: List[ImageDirective] = field(default_factory=list)
    generated_at: str = ""
    raw_body: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()
        self._build_image_directives()
        self._build_raw_body()

    def _build_image_directives(self):
        self.image_directives = [
            ImageDirective(position="cover", description=self.cover_image_directive)
        ]
        for i, section in enumerate(self.sections):
            directive = section.get("image_directive", "")
            if directive:
                self.image_directives.append(
                    ImageDirective(position=f"section_{i + 1}", description=directive)
                )

    def _build_raw_body(self):
        parts = [self.summary, ""]
        for section in self.sections:
            heading = section.get("heading", "")
            body = section.get("body", "")
            if heading:
                parts.append(f"## {heading}")
            parts.append(body)
            parts.append("")
        if self.cta:
            parts.append(f"---\n{self.cta}")
        self.raw_body = "\n".join(parts)

    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            "",
            f"> {self.summary}",
            "",
        ]
        for i, section in enumerate(self.sections):
            lines.append(f"## {section.get('heading', '')}")
            lines.append("")
            lines.append(section.get("body", ""))
            directive = section.get("image_directive", "")
            if directive:
                lines.append(f"\n<!-- 配图指令: {directive} -->")
            lines.append("")
        if self.cta:
            lines.append("---")
            lines.append("")
            lines.append(f"**{self.cta}**")
            lines.append("")
        if self.tags:
            lines.append(f"标签：{'、'.join(self.tags)}")
        return "\n".join(lines)

    def to_html(self) -> str:
        sections_html = []
        for i, section in enumerate(self.sections):
            heading = section.get("heading", "")
            body = section.get("body", "").replace("\n", "<br>")
            directive = section.get("image_directive", "")
            img_placeholder = ""
            if directive:
                img_placeholder = (
                    f'<div class="img-placeholder" '
                    f'data-directive="{directive}" '
                    f'style="background:#f5f5f5;padding:20px;margin:16px 0;'
                    f'text-align:center;color:#999;border-radius:8px;">'
                    f"[配图位: {directive}]</div>"
                )
            sections_html.append(
                f"<h2>{heading}</h2>"
                f"{img_placeholder}"
                f"<p>{body}</p>"
            )

        cover_placeholder = (
            f'<div class="cover-img" '
            f'style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);'
            f'padding:60px 20px;text-align:center;color:#fff;border-radius:8px;'
            f'margin-bottom:24px;">'
            f"<h1 style=\"margin:0;font-size:24px;\">{self.title}</h1>"
            f"<p style=\"margin-top:12px;opacity:0.9;\">[封面: {self.cover_image_directive}]</p>"
            f"</div>"
        )

        tags_html = ""
        if self.tags:
            tags_html = (
                '<div style="margin-top:24px;color:#999;">'
                + " ".join(f"<span>#{t}</span>" for t in self.tags)
                + "</div>"
            )

        cta_html = ""
        if self.cta:
            cta_html = (
                f'<div style="margin-top:24px;padding:16px;'
                f'background:#f0f7ff;border-radius:8px;text-align:center;'
                f'font-weight:bold;color:#1a73e8;">{self.cta}</div>'
            )

        return f"""\
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{self.title}</title>
<style>
body {{
  max-width: 680px;
  margin: 0 auto;
  padding: 20px;
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
  line-height: 1.8;
  color: #333;
}}
h2 {{ color: #1a1a1a; margin-top: 32px; }}
p {{ margin: 12px 0; }}
blockquote {{
  border-left: 4px solid #1a73e8;
  margin: 16px 0;
  padding: 12px 16px;
  background: #f8f9fa;
  color: #555;
}}
</style>
</head>
<body>
{cover_placeholder}
<blockquote>{self.summary}</blockquote>
{"".join(sections_html)}
{cta_html}
{tags_html}
<p style="margin-top:32px;color:#ccc;font-size:12px;">
  生成时间：{self.generated_at}
</p>
</body>
</html>"""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "sections": self.sections,
            "cover_image_directive": self.cover_image_directive,
            "tags": self.tags,
            "cta": self.cta,
            "image_directives": [
                {"position": d.position, "description": d.description}
                for d in self.image_directives
            ],
            "generated_at": self.generated_at,
            "word_count": len(self.raw_body),
        }


async def generate_wechat_article(
    topic: str,
    brand_name: str = "",
    tone_of_voice: str = "",
    call_to_action: str = "",
    banned_words: str = "",
    industry: str = "",
    style_hint: str = "",
    provider: Optional[str] = None,
) -> WechatArticle:
    """Generate a complete WeChat rich post article.

    Uses the wechat platform rules from template_manager to build a structured
    prompt, then calls LLM to produce title + body + image directives.
    """
    import json as _json

    # Build the platform-aware prompt
    base_prompt = format_generation_prompt(
        platform="wechat",
        topic=topic,
        brand_name=brand_name or "品牌方",
        tone_of_voice=tone_of_voice,
        call_to_action=call_to_action,
        banned_words=banned_words,
        industry=industry,
    )

    user_prompt = (
        f"{base_prompt}\n"
        f"## 额外要求\n"
        f"- 输出必须是合法JSON，按系统提示中的字段格式返回\n"
        f"- sections 数组包含3-5个小节\n"
        f"- 每个小节必须包含 heading、body、image_directive 三个字段\n"
        f"- image_directive 要具体描述配图内容、风格、色调\n"
    )

    if style_hint:
        user_prompt += f"- 风格补充说明：{style_hint}\n"

    raw = await generate_content(
        prompt=user_prompt,
        role="content_generator",
        provider=provider,
        system_prompt_override=WECHAT_ARTICLE_SYSTEM_PROMPT,
        temperature=0.5,
        max_tokens=4000,
    )

    # Parse the LLM JSON output
    cleaned = raw.strip()
    # Strip markdown code fence if present
    if cleaned.startswith("```"):
        first_nl = cleaned.index("\n")
        last_fence = cleaned.rfind("```")
        if last_fence > first_nl:
            cleaned = cleaned[first_nl + 1 : last_fence].strip()

    try:
        data = _json.loads(cleaned)
    except _json.JSONDecodeError:
        logger.warning("LLM returned non-JSON for wechat article, wrapping as fallback")
        data = {
            "title": f"{topic} — 深度解析",
            "summary": cleaned[:100],
            "sections": [{"heading": "正文", "body": cleaned, "image_directive": ""}],
            "cover_image_directive": f"主题：{topic}，专业商务风格封面",
            "tags": [topic],
            "cta": "关注我们获取更多专业内容",
        }

    return WechatArticle(
        title=data.get("title", topic),
        summary=data.get("summary", ""),
        sections=data.get("sections", []),
        cover_image_directive=data.get("cover_image_directive", ""),
        tags=data.get("tags", []),
        cta=data.get("cta", ""),
    )
