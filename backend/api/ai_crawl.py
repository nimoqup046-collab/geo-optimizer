"""AI 爬取优化 API 端点。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from services.ai_crawl_optimizer import AICrawlOptimizer


router = APIRouter(prefix="/ai-crawl", tags=["AI 爬取优化"])


class AICrawlOptimizeRequest(BaseModel):
    """AI 爬取优化请求"""
    content: str = Field(..., description="待优化内容")
    brand_name: Optional[str] = Field(None, description="品牌名称")
    target_queries: Optional[List[str]] = Field(
        None, description="目标用户查询（内容应能回答的问题）"
    )
    platform: str = Field(default="wechat", description="发布平台")


@router.post("/optimize", summary="执行 AI 爬取优化分析")
async def run_ai_crawl_optimization(request: AICrawlOptimizeRequest):
    """
    分析内容的 AI 爬取就绪度并生成优化建议。

    输出：爬取就绪度评分、引用就绪度评分、问题清单、内容重写建议、
    可引用断言、Q&A 提取、优化清单。
    """
    try:
        optimizer = AICrawlOptimizer()
        report = await optimizer.optimize(
            content=request.content,
            brand_name=request.brand_name,
            target_queries=request.target_queries,
            platform=request.platform,
        )
        return report.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 爬取优化失败：{str(e)}")
