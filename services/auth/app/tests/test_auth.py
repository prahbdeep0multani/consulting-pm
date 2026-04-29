import pytest
from httpx import AsyncClient


@pytest.fixture()  # type: ignore[untyped-decorator]
async def registered_tenant(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/tenants",
        json={
            "slug": "auth-test-corp",
            "name": "Auth Test Corp",
            "plan": "starter",
            "admin_email": "admin@auth-test.com",
            "admin_password": "Securepass123!",
            "admin_full_name": "Auth Admin",
        },
    )
    assert response.status_code == 201
    return {"slug": "auth-test-corp", "email": "admin@auth-test.com", "password": "Securepass123!"}


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_login_success(client: AsyncClient, registered_tenant: dict[str, str]) -> None:
    response = await client.post(
        "/auth/login",
        json={
            "tenant_slug": registered_tenant["slug"],
            "email": registered_tenant["email"],
            "password": registered_tenant["password"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_login_wrong_password(client: AsyncClient, registered_tenant: dict[str, str]) -> None:
    response = await client.post(
        "/auth/login",
        json={
            "tenant_slug": registered_tenant["slug"],
            "email": registered_tenant["email"],
            "password": "wrong_password",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_refresh_token_rotation(
    client: AsyncClient, registered_tenant: dict[str, str]
) -> None:
    login_resp = await client.post(
        "/auth/login",
        json={
            "tenant_slug": registered_tenant["slug"],
            "email": registered_tenant["email"],
            "password": registered_tenant["password"],
        },
    )
    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = await client.post(
        "/auth/refresh",
        json={
            "tenant_slug": registered_tenant["slug"],
            "refresh_token": refresh_token,
        },
    )
    assert refresh_resp.status_code == 200
    new_refresh = refresh_resp.json()["refresh_token"]
    assert new_refresh != refresh_token

    # Old refresh token must be rejected
    reuse_resp = await client.post(
        "/auth/refresh",
        json={
            "tenant_slug": registered_tenant["slug"],
            "refresh_token": refresh_token,
        },
    )
    assert reuse_resp.status_code == 401


@pytest.mark.asyncio  # type: ignore[untyped-decorator]
async def test_tenant_isolation(client: AsyncClient) -> None:
    """Users from tenant A cannot log in with tenant B's slug."""
    await client.post(
        "/tenants",
        json={
            "slug": "tenant-a",
            "name": "Tenant A",
            "plan": "starter",
            "admin_email": "admin@tenant-a.com",
            "admin_password": "Securepass123!",
            "admin_full_name": "Admin A",
        },
    )
    await client.post(
        "/tenants",
        json={
            "slug": "tenant-b",
            "name": "Tenant B",
            "plan": "starter",
            "admin_email": "admin@tenant-b.com",
            "admin_password": "Securepass123!",
            "admin_full_name": "Admin B",
        },
    )
    # Tenant A's email + password against Tenant B's slug
    response = await client.post(
        "/auth/login",
        json={
            "tenant_slug": "tenant-b",
            "email": "admin@tenant-a.com",
            "password": "Securepass123!",
        },
    )
    assert response.status_code == 401
