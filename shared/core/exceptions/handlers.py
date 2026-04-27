import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from .base import AppError


def _error_response(status_code: int, error_code: str, message: str, detail: object = None) -> JSONResponse:
    body = {
        "error": error_code,
        "message": message,
        "request_id": str(uuid.uuid4()),
    }
    if detail is not None:
        body["detail"] = detail  # type: ignore[assignment]
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.error_code, exc.message, exc.detail)

    @app.exception_handler(PydanticValidationError)
    async def handle_pydantic_error(request: Request, exc: PydanticValidationError) -> JSONResponse:
        return _error_response(422, "validation_error", "Request validation failed", exc.errors())

    @app.exception_handler(Exception)
    async def handle_unhandled(request: Request, exc: Exception) -> JSONResponse:
        return _error_response(500, "internal_error", "An unexpected error occurred")
