import logging
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("TEAM_AI")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # Attach request context
        request.state.request_id = request_id
        logger.info(f"[{request_id}] --> {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            process_time = round((time.time() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-MS"] = str(process_time)
            
            logger.info(f"[{request_id}] <-- {response.status_code} ({process_time}ms)")
            return response
        except Exception as exc:
            process_time = round((time.time() - start_time) * 1000, 2)
            logger.error(f"[{request_id}] CRITICAL FAIL: {str(exc)} ({process_time}ms)", exc_info=True)
            raise exc