import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_tenant(client: AsyncClient) -> None:
    response = await client.post("/tenants", json={
        "slug": "test-corp",
        "name": "Test Corporation",
        "plan": "starter",
        "admin_email": "admin@test-corp.com",
        "admin_password": "Securepass123!",
        "admin_full_name": "Admin User",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "test-corp"
    assert data["name"] == "Test Corporation"


@pytest.mark.asyncio
async def test_duplicate_slug_rejected(client: AsyncClient) -> None:
    payload = {
        "slug": "dup-corp",
        "name": "Dup Corp",
        "plan": "starter",
        "admin_email": "admin@dup.com",
        "admin_password": "Securepass123!",
        "admin_full_name": "Admin",
    }
    await client.post("/tenants", json=payload)
    response = await client.post("/tenants", json=payload)
    assert response.status_code == 409
