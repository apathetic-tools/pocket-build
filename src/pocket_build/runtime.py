# pocket_build/runtime.py
"""Holds live runtime context shared across modules (e.g., log level, color flags)."""

from .types import Runtime

current_runtime: Runtime = {
    "log_level": "info",
}
