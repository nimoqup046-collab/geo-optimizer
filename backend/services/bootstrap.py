from sqlalchemy import select

from database import async_session_maker
from models.workspace import Workspace


DEFAULT_WORKSPACE_NAME = "default"


async def ensure_default_workspace() -> str:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Workspace).where(Workspace.name == DEFAULT_WORKSPACE_NAME)
        )
        workspace = result.scalar_one_or_none()
        if workspace:
            return workspace.id

        workspace = Workspace(name=DEFAULT_WORKSPACE_NAME)
        session.add(workspace)
        await session.commit()
        await session.refresh(workspace)
        return workspace.id
