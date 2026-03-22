import logging
from collections import defaultdict
from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import resolve_workspace_id
from config import settings
from database import get_db
from models.brand import BrandProfile
from models.content import ContentItem, ContentStatus, ContentVariant
from models.report import AnalysisReport
from services.llm_service import generate_content
from services.prompt_assembler import resolve_prompt_bundle
from services.geo_scorer import compute_geo_score
from services.expert_team import run_expert_pipeline


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["content"])


class ContentGenerateRequest(BaseModel):
    workspace_id: Optional[str] = None
    report_id: str
    content_type: str = "article"
    target_platforms: List[str] = Field(
        default_factory=lambda: ["wechat", "xiaohongshu", "zhihu", "video"]
    )
    rewrite_asset_ids: List[str] = Field(default_factory=list)
    count: int = Field(default=1, ge=1, le=5)
    llm_provider: Optional[str] = None
    prompt_profile_id: Optional[str] = None
    mode: str = Field(default="standard", description="standard or expert")


class ContentVariantResponse(BaseModel):
    id: str
    content_item_id: str
    platform: str
    title: str
    body: str
    summary: str
    tags: List[str]
    llm_provider: str
    llm_model: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ContentItemResponse(BaseModel):
    id: str
    workspace_id: str
    brand_id: str
    report_id: str
    content_type: str
    topic: str
    status: str
    version_no: int
    created_at: datetime
    updated_at: datetime
    variants: List[ContentVariantResponse]


class StatusUpdateRequest(BaseModel):
    status: str
    reviewed_by: str = ""


def parse_title_and_body(text: str, fallback_topic: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return fallback_topic, text
    if lines[0].startswith("#"):
        return lines[0].lstrip("#").strip(), "\n".join(lines[1:])
    return lines[0][:120], "\n".join(lines[1:]) if len(lines) > 1 else text


def suggest_tags(platform: str, topic: str) -> List[str]:
    base = {
        "wechat": ["wechat", "longform"],
        "xiaohongshu": ["xiaohongshu", "note"],
        "zhihu": ["zhihu", "qa"],
        "video": ["video", "script"],
    }.get(platform, ["geo"])
    merged = [*base, topic[:16]]
    return [f"#{v}" if not str(v).startswith("#") else str(v) for v in merged if v]


def fallback_variant_text(
    brand_name: str,
    topic: str,
    platform: str,
    call_to_action: str,
) -> str:
    return (
        f"# {brand_name}｜{topic}（{platform}）\n\n"
        "当前为兜底内容，用于保证 GEO 闭环不中断。\n\n"
        "1. 关键洞察：用户最关心“下一步怎么做”。\n"
        "2. 执行路径：先稳定情绪，再重建沟通，最后明确边界。\n"
        "3. 回流动作：完成一次结构化沟通后，在 24 小时内记录反馈。\n\n"
        f"CTA：{call_to_action or '提交你的具体场景，获取可执行的下一步建议。'}"
    )


@router.post("/generate", response_model=List[ContentItemResponse])
async def generate_content_from_report(
    request: ContentGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    workspace_id = await resolve_workspace_id(db, request.workspace_id)
    report_result = await db.execute(
        select(AnalysisReport).where(
            AnalysisReport.id == request.report_id,
            AnalysisReport.workspace_id == workspace_id,
        )
    )
    report = report_result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="未找到分析报告")

    brand_result = await db.execute(select(BrandProfile).where(BrandProfile.id == report.brand_id))
    brand = brand_result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="未找到品牌档案")

    keywords_ranked: List[str] = []
    for _, items in report.keyword_layers.items():
        for item in items:
            keywords_ranked.append(item.get("keyword", ""))
    keywords_ranked = [k for k in keywords_ranked if k]
    if not keywords_ranked:
        keywords_ranked = [brand.name]

    target_platforms = request.target_platforms or ["wechat"]
    if request.count > settings.MAX_CONTENT_PER_REQUEST:
        raise HTTPException(status_code=400, detail="生成数量超过最大限制")

    # Expert mode: run expert pipeline for strategy + optimization context.
    expert_context_text = ""
    if request.mode == "expert" and settings.FEATURE_EXPERT_TEAM:
        try:
            brand_data = {
                "name": brand.name,
                "industry": brand.industry,
                "region": brand.region,
                "tone_of_voice": brand.tone_of_voice,
                "call_to_action": brand.call_to_action,
                "content_boundaries": brand.content_boundaries,
            }
            team_report = await run_expert_pipeline(
                brand_data=brand_data,
                keyword_layers=report.keyword_layers or {},
                gap_analysis=report.gap_analysis or {},
                recommendations=report.recommendations or [],
                target_platforms=target_platforms,
                provider=request.llm_provider or "openrouter",
            )
            expert_context_text = (
                f"\n\n## 专家团队策略指导\n{team_report.strategy.content[:800]}\n"
                f"\n## GEO 优化建议\n{team_report.geo_optimization.content[:600]}\n"
            )
        except Exception:
            expert_context_text = ""

    response_items: List[ContentItemResponse] = []
    for idx in range(request.count):
        topic = keywords_ranked[idx % len(keywords_ranked)]
        item = ContentItem(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            brand_id=brand.id,
            report_id=report.id,
            content_type=request.content_type,
            topic=topic,
            status=ContentStatus.DRAFT,
            version_no=1,
        )
        db.add(item)
        await db.flush()

        variants: List[ContentVariantResponse] = []
        for platform in target_platforms:
            bundle = await resolve_prompt_bundle(
                db=db,
                workspace_id=workspace_id,
                platform=platform,
                topic=topic,
                brand_name=brand.name,
                brand_industry=brand.industry,
                tone_of_voice=brand.tone_of_voice,
                call_to_action=brand.call_to_action,
                banned_words=",".join(brand.banned_words or []),
                role="brand_editor",
                prompt_profile_id=request.prompt_profile_id,
            )
            try:
                prompt_text = bundle.user_prompt
                if expert_context_text:
                    prompt_text = prompt_text + expert_context_text

                generated = await generate_content(
                    prompt=prompt_text,
                    role=bundle.role,
                    provider=request.llm_provider,
                    context={
                        "brand": brand.name,
                        "industry": brand.industry,
                        "region": brand.region,
                        "content_boundaries": brand.content_boundaries,
                    },
                    system_prompt_override=bundle.system_prompt,
                    temperature=0.7,
                    max_tokens=2200,
                )
            except Exception:
                logger.exception("LLM generation failed for platform=%s topic=%s, using fallback", platform, topic)
                generated = fallback_variant_text(
                    brand_name=brand.name,
                    topic=topic,
                    platform=platform,
                    call_to_action=brand.call_to_action,
                )

            title, body = parse_title_and_body(generated, topic)

            # Compute GEO scores for expert mode.
            gen_meta: dict = {
                "topic": topic,
                "report_id": report.id,
                "prompt_profile_id": bundle.profile_id,
                "prompt_profile_name": bundle.profile_name,
                "mode": request.mode,
            }
            if request.mode == "expert":
                try:
                    geo_card = compute_geo_score(generated)
                    gen_meta["geo_scores"] = geo_card.to_dict()
                except Exception:
                    pass

            variant = ContentVariant(
                id=str(uuid.uuid4()),
                content_item_id=item.id,
                platform=platform,
                title=title,
                body=body,
                summary=(body[:280] if body else generated[:280]),
                tags=suggest_tags(platform, topic),
                llm_provider=request.llm_provider or settings.DEFAULT_LLM_PROVIDER,
                llm_model="",
                generation_meta=gen_meta,
                status=ContentStatus.DRAFT,
            )
            db.add(variant)
            await db.flush()
            variants.append(
                ContentVariantResponse(
                    id=variant.id,
                    content_item_id=item.id,
                    platform=variant.platform,
                    title=variant.title,
                    body=variant.body,
                    summary=variant.summary,
                    tags=variant.tags,
                    llm_provider=variant.llm_provider,
                    llm_model=variant.llm_model,
                    status=variant.status,
                    created_at=variant.created_at,
                )
            )

        response_items.append(
            ContentItemResponse(
                id=item.id,
                workspace_id=item.workspace_id,
                brand_id=item.brand_id,
                report_id=item.report_id,
                content_type=item.content_type,
                topic=item.topic,
                status=item.status,
                version_no=item.version_no,
                created_at=item.created_at,
                updated_at=item.updated_at,
                variants=variants,
            )
        )

    await db.commit()
    return response_items


@router.get("", response_model=List[ContentItemResponse])
async def list_content_items(
    workspace_id: Optional[str] = None,
    brand_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    resolved_workspace_id = await resolve_workspace_id(db, workspace_id)
    query = select(ContentItem).where(ContentItem.workspace_id == resolved_workspace_id)
    if brand_id:
        query = query.where(ContentItem.brand_id == brand_id)
    if status:
        query = query.where(ContentItem.status == status)
    result = await db.execute(query.order_by(ContentItem.created_at.desc()))
    items = list(result.scalars().all())

    # Batch-load all variants in a single query to avoid N+1.
    item_ids = [item.id for item in items]
    variants_result = await db.execute(
        select(ContentVariant).where(ContentVariant.content_item_id.in_(item_ids))
    ) if item_ids else None
    all_variants = list(variants_result.scalars().all()) if variants_result else []
    variants_by_item: dict[str, list] = defaultdict(list)
    for v in all_variants:
        variants_by_item[v.content_item_id].append(v)

    responses: List[ContentItemResponse] = []
    for item in items:
        variants = variants_by_item.get(item.id, [])
        responses.append(
            ContentItemResponse(
                id=item.id,
                workspace_id=item.workspace_id,
                brand_id=item.brand_id,
                report_id=item.report_id,
                content_type=item.content_type,
                topic=item.topic,
                status=item.status,
                version_no=item.version_no,
                created_at=item.created_at,
                updated_at=item.updated_at,
                variants=[
                    ContentVariantResponse(
                        id=v.id,
                        content_item_id=v.content_item_id,
                        platform=v.platform,
                        title=v.title,
                        body=v.body,
                        summary=v.summary,
                        tags=v.tags,
                        llm_provider=v.llm_provider,
                        llm_model=v.llm_model,
                        status=v.status,
                        created_at=v.created_at,
                    )
                    for v in variants
                ],
            )
        )
    return responses


@router.patch("/{content_item_id}/status", response_model=ContentItemResponse)
async def update_content_status(
    content_item_id: str,
    request: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ContentItem).where(ContentItem.id == content_item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="未找到内容条目")

    item.status = request.status
    if request.reviewed_by:
        item.reviewed_by = request.reviewed_by

    variants_result = await db.execute(
        select(ContentVariant).where(ContentVariant.content_item_id == content_item_id)
    )
    variants = list(variants_result.scalars().all())
    for variant in variants:
        variant.status = request.status

    await db.commit()
    await db.refresh(item)

    return ContentItemResponse(
        id=item.id,
        workspace_id=item.workspace_id,
        brand_id=item.brand_id,
        report_id=item.report_id,
        content_type=item.content_type,
        topic=item.topic,
        status=item.status,
        version_no=item.version_no,
        created_at=item.created_at,
        updated_at=item.updated_at,
        variants=[
            ContentVariantResponse(
                id=v.id,
                content_item_id=v.content_item_id,
                platform=v.platform,
                title=v.title,
                body=v.body,
                summary=v.summary,
                tags=v.tags,
                llm_provider=v.llm_provider,
                llm_model=v.llm_model,
                status=v.status,
                created_at=v.created_at,
            )
            for v in variants
        ],
    )
