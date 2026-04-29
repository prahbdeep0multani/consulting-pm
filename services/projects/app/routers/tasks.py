import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from shared.core.exceptions import NotFoundError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_tenant_id_dep, get_current_user_id
from ..repositories.project_repo import CommentRepository, TaskRepository
from ..schemas.project import CommentCreate, CommentResponse, TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(tags=["tasks"])


@router.get("/projects/{project_id}/tasks", response_model=list[TaskResponse])
async def list_tasks(
    project_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    status: str | None = None,
    assignee_id: uuid.UUID | None = None,
) -> list[Any]:
    repo = TaskRepository(session)
    return await repo.list(project_id, status, assignee_id, parent_only=True)  # type: ignore[no-any-return]


@router.post("/projects/{project_id}/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    project_id: uuid.UUID,
    body: TaskCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
) -> object:
    repo = TaskRepository(session)
    task = await repo.create(project_id=project_id, reporter_user_id=user_id, **body.model_dump())
    await session.commit()
    return task


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    repo = TaskRepository(session)
    task = await repo.get(task_id)
    if not task:
        raise NotFoundError("Task not found")
    return task


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    repo = TaskRepository(session)
    task = await repo.get(task_id)
    if not task:
        raise NotFoundError("Task not found")
    updates = body.model_dump(exclude_none=True)
    if updates.get("status") == "done" and task.status != "done":
        updates["completed_at"] = datetime.now(UTC)
    updated = await repo.update(task, **updates)
    await session.commit()
    return updated


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> None:
    repo = TaskRepository(session)
    task = await repo.get(task_id)
    if not task:
        raise NotFoundError("Task not found")
    await repo.soft_delete(task)
    await session.commit()


@router.get("/tasks/{task_id}/subtasks", response_model=list[TaskResponse])
async def list_subtasks(
    task_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> list[Any]:
    repo = TaskRepository(session)
    task = await repo.get(task_id)
    if not task:
        raise NotFoundError("Task not found")
    result = await repo.list(task.project_id)
    return [t for t in result if t.parent_task_id == task_id]


# ── Comments ─────────────────────────────────────────────────────────────────


@router.get("/tasks/{task_id}/comments", response_model=list[CommentResponse])
async def list_comments(
    task_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> list[Any]:
    repo = CommentRepository(session)
    return await repo.list(task_id)  # type: ignore[no-any-return]


@router.post("/tasks/{task_id}/comments", response_model=CommentResponse, status_code=201)
async def create_comment(
    task_id: uuid.UUID,
    body: CommentCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
) -> object:
    repo = CommentRepository(session)
    comment = await repo.create(task_id, user_id, body.body)
    await session.commit()
    return comment


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> None:
    repo = CommentRepository(session)
    comment = await repo.get(comment_id)
    if not comment:
        raise NotFoundError("Comment not found")
    await repo.soft_delete(comment)
    await session.commit()
