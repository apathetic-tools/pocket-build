# tests/conftest.py
"""
Shared test fixture for pocket-build.

This lets all tests transparently run against both:
1. The modular package (`src/pocket_build`)
2. The bundled single-file script (`bin/pocket-build.py`)

Each test receives a `pocket_build_env` fixture that behaves like the module.

If the bundled script is missing or older than the source files,
it is automatically rebuilt using `dev/make_script.py`.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Protocol

import pytest

# Ensure the src/ folder is on sys.path (so "import pocket_build" works)
ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

# ruff: noqa: E402 — import after sys.path modification
from pocket_build.types import BuildConfig

# --- Prevent pytest from scanning build output folders ---
# These directories can contain auto-generated code or duplicated tests.
BAD_DIRS = ["dist", "tmp-dist", "bin"]

for bad in BAD_DIRS:
    bad_path = Path(bad).resolve()
    sys.path = [p for p in sys.path if bad not in p]


# ------------------------------------------------------------
# 🧩 Protocol for type safety & editor autocompletion
# ------------------------------------------------------------
class PocketBuildLike(Protocol):
    """Subset of functions shared by both implementations."""

    # --- utils ---
    def load_jsonc(self, path: Path) -> Dict[str, Any]: ...
    def is_excluded(
        self,
        path: Path,
        exclude_patterns: List[str],
        root: Path,
    ) -> bool: ...

    # --- config ---
    def parse_builds(self, raw_config: Dict[str, Any]) -> List[BuildConfig]: ...

    # --- build ---
    def copy_file(
        self,
        src: Path,
        dest: Path,
        root: Path,
        verbose: bool = True,
    ) -> None: ...
    def copy_directory(
        self,
        src: Path,
        dest: Path,
        exclude_patterns: List[str],
        root: Path,
        verbose: bool = True,
    ) -> None: ...
    def copy_item(
        self,
        src: Path,
        dest: Path,
        exclude_patterns: List[str],
        root: Path,
        verbose: bool = True,
    ) -> None: ...
    def run_build(
        self,
        build_cfg: BuildConfig,  # ✅ use the proper TypedDict
        config_dir: Path,
        out_override: Optional[str],
        verbose: bool = True,
    ) -> None: ...

    # --- CLI ---
    def main(self, argv: Optional[List[str]] = None) -> int: ...


def pytest_ignore_collect(collection_path: Path, config):  # type: ignore[override]
    """
    Hook called by pytest for each discovered path.
    Returning True tells pytest to skip collecting tests from it.
    """
    for bad in BAD_DIRS:
        if bad in str(collection_path):
            return True
    return False


# ------------------------------------------------------------
# ⚙️ Auto-build helper for bundled script
# ------------------------------------------------------------
def ensure_bundled_script_up_to_date(root: Path) -> Path:
    """Rebuild `bin/pocket-build.py` if missing or older than source files."""
    bin_path = root / "bin" / "pocket-build.py"
    src_dir = root / "src" / "pocket_build"
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
        env = dict(os.environ)
        for key in ("CI", "GIT_TAG", "GITHUB_REF"):
            env.pop(key, None)

        subprocess.run([sys.executable, str(builder)], check=True, env=env)
        # force mtime update in case contents identical
        bin_path.touch()
        assert bin_path.exists(), "❌ Failed to generate bundled script."

    return bin_path


# ------------------------------------------------------------
# 🔁 Fixture: load either the package or the bundled script
# ------------------------------------------------------------
@pytest.fixture(scope="session", params=["module", "singlefile"])
def pocket_build_env(
    request: pytest.FixtureRequest,
) -> Generator[PocketBuildLike, None, None]:
    """Yield a loaded pocket_build environment (module or bundled single-file)."""
    root = Path(__file__).resolve().parent.parent

    if request.param == "module":
        import pocket_build as mod

        yield mod  # type: ignore[return-value]

    else:
        bin_path = ensure_bundled_script_up_to_date(root)

        spec = importlib.util.spec_from_file_location("pocket_build_single", bin_path)
        assert spec and spec.loader, f"Failed to load spec from {bin_path}"
        mod = importlib.util.module_from_spec(spec)
        sys.modules["pocket_build_single"] = mod
        spec.loader.exec_module(mod)
        yield mod  # type: ignore[return-value]
