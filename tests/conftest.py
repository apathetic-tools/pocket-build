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
from _pytest.python import Metafunc

from tests.fixtures.runtime_protocol import RuntimeLike

GEN_PROTOCOL_CMD = ["poetry", "run", "poe", "gen:test:protocol"]


def ensure_protocol_up_to_date(root: Path) -> Path:
    """Regenerate tests/fixtures/runtime_protocol.py if outdated."""
    proto_path = root / "tests" / "fixtures" / "runtime_protocol.py"
    src_dir = root / "src" / "pocket_build"

    # If missing or older than any source file → rebuild.
    needs_rebuild = not proto_path.exists()
    if not needs_rebuild:
        proto_mtime = proto_path.stat().st_mtime_ns
        for src_file in src_dir.rglob("*.py"):
            if src_file.stat().st_mtime_ns > proto_mtime:
                needs_rebuild = True
                break

    if needs_rebuild:
        print("🧩 Regenerating runtime_protocol.py (gen:test:protocol)...")
        subprocess.run(GEN_PROTOCOL_CMD, cwd=root, check=True)
        proto_path.touch()
        assert proto_path.exists(), "❌ Failed to generate runtime protocol."

    return proto_path


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
@pytest.fixture(scope="session")
def runtime_env(
    request: pytest.FixtureRequest,
) -> Generator[RuntimeLike, None, None]:
    """Yield a loaded pocket_build environment (module or bundled single-file)."""
    root = Path(__file__).resolve().parent.parent

    # --- Ensure supporting artifacts are current ---
    ensure_protocol_up_to_date(root)

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


def pytest_generate_tests(metafunc: Metafunc) -> None:
    """Attach dependency markers automatically for the two runtimes."""
    if "runtime_env" in metafunc.fixturenames:
        metafunc.parametrize(
            "runtime_env",
            [
                pytest.param(
                    "module",
                    id="module",
                    marks=pytest.mark.dependency(
                        name=f"{metafunc.function.__name__}[module]"
                    ),
                ),
                pytest.param(
                    "singlefile",
                    id="singlefile",
                    marks=pytest.mark.dependency(
                        depends=[f"{metafunc.function.__name__}[module]"]
                    ),
                ),
            ],
            indirect=True,
        )
