# tests/utils/patch_everywhere.py

import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

import pocket_build.meta as mod_meta

from .strip_common_prefix import strip_common_prefix
from .test_trace import TEST_TRACE


_PATCH_PATH = Path(__file__).resolve()


def _short_path(path: str | None) -> str:
    if not path:
        return "n/a"
    return strip_common_prefix(path, _PATCH_PATH)


def patch_everywhere(
    mp: pytest.MonkeyPatch,
    mod_env: ModuleType | Any,
    func_name: str,
    replacement_func: Callable[..., object],
) -> None:
    """Replace a function everywhere it was imported.

    Works in both package and stitched single-file runtimes.
    Walks sys.modules once and handles:
      • the defining module
      • any other module that imported the same function object
      • any freshly reloaded stitched modules (heuristic: path under /bin/)
    """
    # --- Sanity checks ---
    func = getattr(mod_env, func_name, None)
    if func is None:
        xmsg = f"Could not find {func_name!r} on {mod_env!r}"
        raise TypeError(xmsg)

    mod_name = getattr(mod_env, "__name__", type(mod_env).__name__)

    # Patch in the defining module
    mp.setattr(mod_env, func_name, replacement_func)
    TEST_TRACE(f"Patched {mod_name}.{func_name}")

    stitch_hints = {"/bin/", "standalone", f"{mod_meta.PROGRAM_SCRIPT}.py"}
    package_prefix = mod_meta.PROGRAM_PACKAGE
    patched_ids: set[int] = set()

    for m in list(sys.modules.values()):
        if (
            m is mod_env
            or not isinstance(m, ModuleType)  # type: ignore[unnecessary-isinstance]
            or not hasattr(m, "__dict__")
        ):
            continue

        # skip irrelevant stdlib or third-party modules for performance
        name = getattr(m, "__name__", "")
        if not name.startswith(package_prefix):
            continue

        did_patch = False

        # 1) Normal case: module imported the same object
        for k, v in list(m.__dict__.items()):
            if v is func:
                mp.setattr(m, k, replacement_func)
                did_patch = True

        # 2) Single-file case: reloaded stitched modules
        #    whose __file__ path matches heuristic
        path = getattr(m, "__file__", "") or ""
        if any(h in path for h in stitch_hints) and hasattr(m, func_name):
            mp.setattr(m, func_name, replacement_func)
            did_patch = True

        if did_patch and id(m) not in patched_ids:
            TEST_TRACE(f"  also patched {name} (path={_short_path(path)})")
            patched_ids.add(id(m))
