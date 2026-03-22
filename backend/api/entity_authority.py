"""专家实体权威建模 API 端点。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from services.entity_authority import EntityAuthorityBuilder


router = APIRouter(prefix="/entity-authority", tags=["实体权威建模"])


class AuthorityProfileRequest(BaseModel):
    """实体权威度画像请求"""
    brand_name: str = Field(..., description="品牌名称")
    brand_context: Optional[Dict[str, Any]] = Field(None, description="品牌上下文")
    experts_data: Optional[List[Dict[str, Any]]] = Field(None, description="已有专家信息")
    existing_content: Optional[List[str]] = Field(None, description="已有内容样本")


class ExpertContentRequest(BaseModel):
    """专家内容模板生成请求"""
    brand_name: str = Field(..., description="品牌名称")
    expert_name: str = Field(..., description="专家姓名")
    specialization: str = Field(..., description="专长领域")
    content_type: str = Field(
        default="expert_column",
        description="内容类型：expert_column/qa_answer/case_study/methodology",
    )


@router.post("/profile", summary="构建实体权威度画像")
async def build_authority_profile(request: AuthorityProfileRequest):
    """
    分析品牌的 E-E-A-T 评分并生成实体权威增强策略。

    输出：E-E-A-T 评分、权威信号、专家实体建议、Schema 标记建议。
    """
    try:
        builder = EntityAuthorityBuilder()
        profile = await builder.build_authority_profile(
            brand_name=request.brand_name,
            brand_context=request.brand_context,
            experts_data=request.experts_data,
            existing_content=request.existing_content,
        )
        return profile.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"实体权威分析失败：{str(e)}")


@router.post("/expert-content", summary="生成专家权威内容模板")
async def generate_expert_content(request: ExpertContentRequest):
    """
    为专家生成强化权威性的内容模板。

    支持类型：专家专栏、Q&A 回答、案例研究、方法论框架。
    """
    try:
        builder = EntityAuthorityBuilder()
        result = await builder.generate_expert_content_templates(
            brand_name=request.brand_name,
            expert_name=request.expert_name,
            specialization=request.specialization,
            content_type=request.content_type,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"专家内容生成失败：{str(e)}")
