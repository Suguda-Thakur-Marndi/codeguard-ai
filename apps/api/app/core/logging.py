"""Structured JSON logging with secret sanitization and context tracking."""

import json
import logging
import re
import sys
import time
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Context variables for distributed tracing across async requests & worker jobs
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
review_job_id_ctx: ContextVar[str | None] = ContextVar("review_job_id", default=None)

# Patterns for sensitive tokens and keys that must never be logged
SENSITIVE_PATTERNS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}"),  # GitHub tokens
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+PRIVATE KEY-----"),
    re.compile(r"(Bearer\s+)[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_=]*"),
    re.compile(r"(secret|token|password|private_key|key|auth|signature)=([^&\s]+)", re.IGNORECASE),
]


def redact_sensitive_data(message: str) -> str:
    """Redact sensitive patterns from strings."""
    if not isinstance(message, str):
        return str(message)
    sanitized = message
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(r"[REDACTED_SECRET]", sanitized)
    return sanitized


class StructuredJsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured observability."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_sensitive_data(record.getMessage()),
        }

        # Attach context variables if present
        req_id = request_id_ctx.get()
        if req_id:
            log_entry["request_id"] = req_id

        job_id = review_job_id_ctx.get()
        if job_id:
            log_entry["review_job_id"] = job_id

        # Attach structured extra attributes if provided
        if hasattr(record, "event"):
            log_entry["event"] = record.event
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = round(record.duration_ms, 2)
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            for k, v in record.extra_fields.items():
                if isinstance(v, str):
                    log_entry[k] = redact_sensitive_data(v)
                else:
                    log_entry[k] = v

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure root logger with structured JSON formatting."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid adding duplicate handlers
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(StructuredJsonFormatter())

    return logging.getLogger("codeguard")


logger = setup_logging()


class TimingLogger:
    """Context manager to measure and log operation duration."""

    def __init__(self, event: str, extra_fields: dict[str, Any] | None = None):
        self.event = event
        self.extra_fields = extra_fields or {}
        self.start_time: float = 0.0

    def __enter__(self) -> "TimingLogger":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration_ms = (time.perf_counter() - self.start_time) * 1000.0
        extra = {
            "event": self.event,
            "duration_ms": duration_ms,
            "extra_fields": self.extra_fields,
        }
        if exc_type is not None:
            extra["extra_fields"]["error"] = str(exc_val)
            logger.error(
                f"Failed operation: {self.event} in {duration_ms:.2f}ms",
                extra=extra,
                exc_info=(exc_type, exc_val, exc_tb),
            )
        else:
            logger.info(
                f"Completed operation: {self.event} in {duration_ms:.2f}ms",
                extra=extra,
            )
