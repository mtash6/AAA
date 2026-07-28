"""
Enterprise Request Tracing & Structured Logging Middleware
Provides high-performance pure ASGI middleware with ContextVar propagation,
distributed trace correlation, health-check suppression, and high-precision timing.
"""

import logging
import time
import uuid
from typing import Set, Optional
from contextvars import ContextVar
from starlette.types import ASGIApp, Scope, Receive, Send, Message

# Global ContextVar for distributed trace correlation across async tasks
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


# --------------------------------------------------------------------------
# LOGGING FILTER FOR AUTOMATIC TRACE ID INJECTION
# --------------------------------------------------------------------------

class RequestIdFilter(logging.Filter):
    """
    Injects the active request_id from ContextVar into standard LogRecord instances.
    Enables %(request_id)s format specifier in standard Python logging.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get("-")
        return True


# Setup Root/Application Logger Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | [%(request_id)s] | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Apply filter to root logger standard handlers
root_logger = logging.getLogger()
for handler in root_logger.handlers:
    handler.addFilter(RequestIdFilter())

logger = logging.getLogger("TEAM_AI")


# --------------------------------------------------------------------------
# PURE ASGI REQUEST LOGGING MIDDLEWARE
# --------------------------------------------------------------------------

class RequestLoggingMiddleware:
    """
    High-performance pure ASGI middleware for request logging and trace propagation.
    Avoids BaseHTTPMiddleware performance bottlenecks and memory streaming leaks.
    """

    def __init__(
        self, 
        app: ASGIApp, 
        exclude_paths: Optional[Set[str]] = None
    ):
        self.app = app
        self.exclude_paths = exclude_paths or {
            "/health", 
            "/healthz", 
            "/metrics", 
            "/live", 
            "/ready", 
            "/favicon.ico"
        }

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Ignore non-HTTP protocols (e.g., WebSockets, Lifespan events)
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Skip logging for health checks to prevent log bloat in Kubernetes/ECS
        if path in self.exclude_paths:
            await self.app(scope, receive, send)
            return

        # 1. Extract or Generate Request/Trace ID
        headers = dict(scope.get("headers", []))
        incoming_trace_id = headers.get(b"x-request-id") or headers.get(b"x-correlation-id")
        
        if incoming_trace_id:
            request_id = incoming_trace_id.decode("latin1")
        else:
            request_id = str(uuid.uuid4())[:8]

        # 2. Set ContextVar token for downstream visibility
        token = request_id_var.set(request_id)

        method = scope.get("method", "UNKNOWN")
        client_host = scope.get("client", ("0.0.0.0", 0))[0]
        start_time = time.perf_counter()

        logger.info(f"--> {method} {path} (client={client_host})")

        status_code = 500  # Default fallback status in case of abrupt failure

        # 3. Intercept response stream to inject headers and capture status code
        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                process_time_ms = (time.perf_counter() - start_time) * 1000.0

                headers_list = list(message.get("headers", []))
                headers_list.append((b"x-request-id", request_id.encode("latin1")))
                headers_list.append((b"x-process-time-ms", f"{process_time_ms:.2f}".encode("latin1")))
                message["headers"] = headers_list

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            process_time = round((time.perf_counter() - start_time) * 1000.0, 2)
            logger.critical(f"CRITICAL FAIL: {str(exc)} ({process_time}ms)", exc_info=True)
            raise exc
        finally:
            process_time = round((time.perf_counter() - start_time) * 1000.0, 2)
            logger.info(f"<-- {status_code} ({process_time}ms)")
            # Clean up ContextVar context state
            request_id_var.reset(token)
