# pocket_build/runtime.py
"""Holds live runtime context shared across modules (e.g., log level, color flags)."""

import os
from typing import TypedDict

from .constants import DEFAULT_LOG_LEVEL
from .meta import PROGRAM_ENV
from .utils import should_use_color


class Runtime(TypedDict):
    log_level: str
    use_color: bool


def _initial_log_level() -> str:
    return (
        os.getenv(f"{PROGRAM_ENV}_LOG_LEVEL")
        or os.getenv("LOG_LEVEL")
        or DEFAULT_LOG_LEVEL
    )


current_runtime: Runtime = {
    "log_level": _initial_log_level(),
    "use_color": should_use_color(),
}
