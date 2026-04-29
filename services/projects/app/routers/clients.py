import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from shared.core.exceptions import NotFoundError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_tenant_id_dep
from ..repositories.project_repo import ClientRepository
from ..schemas.project import ClientCreate, ClientResponse, ClientUpdate

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientResponse])
async def list_clients(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    limit: int = 20,
    offset: int = 0,
) -> list[Any]:
    repo = ClientRepository(session)
    return await repo.list(limit, offset)  # type: ignore[no-any-return]


@router.post("", response_model=ClientResponse, status_code=201)
async def create_client(
    body: ClientCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    repo = ClientRepository(session)
    client = await repo.create(**body.model_dump())
    await session.commit()
    return client


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    repo = ClientRepository(session)
    client = await repo.get(client_id)
    if not client:
        raise NotFoundError("Client not found")
    return client


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: uuid.UUID,
    body: ClientUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    repo = ClientRepository(session)
    client = await repo.get(client_id)
    if not client:
        raise NotFoundError("Client not found")
    updated = await repo.update(client, **body.model_dump(exclude_none=True))
    await session.commit()
    return updated


@router.delete("/{client_id}", status_code=204)
async def delete_client(
    client_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> None:
    repo = ClientRepository(session)
    client = await repo.get(client_id)
    if not client:
        raise NotFoundError("Client not found")
    await repo.soft_delete(client)
    await session.commit()
