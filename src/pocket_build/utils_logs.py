# src/pocket_build/utils_logs.py

import logging
import sys
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

TAG_STYLES = {
    "TRACE": (CYAN, "[TRACE]"),
    "DEBUG": (CYAN, "[DEBUG]"),
    "WARNING": ("", "⚠️ "),
    "ERROR": ("", "❌ "),
    "CRITICAL": ("", "💥 "),
}


# --- Custom TRACE level ------------------------------------------------------


TRACE_LEVEL = logging.DEBUG - 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


def trace(
    self: logging.Logger,
    message: str,
    *args: Any,
    **kwargs: Any,
) -> None:
    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, message, args, **kwargs)


logging.Logger.trace = trace  # type: ignore[attr-defined]


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


_logger = logging.getLogger(PROGRAM_PACKAGE)


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
        "SILENT": 1000,  # effectively disables everything
    }
    _logger.setLevel(level_map.get(level_name, logging.INFO))


def log(
    level: str,
    *values: object,
    sep: str = " ",
    end: str = "\n",
    # file: TextIO | None = None,
    # flush: bool = False,
    # prefix: str | None = None,
) -> None:
    """Unified logging entry point using Python's logging system."""
    _ensure_logger_initialized()
    _set_logger_level_from_runtime()

    message = sep.join(map(str, values))
    if end != "\n":  # logging strips newlines automatically; preserve optional behavior
        message = message + end

    try:
        level_name = level.lower()
        if level_name == "trace":
            _logger.trace(message)  # type: ignore[attr-defined]
        elif level_name == "debug":
            _logger.debug(message)
        elif level_name == "info":
            _logger.info(message)
        elif level_name == "warning":
            _logger.warning(message)
        elif level_name == "error":
            _logger.error(message)
        elif level_name == "critical":
            _logger.critical(message)
        elif level_name == "silent":
            pass  # do nothing
        else:
            safe_log(f"[LOGGER ERROR] ❌ Unknown log level: {level!r}")
    except Exception as e:  # noqa: BLE001
        safe_log(f"[LOGGER FAILURE] {e}")


# --- OLD -------------------------------------------------------------


LEVEL_ORDER = [
    "trace",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    "silent",  # disables all logging
]

_LOG_PREFIXES: dict[str, str | None] = {
    "trace": "[TRACE] ",
    "debug": "[DEBUG] ",
    "info": None,
    "warning": "⚠️ ",
    "error": "❌ ",
    "critical": "💥 ",
}
_LOG_PREFIXES_COLOR: dict[str, str | None] = {
    "trace": YELLOW,
    "debug": GREEN,
    "info": None,
    "warning": None,
    "error": None,
    "critical": None,
}
_LOG_MSG_COLOR: dict[str, str | None] = {
    "trace": None,
    "debug": None,
    "info": None,
    "warning": None,
    "error": None,
    "critical": None,
}


def get_log_level() -> str:
    """Return the current log level, or 'error' if undefined or invalid."""
    level = cast("str | None", current_runtime.get("log_level"))  # type: ignore[redundant-cast]
    if level is None:
        safe_log("[LOGGER ERROR] ❌ Runtime does not specify log_level")
        return "error"

    if level not in LEVEL_ORDER:
        safe_log(f"[LOGGER ERROR] ❌ Unknown log level: {level!r}")
        return "error"

    return level


# def _should_log(level: str, current: str) -> bool:
#     """Return True if a message at `level` should be emitted under
#     the current log level `current`. Never logs if either level is 'silent'.
#     """
#     if level == "silent" or current == "silent":
#         return False

#     if level not in LEVEL_ORDER:
#         safe_log(f"[LOGGER ERROR] ❌ Unknown log level: {level!r}")
#         return False

#     return LEVEL_ORDER.index(level) >= LEVEL_ORDER.index(current)


# def _is_error_level(level: str) -> bool:
#     """Return True if this log level represents a problem or warning."""
#     return level in {"warning", "error", "critical"}


# def _resolve_output_stream(level: str, file: TextIO | None) -> TextIO:
#     """Decide whether to print to stdout or stderr, respecting BYPASS_CAPTURE."""
#     if file is not None:
#         return file

#     if is_bypass_capture():
#         return (
#             getattr(sys, "__stderr__", sys.stderr)
#             if _is_error_level(level)
#             else getattr(sys, "__stdout__", sys.stdout)
#         )
#     return sys.stderr if _is_error_level(level) else sys.stdout


# def _format_log_message(
#     level: str,
#     values: tuple[object, ...],
#     sep: str,
#     prefix: str | None,
# ) -> str:
#     """Apply prefix and color formatting to the log message."""
#     prefix_color = _LOG_PREFIXES_COLOR.get(level)
#     msg_color = _LOG_MSG_COLOR.get(level)

#     # Safely coerce prefix
#     actual_prefix = prefix if prefix is not None else (_LOG_PREFIXES.get(level) or "")

#     # Helper lambdas to treat None/"" as unset
#     def is_set(value: str | None) -> bool:
#         return bool(value and value.strip())

#     # If no whole-line color, apply prefix color
#     if not is_set(msg_color) and is_set(prefix_color):
#         actual_prefix = colorize(actual_prefix, cast("str", prefix_color))

#     message = sep.join([actual_prefix] + [str(v) for v in values])
#     if is_set(msg_color):
#         message = colorize(message, cast("str", msg_color))
#     return message


def colorize(text: str, color: str, *, use_color: bool | None = None) -> str:
    if use_color is None:
        use_color = current_runtime["use_color"]
    return f"{color}{text}{RESET}" if use_color else text
