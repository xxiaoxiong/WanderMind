from __future__ import annotations

from typing import Any


class AppError(Exception):
    code = "internal_error"
    status_code = 500
    retryable = False

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    code = "not_found"
    status_code = 404


class ConflictError(AppError):
    code = "conflict"
    status_code = 409


class InsufficientKnowledgeError(AppError):
    code = "insufficient_knowledge"
    status_code = 409


class UnsafeInputError(AppError):
    code = "unsafe_input"
    status_code = 422


class RuntimeDependencyError(AppError):
    code = "runtime_failure"
    status_code = 502
    retryable = True


class DependencyTimeoutError(AppError):
    code = "dependency_timeout"
    status_code = 504
    retryable = True
