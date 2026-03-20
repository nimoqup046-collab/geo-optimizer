from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import resolve_workspace_id
from database import get_db
from models.workflow_step import WorkflowStep


router = APIRouter(prefix="/workflow-steps", tags=["workflow_steps"])


class WorkflowStepCreateRequest(BaseModel):
    workspace_id: Optional[str] = None
    brand_id: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=160)
    step_type: str = "skill_step"
    adapter: str = "mock"
    status: str = "idle"
    retry_limit: int = Field(default=2, ge=0, le=10)
    input_payload: dict = Field(default_factory=dict)
    config: dict = Field(default_factory=dict)


class WorkflowStepUpdateRequest(BaseModel):
    name: Optional[str] = None
    step_type: Optional[str] = None
    adapter: Optional[str] = None
    status: Optional[str] = None
    retry_count: Optional[int] = None
    retry_limit: Optional[int] = None
    input_payload: Optional[dict] = None
    output_payload: Optional[dict] = None
    config: Optional[dict] = None


class WorkflowStepResponse(BaseModel):
    id: str
    workspace_id: str
    brand_id: Optional[str]
    name: str
    step_type: str
    adapter: str
    status: str
    retry_count: int
    retry_limit: int
    input_payload: dict
    output_payload: dict
    config: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowStepRunRequest(BaseModel):
    payload: dict = Field(default_factory=dict)


@router.post("", response_model=WorkflowStepResponse)
async def create_workflow_step(
    request: WorkflowStepCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    workspace_id = await resolve_workspace_id(db, request.workspace_id)
    step = WorkflowStep(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        brand_id=request.brand_id,
        name=request.name,
        step_type=request.step_type,
        adapter=request.adapter,
        status=request.status,
        retry_limit=request.retry_limit,
        input_payload=request.input_payload,
        config=request.config,
        output_payload={},
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


@router.post("/{step_id}/run", response_model=WorkflowStepResponse)
async def run_workflow_step(
    step_id: str,
    request: WorkflowStepRunRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WorkflowStep).where(WorkflowStep.id == step_id))
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="未找到编排步骤")

    step.status = "running"
    await db.flush()

    # V1 mock adapter placeholder. Real skill adapters can be wired here later.
    mock_output = {
        "adapter": step.adapter,
        "status": "mock_completed",
        "input_payload": request.payload or step.input_payload or {},
        "message": "Mock 适配器执行成功。",
    }
    step.output_payload = mock_output
    step.status = "completed"
    step.retry_count = 0

    await db.commit()
    await db.refresh(step)
    return step


@router.get("", response_model=List[WorkflowStepResponse])
async def list_workflow_steps(
    workspace_id: Optional[str] = None,
    brand_id: Optional[str] = None,
    step_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    resolved_workspace = await resolve_workspace_id(db, workspace_id)
    query = select(WorkflowStep).where(WorkflowStep.workspace_id == resolved_workspace)
    if brand_id:
        query = query.where(WorkflowStep.brand_id == brand_id)
    if step_type:
        query = query.where(WorkflowStep.step_type == step_type)
    result = await db.execute(query.order_by(WorkflowStep.updated_at.desc()))
    return list(result.scalars().all())


@router.patch("/{step_id}", response_model=WorkflowStepResponse)
async def update_workflow_step(
    step_id: str,
    request: WorkflowStepUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WorkflowStep).where(WorkflowStep.id == step_id))
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="未找到编排步骤")

    for key, value in request.model_dump(exclude_none=True).items():
        setattr(step, key, value)

    await db.commit()
    await db.refresh(step)
    return step
