# tests/conftest.py
"""
Shared test setup for project.

Each pytest run now targets a single runtime mode:
- Normal mode (default): uses src/pocket_build
- Single-file mode: uses bin/script.py when RUNTIME_MODE=singlefile

Switch mode with: RUNTIME_MODE=singlefile pytest
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Generator

import pytest

from pocket_build.meta import PROGRAM_PACKAGE, PROGRAM_SCRIPT


def pytest_report_header(config: pytest.Config) -> str:
    mode: str = os.getenv("RUNTIME_MODE", "module")
    return f"Runtime mode: {mode}"


# ------------------------------------------------------------
# ⚙️ Auto-build helper for bundled script
# ------------------------------------------------------------
def ensure_bundled_script_up_to_date(root: Path) -> Path:
    """Rebuild `bin/script.py` if missing or outdated."""
    bin_path = root / "bin" / f"{PROGRAM_SCRIPT}.py"
    src_dir = root / "src" / f"{PROGRAM_PACKAGE}"
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


# ------------------------------------------------------------
# 🔁 Fixture: load either the module or the bundled script
# ------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def runtime_env() -> Generator[None, None, None]:
    """
    Automatically load the correct runtime module based on RUNTIME_MODE.

    When RUNTIME_MODE=singlefile, replaces `<package name>` in sys.modules
    with the single-file bundled version. Otherwise uses the normal package.
    """
    mode: str = os.getenv("RUNTIME_MODE", "module")
    root: Path = Path(__file__).resolve().parent.parent

    if mode == "module":
        yield
        return

    bin_path: Path = ensure_bundled_script_up_to_date(root)
    spec = importlib.util.spec_from_file_location(PROGRAM_PACKAGE, bin_path)
    assert spec and spec.loader, f"Failed to load spec from {bin_path}"

    mod: ModuleType = importlib.util.module_from_spec(spec)
    sys.modules[PROGRAM_PACKAGE] = mod
    spec.loader.exec_module(mod)
    yield
    return


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Filter and record runtime-specific tests for later reporting."""
    mode = os.getenv("RUNTIME_MODE", "module")

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
            # Make path relative to project rootdir
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
