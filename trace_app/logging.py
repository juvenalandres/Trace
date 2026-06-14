import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

# Context variables for request-scoped data
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add request context if available
        request_id = request_id_var.get("")
        if request_id:
            log_entry["request_id"] = request_id

        user_id = user_id_var.get(None)
        if user_id is not None:
            log_entry["user_id"] = user_id

        # Add extra fields
        if hasattr(record, "extra"):
            log_entry.update(record.extra)

        # Add exception info
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure structured JSON logging."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]

    # Configure uvicorn access log
    uvicorn_logger = logging.getLogger("uvicorn.access")
    uvicorn_logger.handlers = [handler]

    # Configure uvicorn error log
    uvicorn_logger = logging.getLogger("uvicorn.error")
    uvicorn_logger.handlers = [handler]


def get_request_id() -> str:
    """Get current request ID or generate a new one."""
    req_id = request_id_var.get("")
    if not req_id:
        req_id = uuid.uuid4().hex[:12]
        request_id_var.set(req_id)
    return req_id


def log_with_context(logger: logging.Logger, level: int, msg: str, **kwargs) -> None:
    """Log a message with extra context fields."""
    extra = {"extra": kwargs}
    logger.log(level, msg, extra=extra)
