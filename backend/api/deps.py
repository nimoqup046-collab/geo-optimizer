from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.workspace import Workspace
from services.bootstrap import DEFAULT_WORKSPACE_NAME


async def resolve_workspace_id(db: AsyncSession, workspace_id: str | None = None) -> str:
    if workspace_id:
        return workspace_id

    result = await db.execute(
        select(Workspace).where(Workspace.name == DEFAULT_WORKSPACE_NAME)
    )
    workspace = result.scalar_one_or_none()
    if workspace:
        return workspace.id
    workspace = Workspace(name=DEFAULT_WORKSPACE_NAME)
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace.id
