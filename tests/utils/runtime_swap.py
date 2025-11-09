# tests/utils/runtime_swap.py
"""Shared test setup for project.

Each pytest run now targets a single runtime mode:
- Normal mode (default): uses src/pocket_build
- standalone mode: uses bin/script.py when RUNTIME_MODE=singlefile

Switch mode with: RUNTIME_MODE=singlefile pytest
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import pocket_build.meta as mod_meta
from tests.utils import PROJ_ROOT

from .test_trace import make_test_trace


if TYPE_CHECKING:
    from types import ModuleType


# --- helpers --------------------------------------------------------------------

TEST_TRACE = make_test_trace("🧬")


def _mode() -> str:
    return os.getenv("RUNTIME_MODE", "installed")


# ------------------------------------------------------------
# ⚙️ Auto-build helper for standalone script
# ------------------------------------------------------------
def ensure_standalone_script_up_to_date(root: Path) -> Path:
    """Rebuild `bin/script.py` if missing or outdated."""
    bin_path = root / "bin" / f"{mod_meta.PROGRAM_SCRIPT}.py"
    src_dir = root / "src" / f"{mod_meta.PROGRAM_PACKAGE}"
    builder = root / "dev" / "make_script.py"

    # If the output file doesn't exist or is older than any source file → rebuild.
    needs_rebuild = not bin_path.exists()
    if not needs_rebuild:
        bin_mtime_ns = bin_path.stat().st_mtime_ns
        for src_file in src_dir.rglob("*.py"):
            if src_file.stat().st_mtime_ns > bin_mtime_ns:
                needs_rebuild = True
                break

    if needs_rebuild:
        print("⚙️  Rebuilding standalone bundle (make_script.py)...")
        assert builder.is_file(), f"Expected builder script at {builder}"
        subprocess.run([sys.executable, str(builder)], check=True)  # noqa: S603
        # force mtime update in case contents identical
        bin_path.touch()
        assert bin_path.exists(), "❌ Failed to generate standalone script."

    return bin_path


# --- runtime_swap() ------------------------------------------------------------------


def runtime_swap() -> bool:
    """Pre-import hook — runs before any tests or plugins are imported.

    This is the right place
    to swap in the standalone single-file module if requested.
    """
    mode = _mode()
    if mode != "singlefile":
        return False  # Normal installed mode; nothing to do.

    bin_path = ensure_standalone_script_up_to_date(PROJ_ROOT)

    if not bin_path.exists():
        xmsg = (
            f"RUNTIME_MODE=singlefile but standalone script not found at {bin_path}.\n"
            f"Hint: run the bundler (e.g. `python dev/make_script.py`)."
        )
        raise pytest.UsageError(xmsg)

    # Nuke any already-imported pocket_build modules to avoid stale refs.
    for name in list(sys.modules):
        if name == "pocket_build" or name.startswith("pocket_build."):
            del sys.modules[name]

    # Load standalone script as the pocket_build package.
    spec = importlib.util.spec_from_file_location(mod_meta.PROGRAM_PACKAGE, bin_path)
    if not spec or not spec.loader:
        xmsg = f"Could not create import spec for {bin_path}"
        raise pytest.UsageError(xmsg)

    try:
        mod: ModuleType = importlib.util.module_from_spec(spec)
        sys.modules[mod_meta.PROGRAM_PACKAGE] = mod
        spec.loader.exec_module(mod)
        TEST_TRACE(f"Loaded standalone module from {bin_path}")
    except Exception as e:
        # Fail fast with context; this is a config/runtime problem.
        error_name = type(e).__name__
        xmsg = (
            f"Failed to import standalone module from {bin_path}.\n"
            f"Original error: {error_name}: {e}\n"
            f"Tip: rebuild the bundle and re-run."
        )
        raise pytest.UsageError(xmsg) from e

    TEST_TRACE(f"✅ Loaded standalone runtime early from {bin_path}")

    return True
