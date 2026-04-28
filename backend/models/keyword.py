"""
关键词数据模型
"""
from sqlalchemy import String, Integer, Float, JSON, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database import Base
import uuid

_utcnow = lambda: datetime.utcnow()


class KeywordCategory:
    """关键词分类"""
    BRAND = "brand"  # 品牌词
    INDUSTRY = "industry"  # 行业词
    LONG_TAIL = "long_tail"  # 长尾词
    COMPETITOR = "competitor"  # 竞品词


class Keyword(Base):
    """关键词模型"""

    __tablename__ = "keywords"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    keyword: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default=KeywordCategory.INDUSTRY)

    # 搜索数据
    search_volume: Mapped[int] = mapped_column(Integer, default=0)  # 搜索量
    trend: Mapped[dict] = mapped_column(JSON, default=list)  # 趋势数据

    # GEO评分
    geo_score: Mapped[float] = mapped_column(Float, default=0.0)  # GEO权重评分 0-100
    competition_level: Mapped[str] = mapped_column(String(50), default="中")  # 竞争程度

    # 分析数据
    ai_references: Mapped[int] = mapped_column(Integer, default=0)  # AI引用次数
    platform_coverage: Mapped[dict] = mapped_column(JSON, default=dict)  # 平台覆盖情况

    # 状态
    recommended: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否推荐
    active: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否激活

    # 关联内容
    generated_content_count: Mapped[int] = mapped_column(Integer, default=0)  # 已生成内容数量

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    last_analyzed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # 最后分析时间

    # 备注
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Keyword(id={self.id}, keyword={self.keyword}, category={self.category})>"
