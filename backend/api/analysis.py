from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import resolve_workspace_id
from config import settings
from database import get_db
from models.brand import BrandProfile
from models.keyword_topic import KeywordIntent, KeywordTopic
from models.report import AnalysisReport
from models.source_asset import SourceAsset
from services.analysis_engine import (
    build_agent_team_summary,
    build_data_layer_summary,
    build_llm_summary,
    build_recommendations,
    classify_keyword,
    estimate_difficulty,
    has_qa_structure,
    score_keyword,
)
from services.storage import storage_service


router = APIRouter(prefix="/analysis", tags=["analysis"])


class AnalysisRunRequest(BaseModel):
    workspace_id: Optional[str] = None
    brand_id: str
    keyword_seeds: List[str] = Field(default_factory=list)
    competitor_keywords: List[str] = Field(default_factory=list)
    asset_ids: List[str] = Field(default_factory=list)
    target_platforms: List[str] = Field(default_factory=lambda: ["wechat", "xiaohongshu", "zhihu", "video"])
    # Agent team options.
    use_agent_team: bool = False
    agent_roles: Optional[List[str]] = None  # subset of role_keys; None = all
    analysis_model: Optional[str] = None     # override LLM model for single-model summary


class AnalysisRunResponse(BaseModel):
    report_id: str
    title: str
    keyword_layers: Dict[str, List[Dict[str, Any]]]
    gap_analysis: Dict[str, Any]
    recommendations: List[str]
    llm_summary: str
    agent_team_report: Optional[str] = None
    created_at: datetime


def _to_markdown(report: AnalysisReport) -> str:
    payload = report.input_payload or {}
    target_platforms = payload.get("target_platforms") or []
    gap = report.gap_analysis or {}
    lines = [
        f"# {report.title}",
        "",
        f"- 生成时间：{report.created_at.isoformat()}",
        f"- 报告 ID：{report.id}",
        f"- 目标平台：{', '.join(target_platforms) if target_platforms else '未指定'}",
        f"- GEO 可见性综合得分：{gap.get('geo_visibility_score', 0):.1%}",
        "",
        "## 关键词分层",
    ]

    for layer_key in ("brand", "industry", "long_tail", "competitor"):
        layer_items = (report.keyword_layers or {}).get(layer_key, [])
        lines.append(f"### {layer_key}")
        if not layer_items:
            lines.append("- 无")
            continue
        for item in layer_items:
            lines.append(
                f"- {item.get('keyword', '')} | 难度: {item.get('difficulty', '')} | GEO分数: {item.get('score', '')}"
            )
        lines.append("")

    lines.extend(
        [
            "## 内容缺口分析",
            f"- 素材数：{gap.get('asset_count', 0)}",
            f"- 覆盖率：{gap.get('coverage_ratio', 0)}",
            f"- GEO 可见性得分：{gap.get('geo_visibility_score', 0):.1%}",
            f"- 问答结构关键词：{', '.join(gap.get('qa_structure_keywords', [])) or '无'}",
            f"- 已覆盖关键词：{', '.join(gap.get('covered_keywords', [])) or '无'}",
            f"- 缺失关键词：{', '.join(gap.get('missing_keywords', [])) or '无'}",
            "",
            "## 推荐动作",
        ]
    )
    for idx, item in enumerate(report.recommendations or [], start=1):
        lines.append(f"{idx}. {item}")

    lines.extend(
        [
            "",
            "## LLM 摘要",
            report.llm_summary or "暂无",
            "",
        ]
    )

    # Append agent team report if present.
    agent_team_report = (report.competitor_analysis or {}).get("agent_team_report")
    if agent_team_report:
        lines.extend(
            [
                "---",
                "",
                "# 专家团队综合报告",
                "",
                agent_team_report,
                "",
            ]
        )

    return "\n".join(lines)


def _to_pdf(markdown_text: str) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.pdfgen import canvas
    except Exception:
        return markdown_text.encode("utf-8")

    export_path = Path(settings.EXPORT_DIR) / f"report_tmp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.pdf"
    c = canvas.Canvas(str(export_path), pagesize=A4)
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    c.setFont("STSong-Light", 11)
    y = 800
    for raw_line in markdown_text.splitlines():
        line = raw_line if raw_line.strip() else " "
        while len(line) > 95:
            seg, line = line[:95], line[95:]
            if y < 60:
                c.showPage()
                c.setFont("STSong-Light", 11)
                y = 800
            c.drawString(40, y, seg)
            y -= 16
        if y < 60:
            c.showPage()
            c.setFont("STSong-Light", 11)
            y = 800
        c.drawString(40, y, line)
        y -= 16
    c.save()
    data = export_path.read_bytes()
    export_path.unlink(missing_ok=True)
    return data


@router.post("/run", response_model=AnalysisRunResponse)
async def run_analysis(request: AnalysisRunRequest, db: AsyncSession = Depends(get_db)):
    workspace_id = await resolve_workspace_id(db, request.workspace_id)
    brand_result = await db.execute(select(BrandProfile).where(BrandProfile.id == request.brand_id))
    brand = brand_result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="未找到品牌")

    asset_texts: List[str] = []
    if request.asset_ids:
        asset_result = await db.execute(
            select(SourceAsset).where(
                SourceAsset.workspace_id == workspace_id,
                SourceAsset.brand_id == request.brand_id,
                SourceAsset.id.in_(request.asset_ids),
            )
        )
        assets = list(asset_result.scalars().all())
    else:
        # If caller does not pass specific assets, use all brand assets by default.
        asset_result = await db.execute(
            select(SourceAsset).where(
                SourceAsset.workspace_id == workspace_id,
                SourceAsset.brand_id == request.brand_id,
            )
        )
        assets = list(asset_result.scalars().all())

    asset_texts = [a.raw_text for a in assets if a.raw_text and a.raw_text.strip()]

    all_keywords = [k.strip() for k in request.keyword_seeds if k.strip()]
    all_keywords.extend([k.strip() for k in request.competitor_keywords if k.strip()])
    all_keywords = list(dict.fromkeys(all_keywords))
    if not all_keywords:
        raise HTTPException(status_code=400, detail="keyword_seeds 不能为空")

    await db.execute(
        delete(KeywordTopic).where(
            KeywordTopic.workspace_id == workspace_id,
            KeywordTopic.brand_id == request.brand_id,
            KeywordTopic.source == "analysis_run",
        )
    )

    keyword_layers: Dict[str, List[Dict[str, Any]]] = {
        KeywordIntent.BRAND: [],
        KeywordIntent.INDUSTRY: [],
        KeywordIntent.LONG_TAIL: [],
        KeywordIntent.COMPETITOR: [],
    }

    # Pre-compute data layer first so we know which keywords are covered.
    data_layer_pre = build_data_layer_summary(asset_texts, all_keywords)
    covered_set = set(data_layer_pre.get("covered_keywords", []))

    for keyword in all_keywords:
        intent = classify_keyword(keyword, brand.name, brand.competitors or [])
        difficulty = estimate_difficulty(keyword)
        covered = keyword in covered_set
        qa = has_qa_structure(keyword)
        score = score_keyword(
            keyword,
            intent,
            difficulty,
            covered=covered,
            has_qa_structure=qa,
            has_entity=(intent == "brand"),
        )
        priority = int(score)

        topic = KeywordTopic(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            brand_id=request.brand_id,
            keyword=keyword,
            intent=intent,
            source="analysis_run",
            priority=priority,
            difficulty=difficulty,
            score=score,
            target_platforms=request.target_platforms,
        )
        db.add(topic)
        keyword_layers[intent].append(
            {
                "keyword": keyword,
                "intent": intent,
                "difficulty": difficulty,
                "score": score,
                "priority": priority,
                "covered": covered,
                "qa_structure": qa,
                "target_platforms": request.target_platforms,
            }
        )

    data_layer = build_data_layer_summary(asset_texts, all_keywords)
    recommendations = build_recommendations(keyword_layers, data_layer)
    competitor_analysis = {
        "competitors": brand.competitors or [],
        "input_competitor_keywords": request.competitor_keywords,
        "suggestion": "围绕竞品高意图词设计对比内容，突出边界、方法和结果指标。",
    }

    llm_payload = {
        "brand": {
            "name": brand.name,
            "industry": brand.industry,
            "tone_of_voice": brand.tone_of_voice,
            "call_to_action": brand.call_to_action,
            "region": brand.region,
        },
        "keyword_layers": keyword_layers,
        "gap_analysis": data_layer,
        "recommendations": recommendations,
        "assets_meta": {
            "selected_assets_count": len(assets),
            "parsed_text_assets_count": len(asset_texts),
            "selected_asset_ids": request.asset_ids,
            "auto_selected_all_assets": len(request.asset_ids) == 0,
        },
    }

    llm_summary = await build_llm_summary(llm_payload, model=request.analysis_model)
    report_title = f"{brand.name} GEO 策略报告"

    # Run agent team if requested and available.
    agent_team_report: Optional[str] = None
    if request.use_agent_team and settings.FEATURE_AGENT_TEAM:
        agent_team_report = await build_agent_team_summary(
            llm_payload,
            roles=request.agent_roles,
        )
        competitor_analysis["agent_team_report"] = agent_team_report

    report = AnalysisReport(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        brand_id=request.brand_id,
        title=report_title,
        report_type="strategy",
        input_payload=request.model_dump(),
        keyword_layers=keyword_layers,
        gap_analysis=data_layer,
        competitor_analysis=competitor_analysis,
        recommendations=recommendations,
        llm_summary=llm_summary,
        status="completed",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return AnalysisRunResponse(
        report_id=report.id,
        title=report.title,
        keyword_layers=report.keyword_layers,
        gap_analysis=report.gap_analysis,
        recommendations=report.recommendations,
        llm_summary=report.llm_summary,
        agent_team_report=agent_team_report,
        created_at=report.created_at,
    )


@router.get("/reports", response_model=List[AnalysisRunResponse])
async def list_reports(
    brand_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    resolved_workspace_id = await resolve_workspace_id(db, workspace_id)
    query = select(AnalysisReport).where(AnalysisReport.workspace_id == resolved_workspace_id)
    if brand_id:
        query = query.where(AnalysisReport.brand_id == brand_id)
    result = await db.execute(query.order_by(AnalysisReport.created_at.desc()))
    reports = list(result.scalars().all())
    return [
        AnalysisRunResponse(
            report_id=r.id,
            title=r.title,
            keyword_layers=r.keyword_layers,
            gap_analysis=r.gap_analysis,
            recommendations=r.recommendations,
            llm_summary=r.llm_summary,
            agent_team_report=(r.competitor_analysis or {}).get("agent_team_report"),
            created_at=r.created_at,
        )
        for r in reports
    ]


@router.get("/reports/{report_id}/export")
async def export_report(
    report_id: str,
    format: str = Query("md", pattern="^(md|pdf)$"),
    workspace_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    resolved_workspace_id = await resolve_workspace_id(db, workspace_id)
    result = await db.execute(
        select(AnalysisReport).where(
            AnalysisReport.id == report_id,
            AnalysisReport.workspace_id == resolved_workspace_id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="未找到分析报告")

    markdown_text = _to_markdown(report)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "md":
        file_name = f"analysis_report_{ts}.md"
        payload = markdown_text.encode("utf-8")
        report.md_path = storage_service.save_export_bytes(file_name, payload)
        await db.commit()
        if report.md_path.startswith("s3://"):
            raise HTTPException(status_code=501, detail="当前版本暂不支持 S3 导出下载代理")
        return FileResponse(path=report.md_path, media_type="text/markdown", filename=file_name)

    file_name = f"analysis_report_{ts}.pdf"
    payload = _to_pdf(markdown_text)
    report.pdf_path = storage_service.save_export_bytes(file_name, payload)
    await db.commit()
    if report.pdf_path.startswith("s3://"):
        raise HTTPException(status_code=501, detail="当前版本暂不支持 S3 导出下载代理")
    return FileResponse(path=report.pdf_path, media_type="application/pdf", filename=file_name)
