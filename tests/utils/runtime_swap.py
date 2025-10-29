# tests/utils/runtime_swap.py
"""
Shared test setup for project.

Each pytest run now targets a single runtime mode:
- Normal mode (default): uses src/pocket_build
- Single-file mode: uses bin/script.py when RUNTIME_MODE=singlefile

Switch mode with: RUNTIME_MODE=singlefile pytest
"""

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

from pytest import UsageError

import pocket_build.meta as mod_meta

from .trace import make_trace

TRACE = make_trace("🧬")
PROJ_ROOT = Path(__file__).resolve().parent.parent.parent


def _mode() -> str:
    return os.getenv("RUNTIME_MODE", "module")


def runtime_swap() -> bool:
    """Pre-import hook — runs before any tests or plugins are imported.

    This is the right place
    to swap in the stitched single-file module if requested.
    """
    mode = _mode()
    if mode != "singlefile":
        return False  # Normal module mode; nothing to do.

    # bin_path = ensure_bundled_script_up_to_date(root)
    bin_path = PROJ_ROOT / "bin" / f"{mod_meta.PROGRAM_SCRIPT}.py"

    if not bin_path.exists():
        msg = (
            f"RUNTIME_MODE=singlefile but bundled script not found at {bin_path}.\n"
            f"Hint: run the bundler (e.g. `python dev/make_script.py`)."
        )
        raise UsageError(msg)

    # Nuke any already-imported pocket_build modules to avoid stale refs.
    for name in list(sys.modules):
        if name == "pocket_build" or name.startswith("pocket_build."):
            del sys.modules[name]

    # Load stitched script as the pocket_build package.
    spec = importlib.util.spec_from_file_location(mod_meta.PROGRAM_PACKAGE, bin_path)
    if not spec or not spec.loader:
        raise UsageError(f"Could not create import spec for {bin_path}")

    try:
        mod: ModuleType = importlib.util.module_from_spec(spec)
        sys.modules[mod_meta.PROGRAM_PACKAGE] = mod
        spec.loader.exec_module(mod)
        TRACE(f"Loaded stitched module from {bin_path}")
    except Exception as e:
        # Fail fast with context; this is a config/runtime problem.
        raise UsageError(
            f"Failed to import stitched module from {bin_path}.\n"
            f"Original error: {type(e).__name__}: {e}\n"
            f"Tip: rebuild the bundle and re-run."
        ) from e

    # # Alias submodules to the same object for consistent imports
    # for sub in [
    #     "actions", "build", "cli", "config", "config_resolve", "config_validate",
    #     "constants", "meta", "runtime", "types",
    #     "utils", "utils_types", "utils_using_runtime",
    # ]:
    #     sys.modules[f"{PROGRAM_PACKAGE}.{sub}"] = mod

    TRACE(f"✅ Loaded stitched runtime early from {bin_path}")

    return True
