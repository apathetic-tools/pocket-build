# pocket_build/runtime.py
"""Holds live runtime context shared across modules (e.g., log level, color flags)."""

from .types import Runtime
from .utils_core import should_use_color

current_runtime: Runtime = {
    "log_level": "info",
    "use_color": should_use_color(),
}
