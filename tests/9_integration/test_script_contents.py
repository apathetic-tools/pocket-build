# tests/test_standalone_metadata.py
"""Verify that the standalone standalone version (`bin/script.py`)
was generated correctly — includes metadata, license header,
and matches the declared version from pyproject.toml.
"""

import os
import re
from typing import Any, cast

from tests.utils import PROJ_ROOT


try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

import pocket_build.meta as mod_meta


# --- only for singlefile runs ---
__runtime_mode__ = "singlefile"


def test_standalone_script_metadata_and_execution() -> None:
    """Ensure the generated script.py script is complete and functional."""
    # --- setup ---
    script = PROJ_ROOT / "bin" / f"{mod_meta.PROGRAM_SCRIPT}.py"
    pyproject = PROJ_ROOT / "pyproject.toml"

    # --- execute and verify ---

    # - Basic existence checks -
    assert script.exists(), (
        "Standalone script not found — run `poetry run poe build:single` first."
    )
    assert pyproject.exists(), "pyproject.toml missing — project layout inconsistent."

    # - Load declared version from pyproject.toml -
    with pyproject.open("rb") as f:
        pyproject_data = cast("dict[str, Any]", tomllib.load(f))  # type: ignore[attr-defined]

    project_section = cast("dict[str, Any]", pyproject_data.get("project", {}))
    declared_version = cast("str", project_section.get("version"))
    assert declared_version, "Version not found in pyproject.toml"

    # - Read standalone script text -
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
            r"^# Commit:\s*unknown \(local build\)",
            text,
            re.MULTILINE,
        )

    assert version_match, "Missing version stamp"
    assert commit_match, "Missing commit stamp"

    standalone_version = version_match.group(1)
    assert standalone_version == declared_version, (
        f"Standalone version '{standalone_version}'"
        f" != pyproject version '{declared_version}'"
    )


def test_standalone_script_has_python_constants_and_parses_them() -> None:
    """Ensure __version__ and __commit__ constants exist and match header."""
    # --- setup ---
    script = PROJ_ROOT / "bin" / f"{mod_meta.PROGRAM_SCRIPT}.py"

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
