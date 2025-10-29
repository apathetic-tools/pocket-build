# tests/test_make_script_integration.py
"""
Integration tests for `dev/make_script.py`.

These verify that the  standalone script (`bin/script.py`)
embeds the correct commit information depending on environment variables.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

# --- only for singlefile runs ---
__runtime_mode__ = "singlefile"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJ_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "env_vars, expected_pattern",
    [
        ({}, r"\(unknown \(local build\)\)"),  # local dev
        ({"CI": "true"}, r"\([0-9a-f]{4,}\)"),  # simulated CI
    ],
)
def test_make_script_respects_ci_env(
    tmp_path: Path,
    env_vars: dict[str, str],
    expected_pattern: str,
):
    """
    Should embed either '(unknown (local build))' or a real hash depending on env.
    """

    # --- setup ---
    builder = PROJ_ROOT / "dev" / "make_script.py"
    tmp_script = tmp_path / "script-test.py"

    # Ensure a clean rebuild every time -
    if tmp_script.exists():
        tmp_script.unlink()

    # Reset any pre-existing CI vars
    env = dict(os.environ)
    for key in ("CI", "GIT_TAG", "GITHUB_REF"):
        env.pop(key, None)

    # Apply simulated environment
    env.update(env_vars)

    # --- execute and verify ---

    # 1) generate the bundle
    proc = subprocess.run(
        [sys.executable, str(builder), "--out", str(tmp_script)],
        capture_output=True,
        text=True,
        check=True,
        env=env,
        cwd=PROJ_ROOT,
    )
    assert not proc.stderr.strip(), f"Bundler stderr not empty: {proc.stderr}"

    # Confirm the bundle was created
    assert tmp_script.exists(), "Expected temporary script to be generated"

    # 2) Execute the generated script
    result = subprocess.run(
        [sys.executable, str(tmp_script), "--version"],
        capture_output=True,
        text=True,
        check=True,
        cwd=PROJ_ROOT,
    )

    out = result.stdout.strip()
    assert out.startswith("Pocket Build"), f"Unexpected version output: {out}"
    assert re.search(r"\d+\.\d+\.\d+", out), f"No semantic version found: {out}"
    assert re.search(expected_pattern, out), f"Unexpected commit pattern: {out}"
