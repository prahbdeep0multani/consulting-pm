import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.exceptions import NotFoundError, UnprocessableError

from ..database import get_session
from ..dependencies import get_current_tenant_id_dep, get_current_user_id
from ..repositories.project_repo import AttachmentRepository
from ..schemas.project import (
    AttachmentConfirm,
    AttachmentResponse,
    AttachmentUploadRequest,
    PresignedUploadResponse,
)

router = APIRouter(tags=["attachments"])


def get_storage():
    from ..main import storage
    return storage


@router.post("/attachments/upload", response_model=PresignedUploadResponse)
async def initiate_upload(
    body: AttachmentUploadRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    tid: Annotated[uuid.UUID, Depends(get_current_tenant_id_dep)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
) -> object:
    s = get_storage()
    attachment_id = uuid.uuid4()
    object_key = s.make_object_key(tid, attachment_id, body.filename)

    upload_url = await s.generate_presigned_put_url(object_key, body.content_type, expire_seconds=300)

    # Create a pending attachment record
    repo = AttachmentRepository(session)
    await repo.create(
        uploaded_by=user_id,
        id=attachment_id,
        filename=body.filename,
        content_type=body.content_type,
        size_bytes=body.size_bytes,
        storage_key=object_key,
        storage_bucket=s._bucket,
        task_id=body.task_id,
        project_id=body.project_id,
    )
    await session.commit()

    return PresignedUploadResponse(upload_url=upload_url, attachment_id=attachment_id)


@router.post("/attachments", response_model=AttachmentResponse, status_code=201)
async def confirm_upload(
    body: AttachmentConfirm,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    repo = AttachmentRepository(session)
    attachment = await repo.get(body.attachment_id)
    if not attachment:
        raise NotFoundError("Attachment not found")

    s = get_storage()
    if not await s.object_exists(attachment.storage_key):
        raise UnprocessableError("File not found in storage — upload may have failed")

    if body.checksum_sha256:
        attachment.checksum_sha256 = body.checksum_sha256
    await session.commit()
    return AttachmentResponse(
        id=attachment.id,
        tenant_id=attachment.tenant_id,
        filename=attachment.filename,
        content_type=attachment.content_type,
        size_bytes=attachment.size_bytes,
        task_id=attachment.task_id,
        project_id=attachment.project_id,
        uploaded_by=attachment.uploaded_by,
        created_at=attachment.created_at,
    )


@router.get("/attachments/{attachment_id}", response_model=AttachmentResponse)
async def get_attachment(
    attachment_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    repo = AttachmentRepository(session)
    a = await repo.get(attachment_id)
    if not a:
        raise NotFoundError("Attachment not found")
    s = get_storage()
    download_url = await s.generate_presigned_get_url(a.storage_key)
    return AttachmentResponse(
        id=a.id, tenant_id=a.tenant_id, filename=a.filename,
        content_type=a.content_type, size_bytes=a.size_bytes,
        task_id=a.task_id, project_id=a.project_id, uploaded_by=a.uploaded_by,
        created_at=a.created_at, download_url=download_url,
    )


@router.delete("/attachments/{attachment_id}", status_code=204)
async def delete_attachment(
    attachment_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> None:
    repo = AttachmentRepository(session)
    a = await repo.get(attachment_id)
    if not a:
        raise NotFoundError("Attachment not found")
    s = get_storage()
    await s.delete_object(a.storage_key)
    await repo.soft_delete(a)
    await session.commit()
