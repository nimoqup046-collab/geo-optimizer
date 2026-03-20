from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings


router = APIRouter(prefix="/creative", tags=["creative"])


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


@router.post("/wechat-rich-post", response_model=WechatRichPostResponse)
async def generate_wechat_rich_post(request: WechatRichPostRequest):
    if not settings.FEATURE_WECHAT_RICH_POST:
        raise HTTPException(
            status_code=403,
            detail="FEATURE_WECHAT_RICH_POST 未开启，当前仅提供分阶段占位能力。",
        )

    return WechatRichPostResponse(
        task_id=str(uuid.uuid4()),
        status="placeholder_ready",
        feature_enabled=True,
        message=(
            "已触发占位接口：公众号图文一键生成将在下一迭代接入真实配图、排版与发布链路。"
        ),
        generated_at=datetime.now(timezone.utc).isoformat(),
        payload={
            "content_item_id": request.content_item_id,
            "variant_id": request.variant_id,
            "title_hint": request.title_hint,
            "style_hint": request.style_hint,
            "next_step": "wire_real_wechat_artifact_pipeline",
        },
    )
