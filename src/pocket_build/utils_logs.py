# src/pocket_build/utils_logs.py


import os
import sys
from contextlib import suppress
from typing import TextIO, cast

from .meta import PROGRAM_ENV
from .runtime import current_runtime
from .utils import safe_log


# Terminal colors (ANSI)
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

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


def is_bypass_capture() -> bool:
    """Return True if capture bypass env vars are active."""
    # this fixes runtime tests and is only microsecond slower than a file global
    return (
        os.getenv(f"{PROGRAM_ENV}_BYPASS_CAPTURE") == "1"
        or os.getenv("BYPASS_CAPTURE") == "1"
    )


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


def _should_log(level: str, current: str) -> bool:
    """Return True if a message at `level` should be emitted under
    the current log level `current`. Never logs if either level is 'silent'.
    """
    if level == "silent" or current == "silent":
        return False

    if level not in LEVEL_ORDER:
        safe_log(f"[LOGGER ERROR] ❌ Unknown log level: {level!r}")
        return False

    return LEVEL_ORDER.index(level) >= LEVEL_ORDER.index(current)


def _is_error_level(level: str) -> bool:
    """Return True if this log level represents a problem or warning."""
    return level in {"warning", "error", "critical"}


def _resolve_output_stream(level: str, file: TextIO | None) -> TextIO:
    """Decide whether to print to stdout or stderr, respecting BYPASS_CAPTURE."""
    if file is not None:
        return file

    if is_bypass_capture():
        return (
            getattr(sys, "__stderr__", sys.stderr)
            if _is_error_level(level)
            else getattr(sys, "__stdout__", sys.stdout)
        )
    return sys.stderr if _is_error_level(level) else sys.stdout


def _format_log_message(
    level: str,
    values: tuple[object, ...],
    sep: str,
    prefix: str | None,
) -> str:
    """Apply prefix and color formatting to the log message."""
    prefix_color = _LOG_PREFIXES_COLOR.get(level)
    msg_color = _LOG_MSG_COLOR.get(level)

    # Safely coerce prefix
    actual_prefix = prefix if prefix is not None else (_LOG_PREFIXES.get(level) or "")

    # Helper lambdas to treat None/"" as unset
    def is_set(value: str | None) -> bool:
        return bool(value and value.strip())

    # If no whole-line color, apply prefix color
    if not is_set(msg_color) and is_set(prefix_color):
        actual_prefix = colorize(actual_prefix, cast("str", prefix_color))

    message = sep.join([actual_prefix] + [str(v) for v in values])
    if is_set(msg_color):
        message = colorize(message, cast("str", msg_color))
    return message


def log(
    level: str,
    *values: object,
    sep: str = " ",
    end: str = "\n",
    file: TextIO | None = None,
    flush: bool = False,
    prefix: str | None = None,
) -> None:
    """Print a message respecting current log level and routing to
    stdout/stderr appropriately.

    - Prefix color and message color are mutually exclusive:
      if a message color is set, prefix color is skipped.
    - Safe for use in captured output; respects BYPASS_CAPTURE
    """
    if getattr(log, "_in_log", False):
        stream = cast("TextIO", sys.__stderr__)
        with suppress(Exception):
            stream.write("[LOGGER ERROR] ❌ Recursive log call suppressed\n")
        return
    log._in_log = True  # type: ignore[attr-defined] # noqa: SLF001

    try:
        if level not in LEVEL_ORDER:
            safe_log(f"[LOGGER ERROR] ❌ Unknown log level: {level!r}")
            return

        current_level = get_log_level()
        if not _should_log(level, current_level):
            return

        stream = _resolve_output_stream(level, file)
        message = _format_log_message(level, values, sep, prefix)
        print(message, end=end, file=stream, flush=flush)
    except Exception as e:  # noqa: BLE001
        safe_log(f"[LOGGER FAILURE] {e}")
    finally:
        log._in_log = False  # type: ignore[attr-defined] # noqa: SLF001


def colorize(text: str, color: str, *, use_color: bool | None = None) -> str:
    if use_color is None:
        use_color = current_runtime["use_color"]
    return f"{color}{text}{RESET}" if use_color else text
