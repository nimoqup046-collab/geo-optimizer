"""案例语料库管理 API 端点。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from services.case_corpus import CaseCorpusManager


router = APIRouter(prefix="/case-corpus", tags=["案例语料库"])


class ProcessCasesRequest(BaseModel):
    """批量案例处理请求"""
    raw_texts: List[str] = Field(..., description="原始案例文本列表（已脱敏）")
    brand_name: Optional[str] = Field(None, description="品牌名称")
    industry: str = Field(default="emotional_counseling", description="行业标识")


class StructureCaseRequest(BaseModel):
    """单案例结构化请求"""
    raw_text: str = Field(..., description="原始案例文本（已脱敏）")
    case_id: str = Field(default="CASE-0001", description="案例编号")
    brand_name: Optional[str] = Field(None, description="品牌名称")


class CaseContentRequest(BaseModel):
    """基于案例生成内容请求"""
    case_insights: List[Dict[str, Any]] = Field(
        ..., description="案例洞察列表（至少包含 title 和 key_insight 字段）"
    )
    content_type: str = Field(
        default="methodology_article",
        description="内容类型：methodology_article/success_stats/expert_qa",
    )
    platform: str = Field(default="wechat", description="发布平台")
    brand_name: Optional[str] = Field(None, description="品牌名称")


@router.post("/process", summary="批量处理案例为结构化语料")
async def process_cases(request: ProcessCasesRequest):
    """
    将原始案例文本批量转化为结构化语料库。

    输出：结构化案例、统计信息、FAQ 语料、方法论库、AI 训练语料。
    """
    try:
        manager = CaseCorpusManager()
        result = await manager.process_raw_cases(
            raw_texts=request.raw_texts,
            brand_name=request.brand_name,
            industry=request.industry,
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"案例处理失败：{str(e)}")


@router.post("/structure-single", summary="结构化单个案例")
async def structure_single_case(request: StructureCaseRequest):
    """
    将单个原始案例文本转化为结构化数据。
    """
    try:
        manager = CaseCorpusManager()
        case = await manager.structure_single_case(
            raw_text=request.raw_text,
            case_id=request.case_id,
            brand_name=request.brand_name,
        )
        if case is None:
            raise HTTPException(status_code=422, detail="案例结构化失败，请检查输入内容")
        from dataclasses import asdict
        return asdict(case)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"案例结构化失败：{str(e)}")
