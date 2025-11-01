# pocket_build/runtime.py
"""Holds live runtime context shared across modules (e.g., log level, color flags)."""

from typing import TypedDict

from .utils import should_use_color


class Runtime(TypedDict):
    log_level: str
    use_color: bool


current_runtime: Runtime = {
    "log_level": "info",
    "use_color": should_use_color(),
}
