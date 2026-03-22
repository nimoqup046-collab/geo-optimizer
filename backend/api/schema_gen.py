"""Schema 结构化数据生成 API 端点。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from services.schema_generator import SchemaGenerator


router = APIRouter(prefix="/schema", tags=["结构化数据"])


class SchemaGenerateRequest(BaseModel):
    """Schema 生成请求"""
    content: str = Field(..., description="待生成结构化数据的内容")
    content_type: str = Field(
        default="article",
        description="内容类型：article/qa/guide/case_study",
    )
    brand_name: Optional[str] = Field(None, description="品牌名称")
    author_name: Optional[str] = Field(None, description="作者名称")
    page_url: Optional[str] = Field(None, description="页面 URL")


class FAQSchemaRequest(BaseModel):
    """FAQ Schema 提取请求"""
    content: str = Field(..., description="待提取 FAQ 的内容")
    max_questions: int = Field(default=8, description="最大问题数", ge=1, le=20)


class HowToSchemaRequest(BaseModel):
    """HowTo Schema 生成请求"""
    content: str = Field(..., description="指南/教程内容")
    title: str = Field(default="", description="标题")


@router.post("/generate", summary="生成全套结构化数据")
async def generate_schemas(request: SchemaGenerateRequest):
    """
    为内容生成全套 Schema.org 结构化数据。

    输出：Article/FAQ/HowTo Schema + llms.txt 建议 + AI Meta 标签。
    """
    try:
        generator = SchemaGenerator()
        result = await generator.generate_schemas(
            content=request.content,
            content_type=request.content_type,
            brand_name=request.brand_name,
            author_name=request.author_name,
            page_url=request.page_url,
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema 生成失败：{str(e)}")


@router.post("/faq", summary="提取 FAQ Schema")
async def extract_faq_schema(request: FAQSchemaRequest):
    """
    从内容中提取常见问题并生成 FAQPage Schema。
    """
    try:
        generator = SchemaGenerator()
        markup = await generator.extract_faq_schema(
            content=request.content,
            max_questions=request.max_questions,
        )
        return {
            "schema_type": markup.schema_type,
            "purpose": markup.purpose,
            "json_ld": markup.json_ld,
            "html_snippet": markup.html_snippet,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FAQ Schema 生成失败：{str(e)}")


@router.post("/howto", summary="生成 HowTo Schema")
async def generate_howto_schema(request: HowToSchemaRequest):
    """
    从指南/教程内容生成 HowTo Schema。
    """
    try:
        generator = SchemaGenerator()
        markup = await generator.generate_howto_schema(
            content=request.content,
            title=request.title,
        )
        return {
            "schema_type": markup.schema_type,
            "purpose": markup.purpose,
            "json_ld": markup.json_ld,
            "html_snippet": markup.html_snippet,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HowTo Schema 生成失败：{str(e)}")
