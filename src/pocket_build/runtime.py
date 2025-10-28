# pocket_build/runtime.py
"""Holds live runtime context shared across modules (e.g., log level, color flags)."""

from __future__ import annotations

from .types import Runtime
from .utils import should_use_color

current_runtime: Runtime = {
    "log_level": "info",
    "use_color": should_use_color(),
}
