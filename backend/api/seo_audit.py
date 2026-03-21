"""SEO audit API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from services.seo_auditor import SEOAuditor


router = APIRouter(prefix="/seo-audit", tags=["SEO 审计"])


class SEOAuditRequest(BaseModel):
    """SEO 审计请求"""
    url: str = Field(..., description="要审计的页面 URL")
    page_type: str = Field(default="article", description="页面类型：article/landing/product/homepage")


class SEOAuditResponse(BaseModel):
    """SEO 审计响应"""
    target_url: str
    page_type: str
    scores: Dict[str, int]
    strengths: List[str]
    issues: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    summary: str


@router.post("", response_model=SEOAuditResponse, summary="执行 SEO 审计")
async def run_seo_audit(request: SEOAuditRequest):
    """
    对指定 URL 执行页面级 SEO 健康检查。

    评分维度：标题优化、Meta Description、标题结构、内容质量、技术 SEO。
    输出：评分卡 + 问题清单 + 改进建议。
    """
    try:
        auditor = SEOAuditor()
        report = await auditor.audit(request.url, page_type=request.page_type)
        return SEOAuditResponse(**report.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SEO 审计失败：{str(e)}")
