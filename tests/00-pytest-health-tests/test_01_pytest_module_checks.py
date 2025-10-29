# tests/test_01_pytest_module_checks.py
"""
Ensures pytest is running against the intended runtime (module vs singlefile)
and that Python’s import cache (`sys.modules`) points to the correct sources.

If RUNTIME_MODE=singlefile, all modules must resolve to the stitched file.
Otherwise, they must resolve to the src tree.
"""

import importlib
import inspect
import os
import pkgutil
import sys
from pathlib import Path

import pytest

import pocket_build as app_package
import pocket_build.meta as mod_meta
import pocket_build.utils as mod_utils
from tests.utils import make_trace

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TRACE = make_trace("🪞")

PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_ROOT = PROJ_ROOT / "src"
BIN_ROOT = PROJ_ROOT / "bin"


def list_important_modules() -> list[str]:
    """Return all importable submodules under the package, if available."""
    important: list[str] = []
    if not hasattr(app_package, "__path__"):
        TRACE("pkgutil.walk_packages skipped — single-file runtime (no __path__)")
        important.append(app_package.__name__)
    else:
        for _, name, _ in pkgutil.walk_packages(
            app_package.__path__, app_package.__name__ + "."
        ):
            important.append(name)

    return important


def dump_snapshot(*, include_full: bool = False) -> None:
    """Prints a summary of key modules and (optionally) a full sys.modules dump."""
    mode: str = os.getenv("RUNTIME_MODE", "module")

    TRACE("========== SNAPSHOT ===========")
    TRACE(f"RUNTIME_MODE={mode}")

    important_modules = list_important_modules()

    # Summary: the modules we care about most
    TRACE("======= IMPORTANT MODULES =====")
    for name in important_modules:
        mod = sys.modules.get(name)
        if not mod:
            continue
        origin = getattr(mod, "__file__", None)
        TRACE(f"  {name:<25} {origin}")

    if include_full:
        # Full origin dump
        TRACE("======== OTHER MODULES ========")
        for name, mod in sorted(sys.modules.items()):
            if name in important_modules:
                continue
            origin = getattr(mod, "__file__", None)
            TRACE(f"  {name:<38} {origin}")

    TRACE("===============================")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pytest_runtime_cache_integrity() -> None:
    """Tests top-of-file module imports in a test file to see if it has a stale cache"""
    # --- setup ---
    mode = os.getenv("RUNTIME_MODE", "unknown")
    utils_file = str(inspect.getsourcefile(mod_utils))
    expected_script = BIN_ROOT / f"{mod_meta.PROGRAM_SCRIPT}.py"

    # --- execute ---
    TRACE(f"RUNTIME_MODE={mode}")
    TRACE(f"{mod_meta.PROGRAM_PACKAGE}.utils  → {utils_file}")

    if os.getenv("TRACE"):
        dump_snapshot()
    stitched = mod_utils.is_stitched()

    if mode == "singlefile":
        # --- verify singlefile ---
        # what does the module itself think?
        assert stitched

        # path peeks
        assert utils_file.startswith(str(BIN_ROOT)), f"{utils_file} not in bin/"

        # exists
        assert expected_script.exists(), f"Expected bundled script at {expected_script}"

        # troubleshooting info
        TRACE(
            f"sys.modules['{mod_meta.PROGRAM_PACKAGE}']"
            f" = {sys.modules.get(mod_meta.PROGRAM_PACKAGE)}"
        )
        TRACE(
            f"sys.modules['{mod_meta.PROGRAM_PACKAGE}.utils']"
            f" = {sys.modules.get(f'{mod_meta.PROGRAM_PACKAGE}.utils')}"
        )

    else:
        # --- verify module ---
        # what does the module itself think?
        assert not stitched

        # path peeks
        assert utils_file.startswith(str(SRC_ROOT)), f"{utils_file} not in src/"

    # --- verify both ---
    important_modules = list_important_modules()
    for submodule in important_modules:
        mod = importlib.import_module(f"{submodule}")
        path = Path(inspect.getsourcefile(mod) or "")
        if mode == "singlefile":
            assert path.samefile(expected_script), f"{submodule} loaded from {path}"
        else:
            assert path.is_relative_to(SRC_ROOT), f"{submodule} not in src/: {path}"


@pytest.mark.debug
def test_debug_dump_all_module_origins() -> None:
    """Optional forensic dump of all loaded modules.

    Useful when debugging import leakage or stale sys.modules cache.
    Always fails intentionally to force pytest to show TRACE output.

    TRACE=1 poetry run pytest -k debug -s
    RUNTIME_MODE=singlefile TRACE=1 poetry run pytest -k debug -s
    """

    # --- verify ---

    # dump everything we know
    dump_snapshot(include_full=True)

    # show total module count for quick glance
    count = sum(1 for name in sys.modules if name.startswith(mod_meta.PROGRAM_PACKAGE))
    TRACE(f"Loaded {count} {mod_meta.PROGRAM_PACKAGE} modules total")

    # force visible failure for debugging runs
    raise AssertionError(
        f"Intentional fail — {count} {mod_meta.PROGRAM_PACKAGE} modules listed above."
    )
