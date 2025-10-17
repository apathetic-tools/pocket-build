# tests/utils/monkeypatch_def.py

from types import FunctionType, ModuleType
from typing import Callable

from _pytest.monkeypatch import MonkeyPatch

from tests.conftest import RuntimeLike

from .trace import TRACE


def patch_runtime_function(
    mp: MonkeyPatch,
    mod: ModuleType,
    runtime_env: RuntimeLike,
    func_name: str,
    replacement_func: Callable[..., object],
) -> None:
    """Patch a function across modular/single-file runtimes deterministically.

    Attempts patching in this order:
      1. Module attribute (e.g. pocket_build.actions)
      2. Single-file globals (runtime_env.main.__globals__)
    Fails loudly if neither is found — no silent fallback.
    """

    # --- verify parameters are correct shape ---
    main_func = getattr(runtime_env, "main", None)
    if not isinstance(main_func, FunctionType):
        raise TypeError(f"runtime_env.main is not a function (got {type(main_func)})")

    globals_dict: dict[str, object] | None = getattr(main_func, "__globals__", None)
    if globals_dict is None:
        # Frozen environments (e.g. PyInstaller) may strip __globals__
        raise RuntimeError(
            f"Cannot patch {func_name!r}: runtime_env.main has no __globals__ "
            "(possibly running in a frozen or restricted environment)."
        )

    # --- do actual patching ---
    if hasattr(mod, func_name):
        TRACE(f"Patched {mod.__name__}.{func_name}")
        mp.setattr(mod, func_name, replacement_func)
        return

    if func_name in globals_dict:
        TRACE(f"Patched main.__globals__[{func_name!r}]")
        mp.setitem(globals_dict, func_name, replacement_func)
        return

    # --- failed; do diagnostics and raise error ---
    mode_hint: str = "unknown"
    mode_fix: str = ""
    if "single" in getattr(runtime_env, "__name__", ""):
        mode_hint = "single-file"
        mode_fix = (
            f"Did you add the file containing `{func_name}`"
            " to make_script.ORDER and regenerate the single-file script?"
        )
    elif getattr(mod, "__package__", "").startswith("pocket_build"):
        mode_hint = "modular"
        mode_fix = f"Did you import `{func_name}` from the correct module?"

    # ❌ Explicit failure: avoid silently patching the wrong namespace
    raise RuntimeError(
        f"Failed to patch {func_name!r} in {mode_hint} mode"
        f" — checked {mod.__name__}"
        f" and globals of {getattr(main_func, '__module__', '?')}."
        f" {mode_fix}"
    )
