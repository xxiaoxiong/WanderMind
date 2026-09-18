from __future__ import annotations

import base64
import binascii
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.exc import SQLAlchemyError

from wandermind.api.router import api_router
from wandermind.api.schemas import HealthResponse
from wandermind.application.container import ApplicationContainer, build_container
from wandermind.cognitive.errors import CognitiveError
from wandermind.cognitive.ingestion import DuplicateKnowledgeError
from wandermind.infrastructure.config import Settings, get_settings
from wandermind.infrastructure.database import create_schema
from wandermind.infrastructure.errors import AppError
from wandermind.infrastructure.observability import request_logging_middleware
from wandermind.runtime import RuntimeErrorBase, RuntimeTimeoutError


def create_app(
    settings: Settings | None = None,
    *,
    container: ApplicationContainer | None = None,
) -> FastAPI:
    selected_settings = settings or get_settings()
    selected_container = container or build_container(selected_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = selected_container
        if selected_container.database_engine is not None and selected_settings.auto_create_schema:
            await create_schema(selected_container.database_engine)
        if selected_settings.enable_scheduler:
            selected_container.scheduler.start()
        yield
        selected_container.scheduler.shutdown()
        await selected_container.runtime.close()
        if selected_container.database_engine is not None:
            await selected_container.database_engine.dispose()

    app = FastAPI(
        title=selected_settings.app_name,
        version=selected_settings.app_version,
        lifespan=lifespan,
    )
    app.state.container = selected_container
    app.add_middleware(
        CORSMiddleware,
        allow_origins=selected_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(request_logging_middleware)

    @app.middleware("http")
    async def enforce_access_control(request: Request, call_next: Any) -> Response:
        if (
            request.method == "OPTIONS"
            or request.url.path == "/health"
            or _has_valid_basic_access(request, selected_settings)
        ):
            response: Response = await call_next(request)
            return response
        return JSONResponse(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="WanderMind", charset="UTF-8"'},
            content={
                "error": {
                    "code": "authentication_required",
                    "message": "valid WanderMind access credentials are required",
                    "details": {},
                    "retryable": False,
                }
            },
        )

    @app.middleware("http")
    async def enforce_body_limit(request: Request, call_next: Any) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                declared_size = selected_settings.max_request_bytes + 1
            if declared_size > selected_settings.max_request_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "payload_too_large",
                            "message": "request body exceeds the configured size limit",
                            "details": {"max_bytes": selected_settings.max_request_bytes},
                            "retryable": False,
                        }
                    },
                )
        response: Response = await call_next(request)
        return response

    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(DuplicateKnowledgeError, _duplicate_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(CognitiveError, _dependency_error_handler)
    app.add_exception_handler(RuntimeErrorBase, _dependency_error_handler)
    app.add_exception_handler(SQLAlchemyError, _dependency_error_handler)
    app.add_exception_handler(Exception, _internal_error_handler)
    app.include_router(api_router)

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        storage = "sqlalchemy" if selected_container.database_engine is not None else "memory"
        return HealthResponse(
            status="ok",
            version=selected_settings.app_version,
            environment=selected_settings.env,
            storage=storage,
            runtime=selected_settings.runtime_adapter,
        )

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    if selected_settings.static_dir is not None:
        static_dir = Path(selected_settings.static_dir)
        if static_dir.is_dir():
            app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")

    return app


def _has_valid_basic_access(request: Request, settings: Settings) -> bool:
    configured_credential = settings.access_password
    if configured_credential is None or not configured_credential.get_secret_value():
        return True
    scheme, _, encoded = request.headers.get("authorization", "").partition(" ")
    if scheme.casefold() != "basic" or not encoded:
        return False
    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False
    username, separator, supplied_credential = decoded.partition(":")
    return bool(
        separator
        and secrets.compare_digest(username, settings.access_username)
        and secrets.compare_digest(
            supplied_credential,
            configured_credential.get_secret_value(),
        )
    )


async def _app_error_handler(_request: Request, error: Exception) -> JSONResponse:
    app_error = error
    assert isinstance(app_error, AppError)
    return JSONResponse(
        status_code=app_error.status_code,
        content={
            "error": {
                "code": app_error.code,
                "message": app_error.message,
                "details": app_error.details,
                "retryable": app_error.retryable,
            }
        },
    )


async def _validation_error_handler(
    _request: Request,
    error: Exception,
) -> JSONResponse:
    validation_error = error
    assert isinstance(validation_error, RequestValidationError)
    errors: list[dict[str, Any]] = list(validation_error.errors())
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "request validation failed",
                "details": {"errors": jsonable_encoder(errors)},
                "retryable": False,
            }
        },
    )


async def _duplicate_error_handler(_request: Request, error: Exception) -> JSONResponse:
    duplicate_error = error
    assert isinstance(duplicate_error, DuplicateKnowledgeError)
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "duplicate_knowledge",
                "message": str(duplicate_error),
                "details": {
                    "existing_id": duplicate_error.existing_id,
                    "reason": duplicate_error.reason,
                },
                "retryable": False,
            }
        },
    )


async def _dependency_error_handler(_request: Request, error: Exception) -> JSONResponse:
    if isinstance(error, SQLAlchemyError):
        return _error_response(
            status_code=503,
            code="database_error",
            message="database operation failed",
            retryable=True,
        )
    if isinstance(error, RuntimeTimeoutError):
        return _error_response(
            status_code=504,
            code="timeout_error",
            message=str(error),
            retryable=True,
        )
    if isinstance(error, RuntimeErrorBase):
        return _error_response(
            status_code=502,
            code="runtime_error",
            message=str(error),
            retryable=error.retryable,
        )
    assert isinstance(error, CognitiveError)
    return _error_response(
        status_code=503 if error.retryable else 500,
        code=error.code,
        message=str(error),
        retryable=error.retryable,
    )


async def _internal_error_handler(_request: Request, error: Exception) -> JSONResponse:
    del error
    return _error_response(
        status_code=500,
        code="internal_error",
        message="an unexpected internal error occurred",
        retryable=False,
    )


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    retryable: bool,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": {},
                "retryable": retryable,
            }
        },
    )
