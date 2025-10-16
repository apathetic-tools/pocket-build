# tests/utils/trace.py

import builtins
import importlib
import os

TRACE_ENABLED = os.environ.get("TRACE", "").lower() in {"1", "true", "yes"}


def TRACE(label: str, *args: object):
    """Lightweight synchronized print for debugging across threads/processes."""
    if not TRACE_ENABLED:
        return

    # Avoid using the possibly monkeypatched "time" from sys.modules
    _real_time = importlib.import_module("time")  # guaranteed pristine copy

    ts = _real_time.monotonic()
    # builtins.print more reliable than sys.stdout.write + sys.stdout.flush
    builtins.print(f"[TRACE {ts:.6f}] {label}:", *args, flush=True)
