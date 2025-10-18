# tests/utils/patch_runtime_function.py

import importlib
import inspect
import sys
from types import FunctionType, ModuleType
from typing import Any, Callable

from _pytest.monkeypatch import MonkeyPatch

from tests.conftest import RuntimeLike

from .trace import TRACE


def patch_runtime_function_func(
    mp: MonkeyPatch,
    runtime_env: RuntimeLike | None,
    func_target: FunctionType,
    replacement_func: Callable[..., object],
) -> None:
    _patch_runtime_function(
        mp=mp,
        runtime_env=runtime_env,
        func_target=func_target,
        replacement_func=replacement_func,
    )


def patch_runtime_function_mod(
    mp: MonkeyPatch,
    runtime_env: RuntimeLike | None,
    module_env: ModuleType | Any,
    func_name: str,
    replacement_func: Callable[..., object],
) -> None:
    _patch_runtime_function(
        mp=mp,
        runtime_env=runtime_env,
        module_env=module_env,
        func_name=func_name,
        replacement_func=replacement_func,
    )


def patch_runtime_function_globals(
    mp: MonkeyPatch,
    runtime_env: RuntimeLike,
    module_name: str,
    func_name: str,
    replacement_func: Callable[..., object],
) -> None:
    _patch_runtime_function(
        mp=mp,
        runtime_env=runtime_env,
        module_name=module_name,
        func_name=func_name,
        replacement_func=replacement_func,
    )


def _patch_runtime_function(
    *,
    mp: MonkeyPatch,
    runtime_env: RuntimeLike | None = None,
    module_name: str | None = None,
    module_env: ModuleType | Any | None = None,
    func_name: str | None = None,
    func_target: FunctionType | None = None,
    replacement_func: Callable[..., object],
) -> None:
    """Patch a function across modular, single-file,
    or direct-module runtimes deterministically.

    Order of preference:
    1. Single-file: runtime_env.main.__globals__
    2. Modular: runtime_env.<module_name>.__globals__
    3. Direct: module_env.<func_name> or func_target
    Fails loudly otherwise.
    """

    # --- sanity check parameter combinations ---
    if func_target is None and func_name is None:
        raise ValueError(
            "You must provide either func_target (the actual function object)"
            " or func_name (the name of the function to patch)."
        )

    if runtime_env is None and module_env is None and func_target is None:
        raise ValueError(
            "Cannot patch: you must provide at least one of"
            " runtime_env, module_env, or func_target"
            " so that the target module can be determined."
        )

    # Priority: runtime_env → module_env → func_target
    # We prefer runtime_env to ensure single-file builds are tested when available.

    resolve_func_name: str | None = func_name
    resolve_func_target: FunctionType | None = func_target

    # 1. if we have runtime_env, check runtime_env.main.__globals__
    #  we need either func_name
    #  or func_target

    # --- runtime_env only needs func_name ---
    if resolve_func_name is None and resolve_func_target is not None:
        resolve_func_name = getattr(resolve_func_target, "__name__", None)
        if resolve_func_name is None:
            raise ValueError(
                f"Cannot determine function name from {resolve_func_target!r}"
            )

    # sanity; we should have the function name now
    if resolve_func_name is None:
        raise ValueError("Cannot determine function name to patch.")

    if runtime_env is not None:
        # --- verify main is callable ---
        main_func = getattr(runtime_env, "main", None)
        if not isinstance(main_func, FunctionType):
            raise TypeError(
                f"runtime_env.main is not a function (got {type(main_func)})"
            )

        # --- single-file and toplevel module patch ---
        main_dict = getattr(main_func, "__globals__", {})
        if resolve_func_name in main_dict:
            TRACE(f"Patched main.__globals__[{resolve_func_name!r}]")
            mp.setitem(main_dict, resolve_func_name, replacement_func)
            return

    # 2. try to find it on the module
    #   we need any of module_env,
    #   or func_target
    #   or runtime_env and module_name

    # --- now we need the module and module name too
    resolve_mod_env: ModuleType | Any | None = module_env
    resolve_mod_name: str | None = module_name

    # try to get the module from func_target
    if resolve_mod_env is None and resolve_func_target is not None:
        # it will raise it's own exceptions on failure
        (resolve_mod_env, resolve_mod_name) = _get_module_for_function(
            resolve_func_target
        )

    # Prefer runtime_env w/ module_name when available, even if module_env is passed.
    if runtime_env is not None and resolve_mod_name is not None:
        # --- verify module exists and has func_name ---
        # Try full path, then fallback to short name
        prev_resolve_mod_name = resolve_mod_name
        try_names = [resolve_mod_name, resolve_mod_name.split(".")[-1]]
        for name in try_names:
            candidate = getattr(runtime_env, name, None)
            if candidate is not None:
                resolve_mod_name = name
                resolve_mod_env = candidate
                break

        if resolve_mod_env is None:
            raise AttributeError(
                f"runtime_env does not have module {resolve_mod_name!r} "
                f"(also tried {resolve_mod_name.split('.')[-1]!r})"
            )

        if prev_resolve_mod_name != resolve_mod_name:
            TRACE(
                f"Resolved module name: {prev_resolve_mod_name!r}"
                f" → {resolve_mod_name!r}"
            )

    # Explicit post-check fallback — only if runtime_env failed
    # NOTE: this one is a bit weird, I'm not certain it is needed
    if resolve_mod_env is None and module_env is not None:
        TRACE(f"Falling back to module_env for {resolve_mod_name!r}")
        resolve_mod_env = module_env

    if resolve_mod_env is None:
        raise AttributeError(
            f"Could not resolve module {resolve_mod_name!r} "
            "from runtime_env, module_env, or func_target."
        )

    # ensure we have module name for messages
    if resolve_mod_env is not None and resolve_mod_name is None:
        resolve_mod_name = getattr(resolve_mod_env, "__module__", None)
        if resolve_mod_name is None:
            raise ValueError(f"Cannot determine module name from {resolve_mod_env!r}")

    # --- make sure function is on the module ---
    if resolve_mod_env is not None:
        resolve_func_target = getattr(resolve_mod_env, resolve_func_name, None)
        if resolve_func_target is None:
            source_hint = (
                f"runtime_env {getattr(runtime_env, '__name__', type(runtime_env))!r} "
                "and module_env both"
                if runtime_env and module_env
                else ("runtime_env" if runtime_env else "module_env")
            )
            raise ValueError(
                f"Could not find function {resolve_func_name!r} "
                f"on {source_hint} ({resolve_mod_env!r})."
            )

    # --- modular patch ---
    # sanity check that we resolved a func_target at this point
    if resolve_func_target is None:
        raise ValueError(
            "Cannot patch without func_target"
            " — no module_env, func_target, or runtime_env resolved"
        )

    mod_dict: dict[str, object] | None = getattr(
        resolve_func_target, "__globals__", None
    )
    if not isinstance(mod_dict, dict):
        raise TypeError(
            f"Target {resolve_func_target!r} has no __globals__ mapping; "
            "cannot be patched by monkeypatch."
        )
    assert isinstance(mod_dict, dict)

    if resolve_func_name in mod_dict:
        TRACE(f"Patched {resolve_mod_name!r}.{resolve_func_name!r}")
        mp.setitem(mod_dict, resolve_func_name, replacement_func)
        return

    # --- failed; do diagnostics and raise error ---
    mode_hint: str = "unknown"
    mode_fix: str = ""

    # just in case
    if resolve_mod_name is None:
        resolve_mod_name = "<unknown>"

    if runtime_env and "single" in getattr(runtime_env, "__name__", ""):
        mode_hint = "single-file"
        mode_fix = (
            f"Did you add the file containing {resolve_func_name!r}"
            " to make_script.ORDER and regenerate the single-file script?"
        )
    else:
        mode_hint = "modular"
        mode_fix = f"Did you import {resolve_func_name!r} from the correct module?"

    # ❌ Explicit failure: avoid silently patching the wrong namespace
    raise RuntimeError(
        f"Failed to patch {resolve_func_name!r} in {mode_hint} mode"
        f" — checked {resolve_mod_name!r}"
        " and main but did not find it in their globals."
        f" {mode_fix}"
    )


def _get_module_for_function(func: FunctionType) -> tuple[ModuleType | Any, str]:
    """Return the actual module object for a given function."""
    # because other types can proxy for ModuleType we don't require it
    if not inspect.isfunction(func):
        raise TypeError(f"Target is not a function: {func!r}")

    # Prefer the global namespace hint
    mod_name: str | None = func.__globals__.get("__name__") or getattr(
        func, "__module__", None
    )
    if not mod_name:
        raise ValueError(f"Cannot determine module for function {func!r}")

    module = sys.modules.get(mod_name)
    if module is None:
        try:
            module = importlib.import_module(mod_name)
        except ModuleNotFoundError:
            raise ValueError(
                f"Cannot determine module {mod_name!r} for function {func!r}"
            )
    return module, mod_name
