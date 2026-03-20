from datetime import datetime, timezone
import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import resolve_workspace_id
from database import get_db
from models.brand import BrandProfile
from models.content import ContentItem, ContentStatus, ContentVariant
from models.keyword_topic import KeywordTopic
from models.performance import OptimizationInsight, PerformanceSnapshot
from models.publish_task import PublishTask
from models.report import AnalysisReport
from models.source_asset import SourceAsset


router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_BRAND_NAME = "演示品牌（情感咨询）"
DEMO_ASSET_TITLE = "演示素材-公众号文章"
DEMO_REPORT_TITLE = "演示品牌 GEO 策略报告"
DEMO_TOPIC = "婚姻关系修复"
DEMO_INSIGHT_TYPE = "demo_next_action"
DEMO_KEYWORD = "婚姻修复"


class DemoBootstrapRequest(BaseModel):
    workspace_id: Optional[str] = None
    force_reset: bool = False


class DemoBootstrapResponse(BaseModel):
    workspace_id: str
    brand_id: str
    asset_id: str
    report_id: str
    content_id: str
    task_id: str
    performance_id: str
    insight_id: str
    bootstrapped_at: str


class DemoStatusResponse(BaseModel):
    ready: bool
    workspace_id: str
    last_bootstrap_at: str | None
    counts: dict


def _keyword_layers() -> dict:
    return {
        "brand": [
            {
                "keyword": "演示品牌 情感修复",
                "intent": "brand",
                "difficulty": "low",
                "score": 88,
                "priority": 88,
                "target_platforms": ["wechat", "xiaohongshu", "zhihu", "video"],
            }
        ],
        "industry": [
            {
                "keyword": "婚姻关系修复",
                "intent": "industry",
                "difficulty": "medium",
                "score": 82,
                "priority": 82,
                "target_platforms": ["wechat", "xiaohongshu", "zhihu"],
            }
        ],
        "long_tail": [
            {
                "keyword": "信任危机沟通技巧",
                "intent": "long_tail",
                "difficulty": "medium",
                "score": 79,
                "priority": 79,
                "target_platforms": ["zhihu", "wechat"],
            }
        ],
        "competitor": [
            {
                "keyword": "情感咨询机构对比",
                "intent": "competitor",
                "difficulty": "high",
                "score": 68,
                "priority": 68,
                "target_platforms": ["zhihu"],
            }
        ],
    }


def _gap_analysis() -> dict:
    return {
        "coverage_score": 61,
        "missing_topics": ["复联阶段话术", "边界重建", "冲突降级流程"],
        "platform_fit": {
            "wechat": "适合长文深度解析，建议每周 2 篇。",
            "xiaohongshu": "适合经验清单和案例卡片，建议每周 3 条。",
            "zhihu": "适合问答型权威内容，建议每周 2 条。",
            "video": "适合 60 秒脚本，建议每周 2 条。",
        },
    }


def _recommendations() -> list[str]:
    return [
        "围绕“婚姻关系修复”建立 1 篇主文 + 3 条平台改写稿。",
        "每篇内容补充可引用结论句，提高 AI 平台摘要引用率。",
        "发布后 24 小时回填阅读、互动、线索数据，进入下一轮优化。",
    ]


def _variant_body(platform: str) -> tuple[str, str]:
    if platform == "wechat":
        return (
            "婚姻关系修复：先稳情绪，再修信任，最后建规则",
            "一、先做情绪止损：先暂停争执，避免继续消耗。\n"
            "二、再做事实澄清：只讨论事实，不翻旧账。\n"
            "三、最后做行动复盘：每周一次沟通复盘会。\n\n"
            "结论：关系修复不是“和好”两个字，而是可执行的步骤。\n"
            "CTA：提交你的具体情境，我们给你下一步建议。",
        )
    if platform == "xiaohongshu":
        return (
            "关系修复 3 步走（可直接照做）",
            "1. 情绪止损：48 小时内先把沟通节奏降下来。\n"
            "2. 沟通重建：一问一答，不抢话，不指责。\n"
            "3. 规则落地：把边界写成清单，按周复盘。\n\n"
            "#婚姻修复 #关系沟通 #情感咨询",
        )
    if platform == "zhihu":
        return (
            "婚姻关系出现信任危机后，应该先做什么？",
            "先明确目标：修复关系，不是赢辩论。\n"
            "建议采用“三层沟通法”：情绪层安抚、事实层澄清、行动层执行。\n"
            "只要每一步可验证，关系恢复速度会明显提升。",
        )
    return (
        "60 秒口播脚本：关系修复最关键的一步",
        "开场：关系修复最怕的不是争吵，而是长期冷处理。\n"
        "中段：今天给你 3 步，情绪止损、事实澄清、规则重建。\n"
        "结尾：做不到全部，先做第一步也比原地消耗强。",
    )


async def _reset_demo_data(db: AsyncSession, workspace_id: str, brand_id: str) -> None:
    variant_ids_result = await db.execute(
        select(ContentVariant.id)
        .join(ContentItem, ContentVariant.content_item_id == ContentItem.id)
        .where(ContentItem.workspace_id == workspace_id, ContentItem.brand_id == brand_id)
    )
    variant_ids = [row[0] for row in variant_ids_result.all()]

    content_ids_result = await db.execute(
        select(ContentItem.id).where(
            ContentItem.workspace_id == workspace_id, ContentItem.brand_id == brand_id
        )
    )
    content_ids = [row[0] for row in content_ids_result.all()]

    if variant_ids:
        await db.execute(
            delete(PublishTask).where(
                PublishTask.workspace_id == workspace_id,
                PublishTask.brand_id == brand_id,
                PublishTask.content_variant_id.in_(variant_ids),
            )
        )
        await db.execute(
            delete(PerformanceSnapshot).where(
                PerformanceSnapshot.workspace_id == workspace_id,
                PerformanceSnapshot.brand_id == brand_id,
                PerformanceSnapshot.content_variant_id.in_(variant_ids),
            )
        )

    await db.execute(
        delete(OptimizationInsight).where(
            OptimizationInsight.workspace_id == workspace_id,
            OptimizationInsight.brand_id == brand_id,
        )
    )
    await db.execute(
        delete(PerformanceSnapshot).where(
            PerformanceSnapshot.workspace_id == workspace_id,
            PerformanceSnapshot.brand_id == brand_id,
        )
    )
    if variant_ids:
        await db.execute(delete(ContentVariant).where(ContentVariant.id.in_(variant_ids)))
    if content_ids:
        await db.execute(delete(ContentItem).where(ContentItem.id.in_(content_ids)))
    await db.execute(
        delete(KeywordTopic).where(
            KeywordTopic.workspace_id == workspace_id, KeywordTopic.brand_id == brand_id
        )
    )
    await db.execute(
        delete(AnalysisReport).where(
            AnalysisReport.workspace_id == workspace_id,
            AnalysisReport.brand_id == brand_id,
        )
    )
    await db.execute(
        delete(SourceAsset).where(
            SourceAsset.workspace_id == workspace_id, SourceAsset.brand_id == brand_id
        )
    )
    await db.execute(
        delete(BrandProfile).where(
            BrandProfile.workspace_id == workspace_id, BrandProfile.id == brand_id
        )
    )
    await db.commit()


@router.post("/bootstrap", response_model=DemoBootstrapResponse)
async def bootstrap_demo_data(
    request: DemoBootstrapRequest,
    db: AsyncSession = Depends(get_db),
):
    workspace_id = await resolve_workspace_id(db, request.workspace_id)

    existing_brand_result = await db.execute(
        select(BrandProfile).where(
            BrandProfile.workspace_id == workspace_id,
            BrandProfile.name == DEMO_BRAND_NAME,
        )
    )
    brand = existing_brand_result.scalar_one_or_none()

    if request.force_reset and brand:
        await _reset_demo_data(db, workspace_id, brand.id)
        brand = None

    if not brand:
        brand = BrandProfile(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            name=DEMO_BRAND_NAME,
            industry="emotion_consulting",
            service_description="聚焦婚姻关系修复与沟通重建的咨询服务。",
            target_audience="关系冲突中、希望稳定修复关系的成年人群。",
            tone_of_voice="专业、温和、可执行",
            call_to_action="提交你的具体情况，获取一对一建议。",
            region="上海 / 华东",
            competitors=["竞品A", "竞品B"],
            banned_words=["保证修复", "100%成功"],
            glossary={"GEO": "Generative Engine Optimization"},
            platform_preferences={
                "wechat": True,
                "xiaohongshu": True,
                "zhihu": True,
                "video": True,
            },
            content_boundaries="不做医疗诊断，不做夸大承诺。",
        )
        db.add(brand)
        await db.flush()
    else:
        brand.industry = "emotion_consulting"
        brand.service_description = "聚焦婚姻关系修复与沟通重建的咨询服务。"
        brand.target_audience = "关系冲突中、希望稳定修复关系的成年人群。"
        brand.tone_of_voice = "专业、温和、可执行"
        brand.call_to_action = "提交你的具体情况，获取一对一建议。"
        brand.region = "上海 / 华东"
        brand.competitors = ["竞品A", "竞品B"]
        brand.banned_words = ["保证修复", "100%成功"]
        brand.glossary = {"GEO": "Generative Engine Optimization"}
        brand.platform_preferences = {
            "wechat": True,
            "xiaohongshu": True,
            "zhihu": True,
            "video": True,
        }
        brand.content_boundaries = "不做医疗诊断，不做夸大承诺。"

    asset_result = await db.execute(
        select(SourceAsset).where(
            SourceAsset.workspace_id == workspace_id,
            SourceAsset.brand_id == brand.id,
            SourceAsset.title == DEMO_ASSET_TITLE,
        )
    )
    asset = asset_result.scalar_one_or_none()
    if not asset:
        asset = SourceAsset(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            brand_id=brand.id,
            title=DEMO_ASSET_TITLE,
            source_type="pasted_text",
            platform="wechat",
            raw_text=(
                "关系修复要先做情绪止损，再做事实澄清，最后建立长期沟通规则。"
                "建议每周复盘一次关系进展，持续降低冲突。"
            ),
            summary="演示素材：关系修复三步法。",
            tags=["演示", "关系修复"],
            status="ready",
        )
        db.add(asset)
        await db.flush()
    else:
        asset.platform = "wechat"
        asset.raw_text = (
            "关系修复要先做情绪止损，再做事实澄清，最后建立长期沟通规则。"
            "建议每周复盘一次关系进展，持续降低冲突。"
        )
        asset.summary = "演示素材：关系修复三步法。"
        asset.tags = ["演示", "关系修复"]
        asset.status = "ready"

    report_result = await db.execute(
        select(AnalysisReport).where(
            AnalysisReport.workspace_id == workspace_id,
            AnalysisReport.brand_id == brand.id,
            AnalysisReport.title == DEMO_REPORT_TITLE,
        )
    )
    report = report_result.scalar_one_or_none()
    if not report:
        report = AnalysisReport(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            brand_id=brand.id,
            title=DEMO_REPORT_TITLE,
            report_type="strategy",
            input_payload={"source": "demo_bootstrap"},
            keyword_layers=_keyword_layers(),
            gap_analysis=_gap_analysis(),
            competitor_analysis={
                "competitors": brand.competitors,
                "suggestion": "用对比型问答内容争夺高意图关键词。",
            },
            recommendations=_recommendations(),
            llm_summary="该品牌在情感咨询场景具备基础内容资产，建议优先做“可引用结论 + 多平台改写”策略。",
            status="completed",
        )
        db.add(report)
        await db.flush()
    else:
        report.report_type = "strategy"
        report.input_payload = {"source": "demo_bootstrap"}
        report.keyword_layers = _keyword_layers()
        report.gap_analysis = _gap_analysis()
        report.competitor_analysis = {
            "competitors": brand.competitors,
            "suggestion": "用对比型问答内容争夺高意图关键词。",
        }
        report.recommendations = _recommendations()
        report.llm_summary = "该品牌在情感咨询场景具备基础内容资产，建议优先做“可引用结论 + 多平台改写”策略。"
        report.status = "completed"

    content_result = await db.execute(
        select(ContentItem).where(
            ContentItem.workspace_id == workspace_id,
            ContentItem.brand_id == brand.id,
            ContentItem.report_id == report.id,
            ContentItem.topic == DEMO_TOPIC,
        )
    )
    content_item = content_result.scalar_one_or_none()
    if not content_item:
        content_item = ContentItem(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            brand_id=brand.id,
            report_id=report.id,
            content_type="article",
            topic=DEMO_TOPIC,
            status=ContentStatus.APPROVED,
            version_no=1,
        )
        db.add(content_item)
        await db.flush()

    variants_result = await db.execute(
        select(ContentVariant).where(ContentVariant.content_item_id == content_item.id)
    )
    variants = list(variants_result.scalars().all())
    if not variants:
        variants = []
        for platform in ["wechat", "xiaohongshu", "zhihu", "video"]:
            title, body = _variant_body(platform)
            variant = ContentVariant(
                id=str(uuid.uuid4()),
                content_item_id=content_item.id,
                platform=platform,
                title=title,
                body=body,
                summary=body[:160],
                tags=["#演示", f"#{platform}", "#GEO"],
                llm_provider="demo",
                llm_model="template-v1",
                generation_meta={"source": "demo_bootstrap"},
                status=ContentStatus.APPROVED,
            )
            db.add(variant)
            await db.flush()
            variants.append(variant)
    else:
        for variant in variants:
            title, body = _variant_body(variant.platform)
            variant.title = title
            variant.body = body
            variant.summary = body[:160]
            variant.tags = ["#演示", f"#{variant.platform}", "#GEO"]
            variant.llm_provider = "demo"
            variant.llm_model = "template-v1"
            variant.generation_meta = {"source": "demo_bootstrap"}
            variant.status = ContentStatus.APPROVED

    primary_variant = variants[0]
    task_result = await db.execute(
        select(PublishTask).where(
            PublishTask.workspace_id == workspace_id,
            PublishTask.brand_id == brand.id,
            PublishTask.content_variant_id == primary_variant.id,
        )
    )
    task = task_result.scalar_one_or_none()
    if not task:
        task = PublishTask(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            brand_id=brand.id,
            content_variant_id=primary_variant.id,
            platform=primary_variant.platform,
            status="posted",
            human_confirmation="confirmed",
            publish_url="https://example.com/demo-post",
            result_payload={"source": "demo_bootstrap"},
        )
        db.add(task)
        await db.flush()
    else:
        task.status = "posted"
        task.human_confirmation = "confirmed"
        task.publish_url = "https://example.com/demo-post"
        task.result_payload = {"source": "demo_bootstrap"}

    perf_result = await db.execute(
        select(PerformanceSnapshot).where(
            PerformanceSnapshot.workspace_id == workspace_id,
            PerformanceSnapshot.brand_id == brand.id,
            PerformanceSnapshot.publish_task_id == task.id,
        )
    )
    snapshot = perf_result.scalar_one_or_none()
    if not snapshot:
        snapshot = PerformanceSnapshot(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            brand_id=brand.id,
            publish_task_id=task.id,
            content_variant_id=primary_variant.id,
            keyword=DEMO_KEYWORD,
            platform=primary_variant.platform,
            impressions=2100,
            reads=486,
            likes=64,
            favorites=28,
            comments=19,
            shares=11,
            leads=7,
            keyword_index=72.6,
            notes="演示数据：首轮发布后 24h 回流。",
        )
        db.add(snapshot)
        await db.flush()
    else:
        snapshot.keyword = DEMO_KEYWORD
        snapshot.platform = primary_variant.platform
        snapshot.impressions = 2100
        snapshot.reads = 486
        snapshot.likes = 64
        snapshot.favorites = 28
        snapshot.comments = 19
        snapshot.shares = 11
        snapshot.leads = 7
        snapshot.keyword_index = 72.6
        snapshot.notes = "演示数据：首轮发布后 24h 回流。"

    insight_result = await db.execute(
        select(OptimizationInsight).where(
            OptimizationInsight.workspace_id == workspace_id,
            OptimizationInsight.brand_id == brand.id,
            OptimizationInsight.insight_type == DEMO_INSIGHT_TYPE,
        )
    )
    insight = insight_result.scalar_one_or_none()
    if not insight:
        insight = OptimizationInsight(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            brand_id=brand.id,
            source_snapshot_ids=[snapshot.id],
            insight_type=DEMO_INSIGHT_TYPE,
            title="下一轮优先扩写“信任重建”主题",
            details="当前发布数据表明微信平台的高意图读者转化更好，建议继续扩写“沟通与边界重建”系列。",
            action_items=[
                "新增 2 篇微信长文，保留可引用结论段。",
                "同步产出 3 条小红书图文摘要，导流到长文。",
                "一周后复盘关键词指数与线索成本。",
            ],
        )
        db.add(insight)
        await db.flush()
    else:
        insight.source_snapshot_ids = [snapshot.id]
        insight.title = "下一轮优先扩写“信任重建”主题"
        insight.details = "当前发布数据表明微信平台的高意图读者转化更好，建议继续扩写“沟通与边界重建”系列。"
        insight.action_items = [
            "新增 2 篇微信长文，保留可引用结论段。",
            "同步产出 3 条小红书图文摘要，导流到长文。",
            "一周后复盘关键词指数与线索成本。",
        ]

    await db.commit()

    return DemoBootstrapResponse(
        workspace_id=workspace_id,
        brand_id=brand.id,
        asset_id=asset.id,
        report_id=report.id,
        content_id=content_item.id,
        task_id=task.id,
        performance_id=snapshot.id,
        insight_id=insight.id,
        bootstrapped_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/status", response_model=DemoStatusResponse)
async def demo_status(
    workspace_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    resolved_workspace_id = await resolve_workspace_id(db, workspace_id)

    brand_result = await db.execute(
        select(BrandProfile).where(
            BrandProfile.workspace_id == resolved_workspace_id,
            BrandProfile.name == DEMO_BRAND_NAME,
        )
    )
    brand = brand_result.scalar_one_or_none()

    counts = {
        "brands": 0,
        "assets": 0,
        "reports": 0,
        "contents": 0,
        "variants": 0,
        "tasks": 0,
        "performance_snapshots": 0,
        "insights": 0,
    }
    last_bootstrap_at = None

    if brand:
        counts["brands"] = 1

        assets_count_result = await db.execute(
            select(func.count(SourceAsset.id)).where(
                SourceAsset.workspace_id == resolved_workspace_id,
                SourceAsset.brand_id == brand.id,
            )
        )
        counts["assets"] = int(assets_count_result.scalar_one() or 0)

        reports_count_result = await db.execute(
            select(func.count(AnalysisReport.id)).where(
                AnalysisReport.workspace_id == resolved_workspace_id,
                AnalysisReport.brand_id == brand.id,
            )
        )
        counts["reports"] = int(reports_count_result.scalar_one() or 0)

        contents_count_result = await db.execute(
            select(func.count(ContentItem.id)).where(
                ContentItem.workspace_id == resolved_workspace_id,
                ContentItem.brand_id == brand.id,
            )
        )
        counts["contents"] = int(contents_count_result.scalar_one() or 0)

        variant_count_result = await db.execute(
            select(func.count(ContentVariant.id))
            .join(ContentItem, ContentVariant.content_item_id == ContentItem.id)
            .where(
                ContentItem.workspace_id == resolved_workspace_id,
                ContentItem.brand_id == brand.id,
            )
        )
        counts["variants"] = int(variant_count_result.scalar_one() or 0)

        tasks_count_result = await db.execute(
            select(func.count(PublishTask.id)).where(
                PublishTask.workspace_id == resolved_workspace_id,
                PublishTask.brand_id == brand.id,
            )
        )
        counts["tasks"] = int(tasks_count_result.scalar_one() or 0)

        perf_count_result = await db.execute(
            select(func.count(PerformanceSnapshot.id)).where(
                PerformanceSnapshot.workspace_id == resolved_workspace_id,
                PerformanceSnapshot.brand_id == brand.id,
            )
        )
        counts["performance_snapshots"] = int(perf_count_result.scalar_one() or 0)

        insights_count_result = await db.execute(
            select(func.count(OptimizationInsight.id)).where(
                OptimizationInsight.workspace_id == resolved_workspace_id,
                OptimizationInsight.brand_id == brand.id,
            )
        )
        counts["insights"] = int(insights_count_result.scalar_one() or 0)

        latest_result = await db.execute(
            select(func.max(OptimizationInsight.created_at)).where(
                OptimizationInsight.workspace_id == resolved_workspace_id,
                OptimizationInsight.brand_id == brand.id,
            )
        )
        latest_dt = latest_result.scalar_one_or_none()
        if latest_dt:
            last_bootstrap_at = latest_dt.replace(tzinfo=timezone.utc).isoformat()

    ready = (
        counts["brands"] > 0
        and counts["assets"] > 0
        and counts["reports"] > 0
        and counts["contents"] > 0
        and counts["tasks"] > 0
        and counts["performance_snapshots"] > 0
        and counts["insights"] > 0
    )

    return DemoStatusResponse(
        ready=ready,
        workspace_id=resolved_workspace_id,
        last_bootstrap_at=last_bootstrap_at,
        counts=counts,
    )
