# tests/conftest.py
"""
Shared test setup for project.

Each pytest run now targets a single runtime mode:
- Normal mode (default): uses src/pocket_build
- Single-file mode: uses bin/script.py when RUNTIME_MODE=singlefile

Switch mode with: RUNTIME_MODE=singlefile pytest
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pytest import Config, Item as PytestItem

import pocket_build.meta as mod_meta
from tests.utils import make_trace, runtime_swap

TRACE = make_trace("⚡️")

# early jank hook
runtime_swap()


def _mode() -> str:
    return os.getenv("RUNTIME_MODE", "module")


def pytest_report_header(config: Config) -> str:
    mode = _mode()
    return f"Runtime mode: {mode}"


# ------------------------------------------------------------
# ⚙️ Auto-build helper for bundled script
# ------------------------------------------------------------
def ensure_bundled_script_up_to_date(root: Path) -> Path:
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
        print("⚙️  Rebuilding single-file bundle (make_script.py)...")
        subprocess.run([sys.executable, str(builder)], check=True)
        # force mtime update in case contents identical
        bin_path.touch()
        assert bin_path.exists(), "❌ Failed to generate bundled script."

    return bin_path


def pytest_collection_modifyitems(
    config: Config,
    items: list[PytestItem],
) -> None:
    """Filter and record runtime-specific tests for later reporting.
    also automatically skips debug tests unless asked for"""

    # --- debug filtering ---
    # detect if the user is filtering for debug tests
    keywords = config.getoption("-k") or ""
    running_debug = "debug" in keywords.lower()

    if running_debug:
        return  # user explicitly requested them, don't skip

    for item in items:
        if "debug" in item.keywords:
            item.add_marker(
                pytest.mark.skip(reason="Skipped debug test (use -k debug to run)")
            )

    # --- mode-specific tests ---
    mode = _mode()

    # file → number of tests
    included_map: dict[str, int] = {}
    root = str(config.rootpath)
    testpaths: list[str] = config.getini("testpaths") or []

    # Identify mode-specific files by a custom variable defined at module scope
    for item in list(items):
        mod = item.getparent(pytest.Module)
        if mod is None or not hasattr(mod, "obj"):
            continue

        runtime_marker = getattr(mod.obj, "__runtime_mode__", None)

        if runtime_marker and runtime_marker != mode:
            items.remove(item)
            continue

        if runtime_marker and runtime_marker == mode:
            file_path = str(item.fspath)
            # Make path relative to project root dir
            if file_path.startswith(root):
                file_path = os.path.relpath(file_path, root)
                for tp in testpaths:
                    if file_path.startswith(tp.rstrip("/") + os.sep):
                        file_path = file_path[len(tp.rstrip("/") + os.sep) :]
                        break

            included_map[file_path] = included_map.get(file_path, 0) + 1

    # Store results for later reporting
    config._included_map = included_map  # type: ignore[attr-defined]
    config._runtime_mode = mode  # type: ignore[attr-defined]


def pytest_unconfigure(config: pytest.Config) -> None:
    """Print summary of included runtime-specific tests at the end."""
    included_map: dict[str, int] = getattr(config, "_included_map", {})
    mode = getattr(config, "_runtime_mode", "module")

    if not included_map:
        return

    total_tests = sum(included_map.values())
    print(
        f"🧪 Included {total_tests} {mode}-specific tests"
        f" across {len(included_map)} files:",
    )
    for path, count in sorted(included_map.items()):
        print(f"   • ({count}) {path}")
