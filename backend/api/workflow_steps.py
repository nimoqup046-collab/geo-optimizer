"""Workflow step CRUD + execution endpoints with real adapter dispatch."""

from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import resolve_workspace_id
from database import get_db
from models.workflow_step import WorkflowStep


router = APIRouter(prefix="/workflow-steps", tags=["workflow_steps"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

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


class StepMetrics(BaseModel):
    """Aggregated metrics for workflow steps."""
    total: int = 0
    idle: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    avg_duration_ms: float = 0.0
    total_retries: int = 0
    adapters: Dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Execution endpoint (real adapter dispatch with retry)
# ---------------------------------------------------------------------------

@router.post("/{step_id}/run", response_model=WorkflowStepResponse)
async def run_workflow_step(
    step_id: str,
    request: WorkflowStepRunRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute a workflow step using its registered adapter.

    The adapter is dispatched from the AdapterRegistry. Failed executions
    are retried with exponential backoff up to the step's retry_limit.
    """
    result = await db.execute(select(WorkflowStep).where(WorkflowStep.id == step_id))
    step = result.scalar_one_or_none()
    if not step:
        raise HTTPException(status_code=404, detail="未找到编排步骤")

    # Merge runtime payload into step's stored input
    effective_input = {**(step.input_payload or {}), **(request.payload or {})}

    step.status = "running"
    await db.flush()

    from services.workflow_executor import execute_step

    exec_result = await execute_step(
        adapter_name=step.adapter,
        input_payload=effective_input,
        config=step.config or {},
        retry_limit=step.retry_limit,
    )

    step.status = exec_result.status
    step.retry_count = exec_result.retry_count
    step.output_payload = {
        **exec_result.output_payload,
        "_meta": {
            "duration_ms": exec_result.duration_ms,
            "started_at": exec_result.started_at,
            "finished_at": exec_result.finished_at,
            "retry_count": exec_result.retry_count,
            "error": exec_result.error,
        },
    }

    await db.commit()
    await db.refresh(step)
    return step


# ---------------------------------------------------------------------------
# Metrics endpoint
# ---------------------------------------------------------------------------

@router.get("/metrics", response_model=StepMetrics)
async def get_step_metrics(
    workspace_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Return aggregated metrics for workflow steps."""
    resolved_workspace = await resolve_workspace_id(db, workspace_id)
    query = select(WorkflowStep).where(WorkflowStep.workspace_id == resolved_workspace)
    result = await db.execute(query)
    steps = list(result.scalars().all())

    counts = {"idle": 0, "running": 0, "completed": 0, "failed": 0}
    adapters: Dict[str, int] = {}
    total_retries = 0
    durations: list[float] = []

    for s in steps:
        counts[s.status] = counts.get(s.status, 0) + 1
        adapters[s.adapter] = adapters.get(s.adapter, 0) + 1
        total_retries += s.retry_count or 0
        # Extract duration from output meta
        meta = (s.output_payload or {}).get("_meta", {})
        d = meta.get("duration_ms")
        if d and isinstance(d, (int, float)):
            durations.append(d)

    avg_duration = round(sum(durations) / len(durations), 2) if durations else 0.0

    return StepMetrics(
        total=len(steps),
        idle=counts.get("idle", 0),
        running=counts.get("running", 0),
        completed=counts.get("completed", 0),
        failed=counts.get("failed", 0),
        avg_duration_ms=avg_duration,
        total_retries=total_retries,
        adapters=adapters,
    )


@router.get("/adapters", response_model=List[str])
async def list_available_adapters():
    """Return all registered adapter names."""
    from services.workflow_executor import AdapterRegistry
    return AdapterRegistry.list_adapters()
