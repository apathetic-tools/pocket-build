# src/pocket_build/utils_logs.py

import logging
import sys
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, TextIO, cast

from .meta import PROGRAM_PACKAGE
from .runtime import current_runtime
from .utils import safe_log


# --- ANSI Colors -------------------------------------------------------------


RESET = "\033[0m"
CYAN = "\033[36m"
YELLOW = "\033[93m"  # or \033[33m
RED = "\033[91m"  # or \033[31m # or background \033[41m
GREEN = "\033[92m"  # or \033[32m
GRAY = "\033[90m"


LEVEL_ORDER = [
    "trace",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    "silent",  # disables all logging
]


TAG_STYLES = {
    "TRACE": (GRAY, "[TRACE]"),
    "DEBUG": (CYAN, "[DEBUG]"),
    "WARNING": ("", "⚠️ "),
    "ERROR": ("", "❌ "),
    "CRITICAL": ("", "💥 "),
}

# sanity check
assert set(TAG_STYLES.keys()) <= {lvl.upper() for lvl in LEVEL_ORDER}, (  # noqa: S101
    "TAG_STYLES contains unknown levels"
)


# --- Custom TRACE level ------------------------------------------------------


class LoggerWithTrace(logging.Logger):
    def trace(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(TRACE_LEVEL):
            self._log(TRACE_LEVEL, msg, args, **kwargs)


TRACE_LEVEL = logging.DEBUG - 5
logging.addLevelName(TRACE_LEVEL, "TRACE")
logging.setLoggerClass(LoggerWithTrace)


# --- Tag formatter ---------------------------------------------------------


class TagFormatter(logging.Formatter):
    def format(self: "TagFormatter", record: logging.LogRecord) -> str:
        tag_color, tag_text = TAG_STYLES.get(record.levelname, ("", ""))
        msg = super().format(record)
        if tag_text:
            use_color = current_runtime.get("use_color", True)
            if use_color and tag_color:
                prefix = f"{tag_color}{tag_text}{RESET}"
            else:
                prefix = tag_text
            return f"{prefix} {msg}"
        return msg


# --- DualStreamHandler ---------------------------------------------------------


class DualStreamHandler(logging.StreamHandler[TextIO]):
    """Send info/debug/trace to stdout, everything else to stderr."""

    def __init__(self) -> None:
        # default to stdout, overridden per record
        super().__init__(stream=sys.stdout)

    def emit(self, record: logging.LogRecord) -> None:
        level = record.levelno
        if level >= logging.WARNING:
            self.stream = sys.stderr
        else:
            self.stream = sys.stdout
        super().emit(record)


# --- Logger initialization ---------------------------------------------------


_logger = cast("LoggerWithTrace", logging.getLogger(PROGRAM_PACKAGE))


def _ensure_logger_initialized() -> None:
    """Configure the logger once."""
    if getattr(_ensure_logger_initialized, "_done", False):
        return

    handler = DualStreamHandler()
    handler.setFormatter(TagFormatter("%(message)s"))
    _logger.addHandler(handler)

    _logger.propagate = False  # don’t double-log through root logger
    _ensure_logger_initialized._done = True  # type: ignore[attr-defined]  # noqa: SLF001


def _set_logger_level_from_runtime() -> None:
    """Sync the internal logger level with runtime/env settings."""
    _ensure_logger_initialized()
    level_name = current_runtime.get("log_level")

    if level_name is None:  # pyright: ignore[reportUnnecessaryComparison]
        safe_log("[LOGGER ERROR] ❌ Runtime does not specify log_level")
        level_name = "ERROR"

    level_name = str(level_name).upper()

    level_map = {
        "TRACE": TRACE_LEVEL,
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        "SILENT": logging.CRITICAL + 1,  # built-in silent equivalent
    }
    _logger.setLevel(level_map.get(level_name, logging.INFO))


def get_logger() -> LoggerWithTrace:
    """Return the configured pocket_build logger."""
    _ensure_logger_initialized()
    _set_logger_level_from_runtime()
    return _logger


def get_log_level() -> str:
    """Return the current log level, or 'error' if undefined or invalid.

    Note: Not for internal use to utils_logs functions."""
    level = cast("str | None", current_runtime.get("log_level"))  # type: ignore[redundant-cast]
    if level is None:
        safe_log("[LOGGER ERROR] ❌ Runtime does not specify log_level")
        return "error"

    if level not in LEVEL_ORDER:
        safe_log(f"[LOGGER ERROR] ❌ Unknown log level: {level!r}")
        return "error"

    return level


def set_log_level(level: str) -> None:
    """Set the logging level.

    Note: Not for internal use to utils_logs functions."""
    current_runtime["log_level"] = level
    _set_logger_level_from_runtime()


@contextmanager
def temporary_log_level(level: str) -> Generator[None, None, None]:
    prev = current_runtime["log_level"]
    current_runtime["log_level"] = level
    _set_logger_level_from_runtime()
    try:
        yield
    finally:
        current_runtime["log_level"] = prev
        _set_logger_level_from_runtime()


def log_dynamic(level: str, message: str) -> None:
    """Log a message at a dynamic level name (e.g. 'info', 'error', 'trace')."""
    logger = get_logger()
    method = getattr(logger, level.lower(), None)
    if callable(method):
        method(message)
    else:
        logger.error("Unknown log level: %r", level)


def colorize(text: str, color: str, *, use_color: bool | None = None) -> str:
    if use_color is None:
        use_color = current_runtime["use_color"]
    return f"{color}{text}{RESET}" if use_color else text
