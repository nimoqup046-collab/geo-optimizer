"""
内容生成相关API
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
import json

from database import get_db
from models.keyword import Keyword
from models.content import GeneratedContent, Platform, ContentStatus
from services.llm_service import generate_content
from services.template_manager import format_generation_prompt, get_template_manager
from config import settings


router = APIRouter(prefix="/content", tags=["内容生成"])


# ==================== 请求/响应模型 ====================

class ContentGenerateRequest(BaseModel):
    """内容生成请求"""
    keyword_id: str = Field(..., description="关键词ID")
    platform: str = Field(..., description="平台: xiaohongshu/wechat/zhihu/video")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词")
    llm_provider: Optional[str] = Field(None, description="LLM服务商")
    count: int = Field(default=1, description="生成数量", ge=1, le=5)


class ContentUpdateRequest(BaseModel):
    """内容更新请求"""
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    manual_edited: Optional[bool] = None
    editor_notes: Optional[str] = None


class ContentResponse(BaseModel):
    """内容响应"""
    id: str
    keyword_id: Optional[str]
    platform: str
    title: str
    content: str
    summary: Optional[str]
    tags: List[str]
    category: Optional[str]
    status: str
    llm_provider: Optional[str]
    llm_model: Optional[str]
    manual_edited: bool
    quality_score: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContentExportRequest(BaseModel):
    """内容导出请求"""
    content_ids: List[str] = Field(..., description="要导出的内容ID列表")
    format: str = Field(default="md", description="导出格式: md/pdf/html")


# ==================== API端点 ====================

@router.post("/generate", response_model=List[ContentResponse], summary="生成内容")
async def generate_content_endpoint(
    request: ContentGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    根据关键词生成指定平台的内容

    支持平台：
    - xiaohongshu: 小红书笔记
    - wechat: 公众号文章
    - zhihu: 知乎回答
    - video: 短视频脚本
    """
    # 验证平台
    valid_platforms = ["xiaohongshu", "wechat", "zhihu", "video"]
    if request.platform not in valid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的平台，请选择: {', '.join(valid_platforms)}"
        )

    # 获取关键词
    result = await db.execute(select(Keyword).where(Keyword.id == request.keyword_id))
    keyword = result.scalar_one_or_none()

    if not keyword:
        raise HTTPException(status_code=404, detail="关键词不存在")

    # 获取模板管理器
    template_mgr = get_template_manager()

    generated_contents = []

    for i in range(request.count):
        try:
            # 构建生成提示词
            if request.custom_prompt:
                prompt = request.custom_prompt
            else:
                prompt = format_generation_prompt(
                    platform=request.platform,
                    keyword=keyword.keyword
                )

            # 根据平台选择角色
            role_map = {
                "xiaohongshu": "xiaohongshu_specialist",
                "wechat": "wechat_specialist",
                "zhihu": "zhihu_specialist",
                "video": "video_script_specialist"
            }
            role = role_map.get(request.platform, "content_generator")

            # 调用LLM生成
            content_text = await generate_content(
                prompt=prompt,
                role=role,
                provider=request.llm_provider,
                context={"keyword": keyword.keyword, "platform": request.platform},
                temperature=0.8,
                max_tokens=3000
            )

            # 解析生成的内容
            title, body = _parse_generated_content(content_text, request.platform)

            # 保存到数据库
            generated = GeneratedContent(
                id=str(uuid.uuid4()),
                keyword_id=keyword.id,
                platform=request.platform,
                title=title,
                content=body,
                summary=content_text[:200] if len(content_text) > 200 else content_text,
                tags=_extract_tags(content_text, request.platform),
                llm_provider=request.llm_provider or settings.DEFAULT_LLM_PROVIDER,
                status=ContentStatus.DRAFT
            )

            db.add(generated)

            # 更新关键词的生成内容计数
            keyword.generated_content_count += 1

            generated_contents.append(generated)

        except Exception as e:
            # 记录错误但继续生成其他内容
            print(f"生成失败: {str(e)}")
            continue

    await db.commit()

    # 刷新获取完整数据
    for content in generated_contents:
        await db.refresh(content)

    return generated_contents


@router.get("", response_model=List[ContentResponse], summary="获取内容列表")
async def get_contents(
    keyword_id: Optional[str] = None,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """获取生成的内容列表，支持筛选和分页"""
    query = select(GeneratedContent)

    if keyword_id:
        query = query.where(GeneratedContent.keyword_id == keyword_id)
    if platform:
        query = query.where(GeneratedContent.platform == platform)
    if status:
        query = query.where(GeneratedContent.status == status)

    query = query.order_by(GeneratedContent.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{content_id}", response_model=ContentResponse, summary="获取内容详情")
async def get_content(
    content_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取单个内容详情"""
    result = await db.execute(select(GeneratedContent).where(GeneratedContent.id == content_id))
    content = result.scalar_one_or_none()

    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")

    return content


@router.put("/{content_id}", response_model=ContentResponse, summary="更新内容")
async def update_content(
    content_id: str,
    request: ContentUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """更新内容（人工编辑）"""
    result = await db.execute(select(GeneratedContent).where(GeneratedContent.id == content_id))
    content = result.scalar_one_or_none()

    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")

    # 更新字段
    if request.title is not None:
        content.title = request.title
    if request.content is not None:
        content.content = request.content
    if request.summary is not None:
        content.summary = request.summary
    if request.tags is not None:
        content.tags = request.tags
    if request.category is not None:
        content.category = request.category
    if request.manual_edited is not None:
        content.manual_edited = request.manual_edited
    if request.editor_notes is not None:
        content.editor_notes = request.editor_notes

    await db.commit()
    await db.refresh(content)

    return content


@router.delete("/{content_id}", summary="删除内容")
async def delete_content(
    content_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除内容"""
    result = await db.execute(select(GeneratedContent).where(GeneratedContent.id == content_id))
    content = result.scalar_one_or_none()

    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")

    await db.delete(content)
    await db.commit()

    return {"message": "删除成功"}


@router.post("/{content_id}/approve", response_model=ContentResponse, summary="审核通过")
async def approve_content(
    content_id: str,
    db: AsyncSession = Depends(get_db)
):
    """审核通过内容，标记为可发布"""
    result = await db.execute(select(GeneratedContent).where(GeneratedContent.id == content_id))
    content = result.scalar_one_or_none()

    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")

    content.status = ContentStatus.APPROVED
    await db.commit()
    await db.refresh(content)

    return content


@router.post("/export", summary="导出内容")
async def export_contents(
    request: ContentExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """导出内容为指定格式"""
    # 获取要导出的内容
    query = select(GeneratedContent).where(GeneratedContent.id.in_(request.content_ids))
    result = await db.execute(query)
    contents = result.scalars().all()

    if not contents:
        raise HTTPException(status_code=404, detail="未找到要导出的内容")

    # 根据格式导出
    if request.format == "md":
        return _export_markdown(contents)
    elif request.format == "html":
        return _export_html(contents)
    elif request.format == "json":
        return _export_json(contents)
    else:
        raise HTTPException(status_code=400, detail="不支持的导出格式")


# ==================== 辅助函数 ====================

def _parse_generated_content(content_text: str, platform: str) -> tuple[str, str]:
    """
    解析生成的内容，提取标题和正文

    Args:
        content_text: 生成的内容
        platform: 平台类型

    Returns:
        (标题, 正文)
    """
    # 尝试提取标题（如果是markdown格式）
    lines = content_text.strip().split('\n')

    title = ""
    body = content_text

    # 查找第一个#标题
    for i, line in enumerate(lines):
        if line.strip().startswith('#'):
            title = line.strip().lstrip('#').strip()
            body = '\n'.join(lines[i+1:]) if i+1 < len(lines) else ""
            break

    # 如果没找到标题，使用第一行作为标题
    if not title and lines:
        title = lines[0].strip()
        body = '\n'.join(lines[1:]) if len(lines) > 1 else ""

    # 如果仍然没有标题，生成一个
    if not title:
        title = f"【{platform}】生成内容"

    return title, body


def _extract_tags(content_text: str, platform: str) -> List[str]:
    """
    从内容中提取标签

    Args:
        content_text: 内容文本
        platform: 平台类型

    Returns:
        标签列表
    """
    tags = []

    # 从内容中提取#标签
    import re
    hashtags = re.findall(r'#(\w+)', content_text)
    tags.extend([f"#{tag}" for tag in hashtags])

    # 根据平台添加默认标签
    default_tags = {
        "xiaohongshu": ["#婚姻修复", "#情感心理", "#亲密关系"],
        "wechat": [],
        "zhihu": ["婚姻修复", "情感咨询"],
        "video": ["#情感", "#婚姻"]
    }

    if not tags:
        tags = default_tags.get(platform, [])

    return tags


def _export_markdown(contents: List[GeneratedContent]) -> dict:
    """导出为Markdown格式"""
    md_content = "# 爱归心理 - 内容导出\n\n"
    md_content += f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    md_content += "---\n\n"

    for content in contents:
        platform_name = {
            "xiaohongshu": "小红书",
            "wechat": "公众号",
            "zhihu": "知乎",
            "video": "视频脚本"
        }.get(content.platform, content.platform)

        md_content += f"## [{platform_name}] {content.title}\n\n"
        md_content += f"**平台**: {platform_name}\n\n"
        md_content += f"**生成时间**: {content.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        if content.tags:
            md_content += f"**标签**: {' '.join(content.tags)}\n\n"

        md_content += "### 正文\n\n"
        md_content += content.content
        md_content += "\n\n---\n\n"

    return {
        "filename": f"geo_content_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
        "content": md_content,
        "content_type": "text/markdown"
    }


def _export_html(contents: List[GeneratedContent]) -> dict:
    """导出为HTML格式"""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>爱归心理 - 内容导出</title>
    <style>
        body { font-family: 'Microsoft YaHei', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        .content-item { border: 1px solid #eee; padding: 20px; margin: 20px 0; border-radius: 8px; }
        .platform-tag { display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; margin-right: 8px; }
        .tag-xiaohongshu { background: #ff2442; color: white; }
        .tag-wechat { background: #07c160; color: white; }
        .tag-zhihu { background: #0084ff; color: white; }
        .tag-video { background: #000; color: white; }
        .tags { margin: 10px 0; }
        .meta { color: #999; font-size: 14px; }
    </style>
</head>
<body>
    <h1>爱归心理 - 内容导出</h1>
    <p class="meta">导出时间: {timestamp}</p>
"""

    html_content = html_content.replace("{timestamp}", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    for content in contents:
        platform_name = {
            "xiaohongshu": "小红书",
            "wechat": "公众号",
            "zhihu": "知乎",
            "video": "视频脚本"
        }.get(content.platform, content.platform)

        html_content += f"""
    <div class="content-item">
        <span class="platform-tag tag-{content.platform}">{platform_name}</span>
        <h2>{content.title}</h2>
        <p class="meta">生成时间: {content.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
"""

        if content.tags:
            tags_html = " ".join([f'<span style="background:#f0f0f0;padding:4px 8px;border-radius:4px;font-size:12px;margin-right:4px;">{tag}</span>' for tag in content.tags])
            html_content += f'        <div class="tags">{tags_html}</div>\n'

        html_content += f"""
        <div class="content-body">
            {content.content.replace(chr(10), '<br>')}
        </div>
    </div>
"""

    html_content += """
</body>
</html>
"""

    return {
        "filename": f"geo_content_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
        "content": html_content,
        "content_type": "text/html"
    }


def _export_json(contents: List[GeneratedContent]) -> dict:
    """导出为JSON格式"""
    data = []
    for content in contents:
        data.append({
            "id": content.id,
            "platform": content.platform,
            "title": content.title,
            "content": content.content,
            "tags": content.tags,
            "created_at": content.created_at.isoformat()
        })

    return {
        "filename": f"geo_content_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        "content": json.dumps(data, ensure_ascii=False, indent=2),
        "content_type": "application/json"
    }
