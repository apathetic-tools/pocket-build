# src/pocket_build/utils_logs.py
"""Shared Apathetic CLI logger implementation."""

from __future__ import annotations

import argparse
import builtins
import importlib
import logging
import os
import sys
from collections.abc import Callable, Generator
from contextlib import contextmanager, suppress
from typing import Any, TextIO, cast

from .constants import DEFAULT_LOG_LEVEL
from .meta import PROGRAM_ENV
from .utils_types import cast_hint


# --- Constants ---------------------------------------------------------------

# Flag for quick runtime enable/disable
TEST_TRACE_ENABLED = os.getenv("TEST_TRACE", "").lower() in {"1", "true", "yes"}

# Lazy, safe import — avoids patched time modules
#   in environments like pytest or eventlet
_real_time = importlib.import_module("time")

# ANSI Colors
RESET = "\033[0m"
CYAN = "\033[36m"
YELLOW = "\033[93m"  # or \033[33m
RED = "\033[91m"  # or \033[31m # or background \033[41m
GREEN = "\033[92m"  # or \033[32m
GRAY = "\033[90m"

# Logger levels
TRACE_LEVEL = logging.DEBUG - 5
# DEBUG      - builtin # verbose
# INFO       - builtin
# WARNING    - builtin
# ERROR      - builtin
# CRITICAL   - builtin # quiet mode
SILENT_LEVEL = logging.CRITICAL + 1  # one above the highest builtin level

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


# --- Logging that bypasses streams -------------------------------------------------


def safe_log(msg: str) -> None:
    """Emergency logger that never fails."""
    stream = cast("TextIO", sys.__stderr__)
    try:
        print(msg, file=stream)
    except Exception:  # noqa: BLE001
        # As final guardrail — never crash during crash reporting
        with suppress(Exception):
            stream.write(f"[INTERNAL] {msg}\n")


# --- Logging for debugging tests -------------------------------------------------


def make_test_trace(icon: str = "🧰") -> Callable[..., Any]:
    def local_trace(label: str, *args: Any) -> Any:
        return TEST_TRACE(label, *args, icon=icon)

    return local_trace


def TEST_TRACE(label: str, *args: Any, icon: str = "🧰") -> None:  # noqa: N802
    """Emit a synchronized, flush-safe diagnostic line.

    Args:
        label: Short identifier or context string.
        *args: Optional values to append.
        icon: Emoji prefix/suffix for easier visual scanning.

    """
    if not TEST_TRACE_ENABLED:
        return

    ts = _real_time.monotonic()
    # builtins.print more reliable than sys.stdout.write + sys.stdout.flush
    builtins.print(
        f"{icon} [TEST TRACE {ts:.6f}] {label}",
        *args,
        file=sys.__stderr__,
        flush=True,
    )


# --- Apathetic logger -----------------------------------------------------


class ApatheticCLILogger(logging.Logger):
    """Logger for all Apathetic CLI tools."""

    enable_color: bool = False

    _logging_module_extended: bool = False

    # if stdout or stderr are redirected, we need to repoint
    _last_stream_ids: tuple[TextIO, TextIO] | None = None

    def __init__(
        self,
        name: str,
        level: int = logging.NOTSET,
        *,
        enable_color: bool | None = None,
    ) -> None:
        # it is too late to call extend_logging_module

        # now let's init our logger
        super().__init__(name, level)

        # default level resolution
        if self.level == logging.NOTSET:
            self.setLevel(self.determine_log_level())

        # detect color support once per instance
        self.enable_color = (
            enable_color
            if enable_color is not None
            else type(self).determine_color_enabled()
        )

        self.propagate = False  # avoid duplicate root logs

        # handler attachment will happen in _log() with ensure_handlers()

    def ensure_handlers(self) -> None:
        if self._last_stream_ids is None or not self.handlers:
            rebuild = True
        else:
            last_stdout, last_stderr = self._last_stream_ids
            rebuild = (last_stdout is not sys.stdout) or (last_stderr is not sys.stderr)

        if rebuild:
            self.handlers.clear()
            h = DualStreamHandler()
            h.setFormatter(TagFormatter("%(message)s"))
            h.enable_color = self.enable_color
            self.addHandler(h)
            self._last_stream_ids = (sys.stdout, sys.stderr)
            TEST_TRACE("ensure_handlers()", f"rebuilt_handlers={self.handlers}")

    def _log(  # type: ignore[override]
        self, level: int, msg: str, args: tuple[Any, ...], **kwargs: Any
    ) -> None:
        TEST_TRACE(
            "_log",
            f"logger={self.name}",
            f"id={id(self)}",
            f"level={self.level_name}",
            f"msg={msg!r}",
        )
        self.ensure_handlers()
        super()._log(level, msg, args, **kwargs)

    def setLevel(self, level: int | str) -> None:  # noqa: N802
        """Case insensitive version"""
        if isinstance(level, str):
            level = level.upper()
        super().setLevel(level)

    @classmethod
    def determine_color_enabled(cls) -> bool:
        """Return True if colored output should be enabled."""
        # Respect explicit overrides
        if "NO_COLOR" in os.environ:
            return False
        if os.getenv("FORCE_COLOR", "").lower() in {"1", "true", "yes"}:
            return True

        # Auto-detect: use color if output is a TTY
        return sys.stdout.isatty()

    @classmethod
    def extend_logging_module(cls) -> bool:
        """The return value tells you if we ran or not.
        If it is False and you're calling it via super(),
        you can likely skip your code too."""
        # ensure module-level logging setup runs only once
        if cls._logging_module_extended:
            return False
        cls._logging_module_extended = True

        logging.setLoggerClass(cls)

        logging.addLevelName(TRACE_LEVEL, "TRACE")
        logging.addLevelName(SILENT_LEVEL, "SILENT")

        logging.TRACE = TRACE_LEVEL  # type: ignore[attr-defined]
        logging.SILENT = SILENT_LEVEL  # type: ignore[attr-defined]

        return True

    def determine_log_level(
        self,
        *,
        args: argparse.Namespace | None = None,
        root_log_level: str | None = None,
    ) -> str:
        """Resolve log level from CLI → env → root config → default."""
        args_level = getattr(args, "log_level", None)
        if args_level is not None:
            return cast_hint(str, args_level).upper()

        env_log_level = os.getenv(f"{PROGRAM_ENV}_LOG_LEVEL") or os.getenv("LOG_LEVEL")
        if env_log_level:
            return env_log_level.upper()

        if root_log_level:
            return root_log_level.upper()

        return DEFAULT_LOG_LEVEL.upper()

    @property
    def level_name(self) -> str:
        """Return the current effective level name
        (see also: logging.getLevelName)."""
        return logging.getLevelName(self.getEffectiveLevel())

    def error_if_not_debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs an exception with the real traceback starting from the caller.
        Only shows full traceback if debug/trace is enabled."""
        exc_info = kwargs.pop("exc_info", True)
        stacklevel = kwargs.pop("stacklevel", 2)  # skip helper frame
        if self.isEnabledFor(logging.DEBUG):
            self.exception(msg, *args, exc_info=exc_info, stacklevel=stacklevel)
        else:
            self.error(msg, *args)

    def critical_if_not_debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs an exception with the real traceback starting from the caller.
        Only shows full traceback if debug/trace is enabled."""
        exc_info = kwargs.pop("exc_info", True)
        stacklevel = kwargs.pop("stacklevel", 2)  # skip helper frame
        if self.isEnabledFor(logging.DEBUG):
            self.exception(msg, *args, exc_info=exc_info, stacklevel=stacklevel)
        else:
            self.critical(msg, *args)

    def colorize(
        self, text: str, color: str, *, enable_color: bool | None = None
    ) -> str:
        if enable_color is None:
            enable_color = self.enable_color
        return f"{color}{text}{RESET}" if enable_color else text

    def trace(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(TRACE_LEVEL):
            self._log(TRACE_LEVEL, msg, args, **kwargs)

    def resolve_level_name(self, level_name: str) -> int | None:
        """logging.getLevelNamesMapping() is only introduced in 3.11"""
        return getattr(logging, level_name.upper(), None)

    def log_dynamic(
        self, level: str | int, msg: str, *args: Any, **kwargs: Any
    ) -> None:
        # Resolve level
        if isinstance(level, str):
            level_no = self.resolve_level_name(level)
            if not isinstance(level_no, int):
                self.error("Unknown log level: %r", level)
                return
        elif isinstance(level, int):  # pyright: ignore[reportUnnecessaryIsInstance]
            level_no = level
        else:
            self.error("Invalid log level type: %r", type(level))
            return

        self._log(level_no, msg, args, **kwargs)

    @contextmanager
    def use_level(self, level: str | int) -> Generator[None, None, None]:
        """Use a context to temporarily log with a different log-level."""
        prev_level = self.level

        # Resolve level
        if isinstance(level, str):
            level_no = self.resolve_level_name(level)
            if not isinstance(level_no, int):
                self.error("Unknown log level: %r", level)
                # Yield control anyway so the 'with' block doesn't explode
                yield
                return
        elif isinstance(level, int):  # pyright: ignore[reportUnnecessaryIsInstance]
            level_no = level
        else:
            self.error("Invalid log level type: %r", type(level))
            yield
            return

        # Apply new level
        self.setLevel(level_no)
        try:
            yield
        finally:
            self.setLevel(prev_level)


# --- Tag formatter ---------------------------------------------------------


class TagFormatter(logging.Formatter):
    def format(self: TagFormatter, record: logging.LogRecord) -> str:
        tag_color, tag_text = TAG_STYLES.get(record.levelname, ("", ""))
        msg = super().format(record)
        if tag_text:
            if getattr(record, "enable_color", False) and tag_color:
                prefix = f"{tag_color}{tag_text}{RESET}"
            else:
                prefix = tag_text
            return f"{prefix} {msg}"
        return msg


# --- DualStreamHandler ---------------------------------------------------------


class DualStreamHandler(logging.StreamHandler[TextIO]):
    """Send info/debug/trace to stdout, everything else to stderr."""

    enable_color: bool = False

    def __init__(self) -> None:
        # default to stdout, overridden per record
        super().__init__(stream=sys.stdout)

    def emit(self, record: logging.LogRecord) -> None:
        level = record.levelno
        if level >= logging.WARNING:
            self.stream = sys.stderr
        else:
            self.stream = sys.stdout

        # used by TagFormatter
        record.enable_color = getattr(self, "enable_color", False)

        super().emit(record)
