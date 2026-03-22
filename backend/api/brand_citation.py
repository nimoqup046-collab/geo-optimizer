"""品牌引用监控 API 端点。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from services.brand_citation_monitor import BrandCitationMonitor


router = APIRouter(prefix="/brand-citation", tags=["品牌引用监控"])


class CitationMonitorRequest(BaseModel):
    """品牌引用监控请求"""
    brand_name: str = Field(..., description="品牌名称")
    queries: Optional[List[str]] = Field(None, description="自定义监控查询列表")
    competitors: Optional[List[str]] = Field(None, description="竞品名称列表")
    industry: str = Field(default="emotional_counseling", description="行业标识")


class CitationProbeRequest(BaseModel):
    """单查询引用探测请求"""
    brand_name: str = Field(..., description="品牌名称")
    query: str = Field(..., description="用户查询")
    competitors: Optional[List[str]] = Field(None, description="竞品名称列表")


@router.post("/monitor", summary="执行品牌引用监控扫描")
async def run_citation_monitor(request: CitationMonitorRequest):
    """
    监控品牌在各大 LLM 回答中的引用情况。

    分析维度：品牌被引用率、引用类型、竞品对比、可见性评分。
    """
    try:
        monitor = BrandCitationMonitor()
        report = await monitor.monitor(
            brand_name=request.brand_name,
            queries=request.queries,
            competitors=request.competitors,
            industry=request.industry,
        )
        return report.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"品牌引用监控失败：{str(e)}")


@router.post("/probe", summary="单查询品牌引用探测")
async def probe_citation(request: CitationProbeRequest):
    """
    对单个用户查询进行品牌引用探测。

    模拟 AI 搜索引擎回答，检测品牌是否被引用。
    """
    try:
        monitor = BrandCitationMonitor()
        hit = await monitor.probe_single_query(
            brand_name=request.brand_name,
            query=request.query,
            competitors=request.competitors,
        )
        return {
            "query": hit.query,
            "brand_mentioned": hit.brand_mentioned,
            "mention_type": hit.mention_type,
            "context": hit.context,
            "confidence": hit.confidence,
            "response_snippet": hit.response_snippet,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"引用探测失败：{str(e)}")
