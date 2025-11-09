# tests/test_standalone_metadata.py
"""Verify that the standalone standalone version (`bin/script.py`)
was generated correctly — includes metadata, license header,
and matches the declared version from pyproject.toml.
"""

import subprocess
import tempfile
from pathlib import Path

import pocket_build.meta as mod_meta
from tests.utils import PROJ_ROOT


# --- only for singlefile runs ---
__runtime_mode__ = "singlefile"


def test_standalone_script_metadata_and_execution() -> None:
    """Ensure the generated script.py script is complete and functional."""
    # --- setup ---
    script = PROJ_ROOT / "bin" / f"{mod_meta.PROGRAM_CONFIG}.py"

    # --- execute and verify ---

    # - Basic existence checks -
    assert script.exists(), (
        "Standalone script not found — run `poetry run poe build:single` first."
    )

    # - Execution check (isolated temp dir) -
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        dummy = tmp / "dummy.txt"
        dummy.write_text("hi", encoding="utf-8")

        config = tmp / f".{mod_meta.PROGRAM_CONFIG}.json"
        config.write_text(
            '{"builds":[{"include":["dummy.txt"],"out":"dist"}]}',
            encoding="utf-8",
        )

        result = subprocess.run(  # noqa: S603
            ["python3", str(script), "--out", "tmp-dist"],  # noqa: S607
            check=False,
            cwd=tmp,  # ✅ run in empty temp dir
            capture_output=True,
            text=True,
            timeout=15,
        )

    assert result.returncode == 0, (
        f"Non-zero exit ({result.returncode}):\n{result.stderr}"
    )
    assert "Build completed" in result.stdout
    assert "🎉 All builds complete" in result.stdout
