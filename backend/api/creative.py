"""Creative content endpoints — WeChat rich post generation & export."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.content import ContentItem, ContentVariant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/creative", tags=["creative"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class WechatRichPostRequest(BaseModel):
    content_item_id: str
    variant_id: Optional[str] = None
    title_hint: str = ""
    style_hint: str = ""


class WechatRichPostResponse(BaseModel):
    task_id: str
    status: str
    feature_enabled: bool
    message: str
    generated_at: str
    payload: dict


class WechatGenerateFromTopicRequest(BaseModel):
    """Generate a WeChat article from scratch given a topic."""
    topic: str
    brand_name: str = ""
    tone_of_voice: str = ""
    call_to_action: str = ""
    banned_words: str = ""
    industry: str = ""
    style_hint: str = ""
    export_formats: List[str] = ["html", "md"]


class WechatArticleResponse(BaseModel):
    task_id: str
    status: str
    title: str
    summary: str
    sections: List[Dict[str, Any]]
    cover_image_directive: str
    image_directives: List[Dict[str, str]]
    tags: List[str]
    cta: str
    word_count: int
    exports: Dict[str, str]  # format -> content string
    generated_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/wechat-rich-post", response_model=WechatRichPostResponse)
async def generate_wechat_rich_post(
    request: WechatRichPostRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a WeChat rich post from an existing content item.

    Reads the content item / variant, uses its topic + body as input,
    then produces a full WeChat article package with image directives.
    """
    if not settings.FEATURE_WECHAT_RICH_POST:
        raise HTTPException(
            status_code=403,
            detail="FEATURE_WECHAT_RICH_POST 未开启。",
        )

    # Look up the content item
    result = await db.execute(
        select(ContentItem).where(ContentItem.id == request.content_item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="内容条目不存在")

    # Find the wechat variant or specified variant
    if request.variant_id:
        var_result = await db.execute(
            select(ContentVariant).where(ContentVariant.id == request.variant_id)
        )
    else:
        var_result = await db.execute(
            select(ContentVariant).where(
                ContentVariant.content_item_id == item.id,
                ContentVariant.platform == "wechat",
            )
        )
    variant = var_result.scalar_one_or_none()

    topic = item.topic or "未命名主题"
    style_hint = request.style_hint

    # If we have a variant, include its body as reference material
    if variant and variant.body:
        style_hint = (
            f"{style_hint}\n\n参考已有内容（请在此基础上优化为完整公众号图文）：\n"
            f"{variant.body[:2000]}"
        )

    from services.wechat_rich_post import generate_wechat_article

    try:
        article = await generate_wechat_article(
            topic=topic,
            style_hint=style_hint,
            industry=settings.DEFAULT_INDUSTRY,
        )
    except Exception:
        logger.exception("WeChat article generation failed for item %s", item.id)
        raise HTTPException(status_code=500, detail="公众号图文生成失败，请稍后重试")

    task_id = str(uuid.uuid4())

    return WechatRichPostResponse(
        task_id=task_id,
        status="generated",
        feature_enabled=True,
        message=f"公众号图文已生成：{article.title}",
        generated_at=article.generated_at,
        payload={
            "content_item_id": request.content_item_id,
            "variant_id": request.variant_id,
            **article.to_dict(),
            "html": article.to_html(),
            "markdown": article.to_markdown(),
        },
    )


@router.post("/wechat-generate", response_model=WechatArticleResponse)
async def generate_wechat_from_topic(request: WechatGenerateFromTopicRequest):
    """Generate a WeChat article from scratch given a topic.

    Returns the structured article with optional HTML/MD exports.
    """
    if not settings.FEATURE_WECHAT_RICH_POST:
        raise HTTPException(
            status_code=403,
            detail="FEATURE_WECHAT_RICH_POST 未开启。",
        )

    from services.wechat_rich_post import generate_wechat_article

    try:
        article = await generate_wechat_article(
            topic=request.topic,
            brand_name=request.brand_name,
            tone_of_voice=request.tone_of_voice,
            call_to_action=request.call_to_action,
            banned_words=request.banned_words,
            industry=request.industry,
            style_hint=request.style_hint,
        )
    except Exception:
        logger.exception("WeChat article generation failed for topic: %s", request.topic)
        raise HTTPException(status_code=500, detail="公众号图文生成失败，请稍后重试")

    exports: Dict[str, str] = {}
    for fmt in request.export_formats:
        if fmt == "html":
            exports["html"] = article.to_html()
        elif fmt == "md":
            exports["md"] = article.to_markdown()

    return WechatArticleResponse(
        task_id=str(uuid.uuid4()),
        status="generated",
        title=article.title,
        summary=article.summary,
        sections=article.sections,
        cover_image_directive=article.cover_image_directive,
        image_directives=[
            {"position": d.position, "description": d.description}
            for d in article.image_directives
        ],
        tags=article.tags,
        cta=article.cta,
        word_count=len(article.raw_body),
        exports=exports,
        generated_at=article.generated_at,
    )


@router.post("/wechat-export")
async def export_wechat_article(
    request: WechatGenerateFromTopicRequest,
):
    """Generate and immediately export a WeChat article as downloadable HTML."""
    if not settings.FEATURE_WECHAT_RICH_POST:
        raise HTTPException(
            status_code=403,
            detail="FEATURE_WECHAT_RICH_POST 未开启。",
        )

    from fastapi.responses import HTMLResponse
    from services.wechat_rich_post import generate_wechat_article

    try:
        article = await generate_wechat_article(
            topic=request.topic,
            brand_name=request.brand_name,
            tone_of_voice=request.tone_of_voice,
            call_to_action=request.call_to_action,
            banned_words=request.banned_words,
            industry=request.industry,
            style_hint=request.style_hint,
        )
    except Exception:
        logger.exception("WeChat export failed for topic: %s", request.topic)
        raise HTTPException(status_code=500, detail="公众号图文导出失败")

    return HTMLResponse(
        content=article.to_html(),
        headers={
            "Content-Disposition": f'attachment; filename="wechat_{article.title[:20]}.html"'
        },
    )
