from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    # Import models to register metadata.
    from models.account import PlatformAccount  # noqa: F401
    from models.brand import BrandProfile  # noqa: F401
    from models.content import ContentItem, ContentVariant  # noqa: F401
    from models.keyword_topic import KeywordTopic  # noqa: F401
    from models.performance import OptimizationInsight, PerformanceSnapshot  # noqa: F401
    from models.prompt_profile import PromptProfile  # noqa: F401
    from models.publish_task import PublishTask  # noqa: F401
    from models.report import AnalysisReport  # noqa: F401
    from models.source_asset import SourceAsset  # noqa: F401
    from models.workflow_step import WorkflowStep  # noqa: F401
    from models.ranking import RankingSnapshot  # noqa: F401
    from models.workspace import Workspace  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
