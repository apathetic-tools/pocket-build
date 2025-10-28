# tests/test_bundled_metadata.py
"""
Verify that the bundled single-file version (`bin/script.py`)
was generated correctly — includes metadata, license header,
and matches the declared version from pyproject.toml.
"""

# we import `_` private for testing purposes only
# pyright: reportPrivateUsage=false
# ruff: noqa: F401

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

import pocket_build.actions as mod_actions
from pocket_build.meta import PROGRAM_SCRIPT

# --- only for singlefile runs ---
__runtime_mode__ = "singlefile"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJ_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_bundled_script_metadata_and_execution() -> None:
    """Ensure the generated script.py script is complete and functional."""
    # --- setup ---
    script = PROJ_ROOT / "bin" / f"{PROGRAM_SCRIPT}.py"
    pyproject = PROJ_ROOT / "pyproject.toml"

    # --- execute and verify ---

    # - Basic existence checks -
    assert script.exists(), (
        "Bundled script not found — run `poetry run poe build:single` first."
    )
    assert pyproject.exists(), "pyproject.toml missing — project layout inconsistent."

    # - Load declared version from pyproject.toml -
    with pyproject.open("rb") as f:
        pyproject_data = cast(dict[str, Any], tomllib.load(f))  # type: ignore[attr-defined]

    project_section = cast(dict[str, Any], pyproject_data.get("project", {}))
    declared_version = cast(str, project_section.get("version"))
    assert declared_version, "Version not found in pyproject.toml"

    # - Read bundled script text -
    text = script.read_text(encoding="utf-8")

    # - Metadata presence checks -
    assert "# Pocket Build" in text
    assert "License: MIT-NOAI" in text
    assert "Version:" in text
    assert "Repo:" in text
    assert "auto-generated" in text

    # - Version and commit format checks -
    version_match = re.search(r"^# Version:\s*([\w.\-]+)", text, re.MULTILINE)

    if os.getenv("CI") or os.getenv("GIT_TAG") or os.getenv("GITHUB_REF"):
        commit_match = re.search(r"^# Commit:\s*([0-9a-f]{4,})", text, re.MULTILINE)
    else:
        commit_match = re.search(
            r"^# Commit:\s*unknown \(local build\)", text, re.MULTILINE
        )

    assert version_match, "Missing version stamp"
    assert commit_match, "Missing commit stamp"

    bundled_version = version_match.group(1)
    assert bundled_version == declared_version, (
        f"Bundled version '{bundled_version}' != pyproject version '{declared_version}'"
    )

    # - Execution check (isolated temp dir) -
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        dummy = tmp / "dummy.txt"
        dummy.write_text("hi", encoding="utf-8")

        config = tmp / f".{PROGRAM_SCRIPT}.json"
        config.write_text(
            '{"builds":[{"include":["dummy.txt"],"out":"dist"}]}',
            encoding="utf-8",
        )

        result = subprocess.run(
            ["python3", str(script), "--out", "tmp-dist"],
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


def test_bundled_script_has_python_constants_and_parses_them() -> None:
    """Ensure __version__ and __commit__ constants exist and match header."""
    # --- setup ---
    script = PROJ_ROOT / "bin" / f"{PROGRAM_SCRIPT}.py"

    # --- execute ---
    text = script.read_text(encoding="utf-8")

    # --- verify ---
    # Check constants exist
    version_const = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text)
    commit_const = re.search(r"__commit__\s*=\s*['\"]([^'\"]+)['\"]", text)
    assert version_const, "Missing __version__ constant"
    assert commit_const, "Missing __commit__ constant"

    # Check they match header comments
    header_version = re.search(r"^# Version:\s*([\w.\-]+)", text, re.MULTILINE)
    header_commit = re.search(r"^# Commit:\s*(.+)$", text, re.MULTILINE)
    assert header_version, "Missing # Version header"
    assert header_commit, "Missing # Commit header"

    assert version_const.group(1) == header_version.group(1)
    assert commit_const.group(1) == header_commit.group(1)


def test__get_metadata_from_header_prefers_constants(tmp_path: Path) -> None:
    """Should return values from __version__ and __commit__ if header lines missing."""
    # --- setup ---
    text = """
__version__ = "1.2.3"
__commit__ = "abc1234"
"""
    script = tmp_path / "fake_script.py"
    script.write_text(text)

    # --- execute ---
    version, commit = mod_actions._get_metadata_from_header(script)

    # --- verify ---
    assert version == "1.2.3"
    assert commit == "abc1234"


def test__get_metadata_from_header_missing_all(tmp_path: Path) -> None:
    # --- setup ---
    p = tmp_path / "script.py"
    p.write_text("# no metadata")

    # --- execute ---
    version, commit = mod_actions._get_metadata_from_header(p)

    # --- verify ---
    assert version == "unknown"
    assert commit == "unknown"
