from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse


def create_health_router(
    service_name: str,
    readiness_checks: list[tuple[str, Callable[[], Coroutine[Any, Any, bool]]]] | None = None,
) -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/health")
    async def liveness() -> dict[str, str]:
        return {"status": "ok", "service": service_name}

    @router.get("/ready")
    async def readiness() -> JSONResponse:
        checks: dict[str, str] = {}
        all_ok = True

        for name, check_fn in (readiness_checks or []):
            try:
                ok = await check_fn()
                checks[name] = "ok" if ok else "degraded"
                if not ok:
                    all_ok = False
            except Exception:
                checks[name] = "error"
                all_ok = False

        status_code = 200 if all_ok else 503
        return JSONResponse(
            status_code=status_code,
            content={"status": "ready" if all_ok else "not_ready", "checks": checks},
        )

    return router
