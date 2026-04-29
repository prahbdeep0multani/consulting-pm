import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from shared.core.exceptions import NotFoundError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_tenant_id_dep, get_current_user_id
from ..repositories.project_repo import MilestoneRepository, ProjectRepository
from ..schemas.project import (
    MilestoneCreate,
    MilestoneResponse,
    MilestoneUpdate,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    status: str | None = None,
    client_id: uuid.UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Any]:
    repo = ProjectRepository(session)
    return await repo.list(limit, offset, status, client_id)  # type: ignore[return-value]


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
) -> object:
    repo = ProjectRepository(session)
    project = await repo.create(manager_user_id=user_id, **body.model_dump())
    await session.commit()
    return project


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    repo = ProjectRepository(session)
    project = await repo.get(project_id)
    if not project:
        raise NotFoundError("Project not found")
    return project


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    repo = ProjectRepository(session)
    project = await repo.get(project_id)
    if not project:
        raise NotFoundError("Project not found")
    updated = await repo.update(project, **body.model_dump(exclude_none=True))
    await session.commit()
    return updated


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> None:
    repo = ProjectRepository(session)
    project = await repo.get(project_id)
    if not project:
        raise NotFoundError("Project not found")
    await repo.soft_delete(project)
    await session.commit()


# ── Milestones ───────────────────────────────────────────────────────────────


@router.get("/projects/{project_id}/milestones", response_model=list[MilestoneResponse])
async def list_milestones(
    project_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> list[Any]:
    repo = MilestoneRepository(session)
    return await repo.list(project_id)  # type: ignore[return-value]


@router.post("/projects/{project_id}/milestones", response_model=MilestoneResponse, status_code=201)
async def create_milestone(
    project_id: uuid.UUID,
    body: MilestoneCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    proj_repo = ProjectRepository(session)
    if not await proj_repo.get(project_id):
        raise NotFoundError("Project not found")
    repo = MilestoneRepository(session)
    ms = await repo.create(project_id=project_id, **body.model_dump())
    await session.commit()
    return ms


@router.patch("/projects/{project_id}/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    project_id: uuid.UUID,
    milestone_id: uuid.UUID,
    body: MilestoneUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    repo = MilestoneRepository(session)
    ms = await repo.get(milestone_id)
    if not ms or ms.project_id != project_id:
        raise NotFoundError("Milestone not found")
    updated = await repo.update(ms, **body.model_dump(exclude_none=True))
    await session.commit()
    return updated


@router.delete("/projects/{project_id}/milestones/{milestone_id}", status_code=204)
async def delete_milestone(
    project_id: uuid.UUID,
    milestone_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> None:
    repo = MilestoneRepository(session)
    ms = await repo.get(milestone_id)
    if not ms or ms.project_id != project_id:
        raise NotFoundError("Milestone not found")
    await repo.soft_delete(ms)
    await session.commit()
