from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger("TEAM_AI.Exceptions")


class TEAMAIException(Exception):
    """Base Domain Exception"""
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, code: str = "BAD_REQUEST"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


def register_exception_handlers(app):
    @app.exception_handler(TEAMAIException)
    async def team_ai_exception_handler(request: Request, exc: TEAMAIException):
        req_id = getattr(request.state, "request_id", "UNKNOWN")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "request_id": req_id,
                "error": {
                    "code": exc.code,
                    "message": exc.message
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = getattr(request.state, "request_id", "UNKNOWN")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "request_id": req_id,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters or payload format.",
                    "details": exc.errors()
                }
            }
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        req_id = getattr(request.state, "request_id", "UNKNOWN")
        logger.error(f"[{req_id}] Database Error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "request_id": req_id,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "A database transaction error occurred."
                }
            }
        )

    @app.exception_handler(Exception)
    async def global_unhandled_exception_handler(request: Request, exc: Exception):
        req_id = getattr(request.state, "request_id", "UNKNOWN")
        logger.critical(f"[{req_id}] Unhandled Exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "request_id": req_id,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": f"System error: {str(exc)}"
                }
            }
        )