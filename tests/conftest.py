# tests/conftest.py
"""
Shared test fixture for pocket-build.

This lets all tests transparently run against both:
1. The modular package (`src/pocket_build`)
2. The bundled single-file script (`bin/pocket-build.py`)

Each test receives a `runtime_env` fixture that behaves like the module.

If the bundled script is missing or older than the source files,
it is automatically rebuilt using `dev/make_script.py`.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Generator

import pytest

from tests.fixtures.runtime_protocol import RuntimeLike


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
        subprocess.run([sys.executable, str(builder)], check=True)
        # force mtime update in case contents identical
        bin_path.touch()
        assert bin_path.exists(), "❌ Failed to generate bundled script."

    return bin_path


# ------------------------------------------------------------
# 🔁 Fixture: load either the package or the bundled script
# ------------------------------------------------------------
@pytest.fixture(scope="session", params=["module", "singlefile"])
def runtime_env(
    request: pytest.FixtureRequest,
) -> Generator[RuntimeLike, None, None]:
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
