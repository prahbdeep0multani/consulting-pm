import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.models.base import get_current_tenant_id

from ..models.project import Attachment, Client, Comment, Milestone, Project, Task


class ClientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(self, **kwargs: object) -> Client:
        obj = Client(tenant_id=get_current_tenant_id(), **kwargs)
        self._s.add(obj)
        await self._s.flush()
        return obj

    async def get(self, client_id: uuid.UUID) -> Client | None:
        result = await self._s.execute(
            select(Client).where(Client.id == client_id, Client.tenant_id == get_current_tenant_id(), Client.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list(self, limit: int = 20, offset: int = 0) -> list[Client]:
        result = await self._s.execute(
            select(Client).where(Client.tenant_id == get_current_tenant_id(), Client.deleted_at.is_(None)).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def update(self, obj: Client, **kwargs: object) -> Client:
        for k, v in kwargs.items():
            setattr(obj, k, v)
        obj.updated_at = datetime.now(timezone.utc)
        await self._s.flush()
        return obj

    async def soft_delete(self, obj: Client) -> None:
        obj.deleted_at = datetime.now(timezone.utc)
        await self._s.flush()


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(self, **kwargs: object) -> Project:
        obj = Project(tenant_id=get_current_tenant_id(), **kwargs)
        self._s.add(obj)
        await self._s.flush()
        return obj

    async def get(self, project_id: uuid.UUID) -> Project | None:
        result = await self._s.execute(
            select(Project).where(Project.id == project_id, Project.tenant_id == get_current_tenant_id(), Project.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list(self, limit: int = 20, offset: int = 0, status: str | None = None, client_id: uuid.UUID | None = None) -> list[Project]:
        q = select(Project).where(Project.tenant_id == get_current_tenant_id(), Project.deleted_at.is_(None))
        if status:
            q = q.where(Project.status == status)
        if client_id:
            q = q.where(Project.client_id == client_id)
        result = await self._s.execute(q.limit(limit).offset(offset))
        return list(result.scalars().all())

    async def update(self, obj: Project, **kwargs: object) -> Project:
        for k, v in kwargs.items():
            setattr(obj, k, v)
        obj.updated_at = datetime.now(timezone.utc)
        await self._s.flush()
        return obj

    async def soft_delete(self, obj: Project) -> None:
        obj.deleted_at = datetime.now(timezone.utc)
        await self._s.flush()


class MilestoneRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(self, project_id: uuid.UUID, **kwargs: object) -> Milestone:
        obj = Milestone(tenant_id=get_current_tenant_id(), project_id=project_id, **kwargs)
        self._s.add(obj)
        await self._s.flush()
        return obj

    async def get(self, milestone_id: uuid.UUID) -> Milestone | None:
        result = await self._s.execute(
            select(Milestone).where(Milestone.id == milestone_id, Milestone.tenant_id == get_current_tenant_id(), Milestone.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list(self, project_id: uuid.UUID) -> list[Milestone]:
        result = await self._s.execute(
            select(Milestone).where(Milestone.project_id == project_id, Milestone.tenant_id == get_current_tenant_id(), Milestone.deleted_at.is_(None))
        )
        return list(result.scalars().all())

    async def update(self, obj: Milestone, **kwargs: object) -> Milestone:
        for k, v in kwargs.items():
            setattr(obj, k, v)
        await self._s.flush()
        return obj

    async def soft_delete(self, obj: Milestone) -> None:
        obj.deleted_at = datetime.now(timezone.utc)
        await self._s.flush()


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(self, project_id: uuid.UUID, reporter_user_id: uuid.UUID, **kwargs: object) -> Task:
        obj = Task(tenant_id=get_current_tenant_id(), project_id=project_id, reporter_user_id=reporter_user_id, **kwargs)
        self._s.add(obj)
        await self._s.flush()
        return obj

    async def get(self, task_id: uuid.UUID) -> Task | None:
        result = await self._s.execute(
            select(Task).where(Task.id == task_id, Task.tenant_id == get_current_tenant_id(), Task.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list(self, project_id: uuid.UUID, status: str | None = None, assignee_id: uuid.UUID | None = None, parent_only: bool = False) -> list[Task]:
        q = select(Task).where(Task.project_id == project_id, Task.tenant_id == get_current_tenant_id(), Task.deleted_at.is_(None))
        if status:
            q = q.where(Task.status == status)
        if assignee_id:
            q = q.where(Task.assignee_user_id == assignee_id)
        if parent_only:
            q = q.where(Task.parent_task_id.is_(None))
        result = await self._s.execute(q.order_by(Task.position))
        return list(result.scalars().all())

    async def update(self, obj: Task, **kwargs: object) -> Task:
        for k, v in kwargs.items():
            setattr(obj, k, v)
        obj.updated_at = datetime.now(timezone.utc)
        await self._s.flush()
        return obj

    async def soft_delete(self, obj: Task) -> None:
        obj.deleted_at = datetime.now(timezone.utc)
        await self._s.flush()


class CommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(self, task_id: uuid.UUID, author_user_id: uuid.UUID, body: str) -> Comment:
        obj = Comment(tenant_id=get_current_tenant_id(), task_id=task_id, author_user_id=author_user_id, body=body)
        self._s.add(obj)
        await self._s.flush()
        return obj

    async def get(self, comment_id: uuid.UUID) -> Comment | None:
        result = await self._s.execute(
            select(Comment).where(Comment.id == comment_id, Comment.tenant_id == get_current_tenant_id(), Comment.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list(self, task_id: uuid.UUID) -> list[Comment]:
        result = await self._s.execute(
            select(Comment).where(Comment.task_id == task_id, Comment.tenant_id == get_current_tenant_id(), Comment.deleted_at.is_(None)).order_by(Comment.created_at)
        )
        return list(result.scalars().all())

    async def soft_delete(self, obj: Comment) -> None:
        obj.deleted_at = datetime.now(timezone.utc)
        await self._s.flush()


class AttachmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(self, uploaded_by: uuid.UUID, **kwargs: object) -> Attachment:
        obj = Attachment(tenant_id=get_current_tenant_id(), uploaded_by=uploaded_by, **kwargs)
        self._s.add(obj)
        await self._s.flush()
        return obj

    async def get(self, attachment_id: uuid.UUID) -> Attachment | None:
        result = await self._s.execute(
            select(Attachment).where(Attachment.id == attachment_id, Attachment.tenant_id == get_current_tenant_id(), Attachment.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_for_task(self, task_id: uuid.UUID) -> list[Attachment]:
        result = await self._s.execute(
            select(Attachment).where(Attachment.task_id == task_id, Attachment.tenant_id == get_current_tenant_id(), Attachment.deleted_at.is_(None))
        )
        return list(result.scalars().all())

    async def list_for_project(self, project_id: uuid.UUID) -> list[Attachment]:
        result = await self._s.execute(
            select(Attachment).where(Attachment.project_id == project_id, Attachment.tenant_id == get_current_tenant_id(), Attachment.deleted_at.is_(None))
        )
        return list(result.scalars().all())

    async def soft_delete(self, obj: Attachment) -> None:
        obj.deleted_at = datetime.now(timezone.utc)
        await self._s.flush()
