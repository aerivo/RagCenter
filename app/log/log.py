import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_logger = logging.getLogger("ragcenter")
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
_FIXED_FIELDS = {"timestamp", "level", "event", "request_id"}
_TEXT_ESCAPES = str.maketrans({"\\": "\\\\", "\r": "\\r", "\n": "\\n", "|": "\\|"})


class _TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, UTC)
        request_id = getattr(record, "request_id", None) or "-"
        parts = [
            timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            record.levelname,
            record.getMessage(),
            f"request_id={request_id}",
        ]
        fields = getattr(record, "fields", {})
        parts.extend(
            f"{name}={value}" for name, value in fields.items() if name not in _FIXED_FIELDS
        )
        line = " | ".join(part.translate(_TEXT_ESCAPES) for part in parts)
        if record.exc_info:
            line = f"{line}\n{self.formatException(record.exc_info)}"
        if record.stack_info:
            line = f"{line}\n{self.formatStack(record.stack_info)}"
        return line


class _EventLogger(logging.LoggerAdapter):
    def process(self, msg: object, kwargs: dict[str, Any]) -> tuple[object, dict[str, Any]]:
        extra = kwargs.pop("extra", None) or {}
        logging_options = {
            name: kwargs.pop(name)
            for name in ("exc_info", "stack_info", "stacklevel")
            if name in kwargs
        }
        logging_options["extra"] = {
            "request_id": _request_id.get(),
            "fields": {**extra, **kwargs},
        }
        return msg, logging_options


logger = _EventLogger(_logger)


def _file_handler(filename: str) -> RotatingFileHandler:
    return RotatingFileHandler(
        _LOG_DIR / filename,
        maxBytes=20 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
        delay=True,
    )


def configure_logging() -> None:
    if _logger.handlers:
        return

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    formatter = _TextFormatter()

    console_handler = logging.StreamHandler(sys.stdout)
    app_handler = _file_handler("app.log")
    app_handler.addFilter(lambda record: record.levelno < logging.ERROR)
    error_handler = _file_handler("error.log")
    error_handler.setLevel(logging.ERROR)

    for handler in (console_handler, app_handler, error_handler):
        handler.setFormatter(formatter)
        _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = Headers(scope=scope).get("x-request-id") or f"req_{uuid4().hex}"
        token = _request_id.set(request_id)
        started = perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        def request_fields() -> dict[str, object]:
            return {
                "method": scope["method"],
                "path": scope["path"],
                "status_code": status_code,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            }

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            logger.exception("request_failed", **request_fields())
            raise
        else:
            logger.info("request_completed", **request_fields())
        finally:
            _request_id.reset(token)
