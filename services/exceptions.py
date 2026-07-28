"""
Global Exception Architecture & Standardized Error Envelopes
Provides hierarchical domain exceptions and FastAPI exception handlers.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List, Union

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

logger = logging.getLogger("TEAM_AI.Exceptions")

DEBUG_MODE = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")


# --------------------------------------------------------------------------
# DOMAIN EXCEPTION HIERARCHY
# --------------------------------------------------------------------------

class TEAMAIException(Exception):
    """Base Enterprise Domain Exception."""
    def __init__(
        self, 
        message: str, 
        status_code: int = status.HTTP_400_BAD_REQUEST, 
        code: str = "BAD_REQUEST",
        details: Optional[Any] = None
    ):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        super().__init__(message)


class EntityNotFoundException(TEAMAIException):
    def __init__(self, message: str = "Requested resource was not found.", details: Optional[Any] = None):
        super().__init__(message=message, status_code=status.HTTP_404_NOT_FOUND, code="RESOURCE_NOT_FOUND", details=details)


class UnauthorizedException(TEAMAIException):
    def __init__(self, message: str = "Authentication credentials are invalid or missing.", details: Optional[Any] = None):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED, code="UNAUTHORIZED", details=details)


class ForbiddenException(TEAMAIException):
    def __init__(self, message: str = "Access denied for current user role.", details: Optional[Any] = None):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN, code="FORBIDDEN", details=details)


class ConflictException(TEAMAIException):
    def __init__(self, message: str = "Resource conflict or duplicate constraint violation.", details: Optional[Any] = None):
        super().__init__(message=message, status_code=status.HTTP_409_CONFLICT, code="RESOURCE_CONFLICT", details=details)


class ValidationException(TEAMAIException):
    def __init__(self, message: str = "Validation failed for provided inputs.", details: Optional[Any] = None):
        super().__init__(message=message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, code="VALIDATION_ERROR", details=details)


# --------------------------------------------------------------------------
# RESPONSE BUILDER HELPER
# --------------------------------------------------------------------------

def _build_error_response(
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
    details: Optional[Any] = None
) -> JSONResponse:
    """Formats standardized API response envelopes."""
    req_id = getattr(request.state, "request_id", "UNKNOWN")
    
    content: Dict[str, Any] = {
        "success": False,
        "request_id": req_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "path": request.url.path,
        "method": request.method,
        "error": {
            "code": error_code,
            "message": message,
        }
    }
    
    if details is not None:
        content["error"]["details"] = details
        
    return JSONResponse(status_code=status_code, content=content)


# --------------------------------------------------------------------------
# EXCEPTION REGISTRATION
# --------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """Registers unified custom exception handlers with the FastAPI engine."""

    # 1. Custom Domain Exceptions
    @app.exception_handler(TEAMAIException)
    async def team_ai_exception_handler(request: Request, exc: TEAMAIException):
        logger.warning(f"[{getattr(request.state, 'request_id', 'UNKNOWN')}] Domain Exception ({exc.code}): {exc.message}")
        return _build_error_response(
            request=request,
            status_code=exc.status_code,
            error_code=exc.code,
            message=exc.message,
            details=exc.details
        )

    # 2. Native Starlette/FastAPI HTTP Exceptions
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        error_code_map = {
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED"
        }
        code = error_code_map.get(exc.status_code, "HTTP_ERROR")
        return _build_error_response(
            request=request,
            status_code=exc.status_code,
            error_code=code,
            message=str(exc.detail)
        )

    # 3. Pydantic Request Validation Errors
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = getattr(request.state, "request_id", "UNKNOWN")
        logger.info(f"[{req_id}] Payload Validation Failure on {request.method} {request.url.path}")
        
        # Format Pydantic error details safely
        sanitized_errors = []
        for err in exc.errors():
            loc = " -> ".join([str(x) for x in err.get("loc", [])])
            sanitized_errors.append({
                "location": loc,
                "message": err.get("msg"),
                "type": err.get("type")
            })

        return _build_error_response(
            request=request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            message="Invalid request parameters or payload body format.",
            details=sanitized_errors
        )

    # 4. Database Errors (SQLAlchemy)
    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        req_id = getattr(request.state, "request_id", "UNKNOWN")
        logger.error(f"[{req_id}] Database Transaction Error: {type(exc).__name__} - {str(exc)}", exc_info=True)
        
        if isinstance(exc, IntegrityError):
            return _build_error_response(
                request=request,
                status_code=status.HTTP_409_CONFLICT,
                error_code="DATABASE_INTEGRITY_CONFLICT",
                message="Operation violated a database uniqueness or foreign key constraint."
            )

        return _build_error_response(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            message="A database processing error occurred."
        )

    # 5. Global Catch-All Unhandled Exceptions
    @app.exception_handler(Exception)
    async def global_unhandled_exception_handler(request: Request, exc: Exception):
        req_id = getattr(request.state, "request_id", "UNKNOWN")
        logger.critical(f"[{req_id}] Unhandled Exception ({type(exc).__name__}): {str(exc)}", exc_info=True)
        
        # Hide raw exception strings in production to prevent security leaks
        public_message = str(exc) if DEBUG_MODE else "An unexpected internal server error occurred."
        
        return _build_error_response(
            request=request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            message=public_message,
            details={"debug_type": type(exc).__name__} if DEBUG_MODE else None
        )
