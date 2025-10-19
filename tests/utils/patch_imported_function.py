# tests/utils/patch_imported_function.py

import inspect
import sys
from types import FunctionType, ModuleType
from typing import Callable

from _pytest.monkeypatch import MonkeyPatch

from .trace import TRACE


def patch_imported_function(
    mp: MonkeyPatch,
    func: FunctionType,
    replacement: Callable[..., object],
) -> None:
    """Monkeypatch a function given its imported reference.

    Works safely across modular and single-file (shimmed) runtimes.
    """

    # --- Sanity checks ---
    if not inspect.isfunction(func):
        raise TypeError(f"Expected a function, got {type(func).__name__}: {func!r}")

    mod_name = getattr(func, "__module__", None)
    func_name = getattr(func, "__name__", None)

    if not mod_name or not isinstance(mod_name, str):
        raise ValueError(f"Function {func!r} has no valid __module__ attribute")
    if not func_name or not isinstance(func_name, str):
        raise ValueError(f"Function {func!r} has no valid __name__ attribute")

    mod = sys.modules.get(mod_name)
    if not isinstance(mod, ModuleType):
        raise ValueError(f"Cannot resolve real module for {func_name!r} ({mod_name!r})")

    # --- Patch via resolved module ---
    TRACE(f"Patched {mod.__name__}.{func_name}")
    mp.setattr(mod, func_name, replacement)

    # Optional redundancy: for safety with shims or submodules
    if mod_name.startswith("pocket_build.") and mod_name in sys.modules:
        mp.setattr(f"{mod_name}.{func_name}", replacement, raising=False)

    # Also patch any importer that has already bound it
    for m in list(sys.modules.values()):
        # already patched this one
        if m is mod:
            continue

        if not hasattr(m, "__dict__"):
            continue

        g = m.__dict__

        # skip irrelevant stdlib or third-party modules for performance
        if not getattr(m, "__name__", "").startswith("pocket_build"):
            continue

        if g.get(func_name) is func:
            TRACE(f"  also patched {m.__name__}.{func_name}")
            mp.setitem(g, func_name, replacement)
