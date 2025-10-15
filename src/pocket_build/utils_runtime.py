# src/pocket_build/utils_runtime.py

import os
import sys
from typing import TextIO, cast

from .meta import PROGRAM_ENV
from .runtime import current_runtime

# Terminal colors (ANSI)
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

LEVEL_ORDER = ["critical", "error", "warning", "info", "debug", "trace"]

LOG_PREFIXES: dict[str, str | None] = {
    "critical": "💥 ",
    "error": "❌ ",
    "warning": "⚠️ ",
    "info": None,
    "debug": "[DEBUG] ",
    "trace": "[TRACE] ",
}
LOG_PREFIXES_COLOR: dict[str, str | None] = {
    "critical": None,
    "error": None,
    "warning": None,
    "info": None,
    "debug": GREEN,
    "trace": YELLOW,
}
LOG_MSG_COLOR: dict[str, str | None] = {
    "critical": None,
    "error": None,
    "warning": None,
    "info": None,
    "debug": None,
    "trace": None,
}


def is_bypass_capture() -> bool:
    """Return True if capture bypass env vars are active."""
    # this fixes runtime tests and is only microsecond slower than a file global
    return (
        os.getenv(f"{PROGRAM_ENV}_BYPASS_CAPTURE") == "1"
        or os.getenv("BYPASS_CAPTURE") == "1"
    )


def should_log(level: str, current: str) -> bool:
    return LEVEL_ORDER.index(level) <= LEVEL_ORDER.index(current)


def is_error_level(level: str) -> bool:
    """Return True if this log level represents a problem or warning."""
    return level in {"warning", "error", "critical"}


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
    - Safe for use in captured output; respects BYPASS_CAPTURE"""
    current_level = current_runtime["log_level"]
    if not should_log(level, current_level):
        return

    # Determine correct output stream
    if file is None and is_bypass_capture():
        file = (
            getattr(sys, "__stderr__", sys.stderr)
            if is_error_level(level)
            else getattr(sys, "__stdout__", sys.stdout)
        )
    elif file is None:
        file = sys.stderr if is_error_level(level) else sys.stdout

    prefix_color = LOG_PREFIXES_COLOR.get(level)
    msg_color = LOG_MSG_COLOR.get(level)

    # Safely coerce prefix
    actual_prefix = prefix if prefix is not None else (LOG_PREFIXES.get(level) or "")

    # Helper lambdas to treat None/"" as unset
    def is_set(value: str | None) -> bool:
        return bool(value and value.strip())

    # If no whole-line color, apply prefix color
    if not is_set(msg_color) and is_set(prefix_color):
        actual_prefix = colorize(actual_prefix, cast(str, prefix_color))

    message = sep.join([actual_prefix] + [str(v) for v in values])

    if is_set(msg_color):
        message = colorize(message, cast(str, msg_color))

    print(message, end=end, file=file, flush=flush)


def colorize(text: str, color: str, use_color: bool | None = None) -> str:
    if use_color is None:
        use_color = current_runtime["use_color"]
    return f"{color}{text}{RESET}" if use_color else text
