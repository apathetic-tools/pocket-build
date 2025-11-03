# tests/utils/trace.py
"""Unified trace logger for pytest diagnostics.

Uses monotonic timestamps for ordering and writes directly to sys.__stderr__
to bypass pytest’s capture system. This makes output visible even during
setup or import-time execution. Enable by setting TEST_TRACE=1 (or 'true', 'yes').
"""

import builtins
import importlib
import os
import sys
from collections.abc import Callable
from typing import Any


# Flag for quick runtime enable/disable
TEST_TRACE_ENABLED = os.getenv("TEST_TRACE", "").lower() in {"1", "true", "yes"}

# Lazy, safe import — avoids patched time modules
#   in environments like pytest or eventlet
_real_time = importlib.import_module("time")


def make_test_trace(icon: str = "🧪") -> Callable[..., Any]:
    def local_trace(label: str, *args: Any) -> Any:
        return TEST_TRACE(label, *args, icon=icon)

    return local_trace


def TEST_TRACE(label: str, *args: Any, icon: str = "🧪") -> None:  # noqa: N802
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
