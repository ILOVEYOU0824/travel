"""전역 예외 핸들러 — 구조화 detail + 로깅."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.claude_service import ClaudeApiError
from app.services.places_service import PlacesApiError
from app.services.routes_service import RoutesApiError

logger = logging.getLogger("japantrip")


def _payload(*, code: str, message: str, status: int) -> dict:
    return {"detail": message, "code": code, "status": status}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ClaudeApiError)
    async def claude_error(_request: Request, exc: ClaudeApiError) -> JSONResponse:
        status = exc.status_code or 502
        logger.warning("ClaudeApiError: %s", exc)
        return JSONResponse(
            status_code=status,
            content=_payload(code="llm_error", message=str(exc), status=status),
        )

    @app.exception_handler(PlacesApiError)
    async def places_error(_request: Request, exc: PlacesApiError) -> JSONResponse:
        status = exc.status_code or 502
        logger.warning("PlacesApiError: %s", exc)
        return JSONResponse(
            status_code=status,
            content=_payload(code="places_error", message=str(exc), status=status),
        )

    @app.exception_handler(RoutesApiError)
    async def routes_error(_request: Request, exc: RoutesApiError) -> JSONResponse:
        status = exc.status_code or 502
        logger.warning("RoutesApiError: %s", exc)
        return JSONResponse(
            status_code=status,
            content=_payload(code="routes_error", message=str(exc), status=status),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info("ValidationError: %s", exc.errors())
        return JSONResponse(
            status_code=422,
            content=_payload(
                code="validation_error",
                message="요청 값이 올바르지 않습니다.",
                status=422,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(code="http_error", message=detail, status=exc.status_code),
        )

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_payload(
                code="internal_error",
                message="서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
                status=500,
            ),
        )
