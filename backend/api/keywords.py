"""
关键词相关API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from database import get_db
from models.keyword import Keyword, KeywordCategory
from services.llm_service import generate_content
from services.keyword_researcher import KeywordResearcher
from services.topic_cluster import TopicClusterEngine
from services.content_calendar import ContentCalendarGenerator


router = APIRouter(prefix="/keywords", tags=["关键词"])


# ==================== 请求/响应模型 ====================

class KeywordCreate(BaseModel):
    """创建关键词请求"""
    keyword: str = Field(..., description="关键词", min_length=1, max_length=200)
    category: str = Field(default=KeywordCategory.INDUSTRY, description="分类")
    notes: Optional[str] = Field(None, description="备注")


class KeywordUpdate(BaseModel):
    """更新关键词请求"""
    keyword: Optional[str] = None
    category: Optional[str] = None
    recommended: Optional[bool] = None
    active: Optional[bool] = None
    notes: Optional[str] = None


class KeywordResponse(BaseModel):
    """关键词响应"""
    id: str
    keyword: str
    category: str
    search_volume: int
    trend: List[dict]
    geo_score: float
    competition_level: str
    ai_references: int
    platform_coverage: dict
    recommended: bool
    active: bool
    generated_content_count: int
    created_at: datetime
    updated_at: datetime
    last_analyzed_at: Optional[datetime]
    notes: Optional[str]

    class Config:
        from_attributes = True


class KeywordAnalysisRequest(BaseModel):
    """关键词分析请求"""
    keyword_ids: List[str] = Field(..., description="要分析的关键词ID列表")
    deep_analysis: bool = Field(default=False, description="是否深度分析")


class KeywordAnalysisResponse(BaseModel):
    """关键词分析响应"""
    keyword_id: str
    keyword: str
    geo_score: float
    search_opportunity: str  # 高/中/低
    competition_level: str
    recommendations: List[str]
    related_keywords: List[str]
    content_suggestions: List[str]


class BatchImportRequest(BaseModel):
    """批量导入请求"""
    keywords: List[str] = Field(..., description="关键词列表")
    category: str = Field(default=KeywordCategory.INDUSTRY, description="默认分类")


# ==================== API端点 ====================

@router.post("", response_model=KeywordResponse, summary="添加关键词")
async def create_keyword(
    request: KeywordCreate,
    db: AsyncSession = Depends(get_db)
):
    """添加新关键词"""
    # 检查是否已存在
    existing = await db.execute(
        select(Keyword).where(Keyword.keyword == request.keyword)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="关键词已存在")

    keyword = Keyword(
        id=str(uuid.uuid4()),
        keyword=request.keyword,
        category=request.category,
        notes=request.notes
    )

    db.add(keyword)
    await db.commit()
    await db.refresh(keyword)

    return keyword


@router.get("", response_model=List[KeywordResponse], summary="获取关键词列表")
async def get_keywords(
    category: Optional[str] = None,
    active: Optional[bool] = None,
    recommended: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取关键词列表，支持筛选和分页"""
    query = select(Keyword)

    if category:
        query = query.where(Keyword.category == category)
    if active is not None:
        query = query.where(Keyword.active == active)
    if recommended is not None:
        query = query.where(Keyword.recommended == recommended)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{keyword_id}", response_model=KeywordResponse, summary="获取关键词详情")
async def get_keyword(
    keyword_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取单个关键词详情"""
    result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
    keyword = result.scalar_one_or_none()

    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    return keyword


@router.put("/{keyword_id}", response_model=KeywordResponse, summary="更新关键词")
async def update_keyword(
    keyword_id: str,
    request: KeywordUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新关键词信息"""
    result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
    keyword = result.scalar_one_or_none()

    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    # 更新字段
    if request.keyword is not None:
        keyword.keyword = request.keyword
    if request.category is not None:
        keyword.category = request.category
    if request.recommended is not None:
        keyword.recommended = request.recommended
    if request.active is not None:
        keyword.active = request.active
    if request.notes is not None:
        keyword.notes = request.notes

    await db.commit()
    await db.refresh(keyword)

    return keyword


@router.delete("/{keyword_id}", summary="删除关键词")
async def delete_keyword(
    keyword_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除关键词"""
    result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
    keyword = result.scalar_one_or_none()

    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    await db.delete(keyword)
    await db.commit()

    return {"message": "删除成功"}


@router.post("/batch-import", response_model=List[KeywordResponse], summary="批量导入关键词")
async def batch_import_keywords(
    request: BatchImportRequest,
    db: AsyncSession = Depends(get_db)
):
    """批量导入关键词"""
    keywords = []

    for kw in request.keywords:
        # 检查是否已存在
        existing = await db.execute(
            select(Keyword).where(Keyword.keyword == kw)
        )
        if existing.scalar_one_or_none():
            continue

        keyword = Keyword(
            id=str(uuid.uuid4()),
            keyword=kw,
            category=request.category
        )
        keywords.append(keyword)
        db.add(keyword)

    await db.commit()

    for keyword in keywords:
        await db.refresh(keyword)

    return keywords


@router.post("/{keyword_id}/analyze", response_model=KeywordAnalysisResponse, summary="分析关键词")
async def analyze_keyword(
    keyword_id: str,
    deep_analysis: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    分析关键词的GEO价值和内容机会

    使用AI分析关键词的搜索价值、竞争程度、内容机会等
    """
    # 获取关键词
    result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
    keyword = result.scalar_one_or_none()

    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    # 构建分析提示词
    analysis_prompt = f"""请分析以下关键词在情感咨询/婚姻修复领域的GEO价值和内容机会。

关键词：{keyword.keyword}

请从以下维度分析：
1. 搜索热度预估（高/中/低）
2. AI引用潜力（高/中/低）- 这个关键词被AI大模型引用的可能性
3. 竞争程度（高/中/低）
4. 内容创作机会和方向
5. 相关长尾关键词建议（5-10个）
6. 具体的内容创作建议（3-5个）

请以JSON格式返回结果：
{{
    "search_opportunity": "高/中/低",
    "ai_citation_potential": "高/中/低",
    "competition_level": "高/中/低",
    "geo_score": 0-100的评分,
    "related_keywords": ["关键词1", "关键词2", ...],
    "content_suggestions": ["建议1", "建议2", ...],
    "analysis_reasoning": "分析理由"
}}
"""

    try:
        # 调用LLM进行分析
        response = await generate_content(
            prompt=analysis_prompt,
            role="keyword_analyzer",
            temperature=0.3  # 降低温度获得更稳定的结果
        )

        # 解析JSON响应
        import json
        # 尝试提取JSON部分
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()

        analysis_data = json.loads(response)

        # 更新关键词数据
        keyword.geo_score = analysis_data.get("geo_score", 50.0)
        keyword.competition_level = analysis_data.get("competition_level", "中")
        keyword.last_analyzed_at = datetime.utcnow()
        await db.commit()

        return KeywordAnalysisResponse(
            keyword_id=keyword.id,
            keyword=keyword.keyword,
            geo_score=keyword.geo_score,
            search_opportunity=analysis_data.get("search_opportunity", "中"),
            competition_level=keyword.competition_level,
            recommendations=analysis_data.get("content_suggestions", []),
            related_keywords=analysis_data.get("related_keywords", []),
            content_suggestions=analysis_data.get("content_suggestions", [])
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"关键词分析失败: {str(e)}"
        )


@router.post("/batch-analyze", summary="批量分析关键词")
async def batch_analyze_keywords(
    request: KeywordAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """批量分析多个关键词"""
    results = []

    for keyword_id in request.keyword_ids:
        try:
            result = await analyze_keyword(keyword_id, request.deep_analysis, db)
            results.append(result)
        except Exception as e:
            results.append({
                "keyword_id": keyword_id,
                "error": str(e)
            })

    return results


# ==================== 深度研究端点 ====================


class KeywordResearchRequest(BaseModel):
    """关键词深度研究请求"""
    topic: str = Field(..., description="研究主题", min_length=1)
    brand_name: Optional[str] = Field(None, description="品牌名称")
    industry: Optional[str] = Field(None, description="行业")
    competitors: List[str] = Field(default_factory=list, description="竞品列表")


class TopicClusterRequest(BaseModel):
    """Topic Cluster 构建请求"""
    topic: str = Field(..., description="主题", min_length=1)
    keywords: List[str] = Field(default_factory=list, description="已有关键词列表")
    brand_name: Optional[str] = Field(None, description="品牌名称")
    industry: Optional[str] = Field(None, description="行业")
    max_clusters: int = Field(default=3, ge=1, le=5, description="最大聚类数")


class ContentCalendarRequest(BaseModel):
    """内容日历生成请求"""
    topic: str = Field(..., description="主题", min_length=1)
    keywords: List[str] = Field(default_factory=list, description="关键词列表")
    brand_name: Optional[str] = Field(None, description="品牌名称")
    industry: Optional[str] = Field(None, description="行业")
    weeks: int = Field(default=4, ge=1, le=12, description="规划周数")


@router.post("/research", summary="深度关键词研究")
async def keyword_research(request: KeywordResearchRequest):
    """
    执行多维关键词研究，输出趋势分析、商业关键词、长尾机会和 GEO 建议。

    融合 seo-geo-claude-skills 的 keyword-research 分析框架，
    结合本地分析引擎的关键词分类和难度评估。
    """
    brand_context = {
        "brand_name": request.brand_name or "",
        "industry": request.industry or "",
        "competitors": request.competitors,
    }

    try:
        researcher = KeywordResearcher()
        report = await researcher.research(request.topic, brand_context)
        return report.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"关键词研究失败：{str(e)}")


@router.post("/clusters", summary="构建 Topic Clusters")
async def build_topic_clusters(request: TopicClusterRequest):
    """
    基于主题和关键词构建 Topic Cluster 映射。

    生成支柱页面（Pillar Page）和集群页面（Cluster Pages）的结构化映射，
    包含内链策略建议。
    """
    brand_context = {
        "brand_name": request.brand_name or "",
        "industry": request.industry or "",
    }

    try:
        engine = TopicClusterEngine()
        result = await engine.build_clusters(
            topic=request.topic,
            keywords=request.keywords,
            brand_context=brand_context,
            max_clusters=request.max_clusters,
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Topic Cluster 构建失败：{str(e)}")


@router.post("/calendar", summary="生成内容日历")
async def generate_content_calendar(request: ContentCalendarRequest):
    """
    基于主题和关键词生成内容发布日历。

    按 P0/P1/P2 优先级排序，覆盖多平台（公众号/小红书/知乎/短视频），
    包含内容类型和简要 brief。
    """
    brand_context = {
        "brand_name": request.brand_name or "",
        "industry": request.industry or "",
    }

    try:
        generator = ContentCalendarGenerator()
        result = await generator.generate(
            topic=request.topic,
            keywords=request.keywords,
            brand_context=brand_context,
            weeks=request.weeks,
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内容日历生成失败：{str(e)}")
