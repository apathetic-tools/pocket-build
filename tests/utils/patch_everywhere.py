# tests/utils/patch_everywhere.py

import sys
from collections.abc import Callable
from types import ModuleType
from typing import Any

import pytest

import pocket_build.meta as mod_meta

from .trace import TRACE


def patch_everywhere(
    mp: pytest.MonkeyPatch,
    mod_env: ModuleType | Any,
    func_name: str,
    replacement_func: Callable[..., object],
) -> None:
    """Replace a function everywhere it was imported.

    Patches both the defining module and any other loaded modules
    that have imported the same function object.
    Uses pytest's MonkeyPatch so patches are reverted automatically.
    """
    # --- Sanity checks ---
    func = getattr(mod_env, func_name, None)
    if func is None:
        xmsg = f"Could not find {func_name!r} on {mod_env!r}"
        raise TypeError(xmsg)

    mod_name = getattr(mod_env, "__name__", type(mod_env).__name__)

    # Patch in the defining module
    mp.setattr(mod_env, func_name, replacement_func)
    TRACE(f"Patched {mod_name}.{func_name}")

    # Walk all loaded modules and patch any that imported the same object
    for m in list(sys.modules.values()):
        if m is mod_env or not hasattr(m, "__dict__"):
            continue

        # skip irrelevant stdlib or third-party modules for performance
        name = getattr(m, "__name__", "")
        if not name.startswith(mod_meta.PROGRAM_PACKAGE):
            continue

        for k, v in list(m.__dict__.items()):
            if v is func:
                mp.setattr(m, k, replacement_func)
                TRACE(f"  also patched {name}.{k}")
