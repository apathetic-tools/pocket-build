# tests/test_bundled_metadata.py
"""
Verify that the bundled single-file version (`bin/pocket-build.py`)
was generated correctly — includes metadata, license header,
and matches the declared version from pyproject.toml.
"""

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


def test_bundled_script_metadata_and_execution() -> None:
    """Ensure the generated pocket-build.py script is complete and functional."""
    root = Path(__file__).resolve().parent.parent
    script = root / "bin" / "pocket-build.py"
    pyproject = root / "pyproject.toml"

    # --- Basic existence checks ---
    assert script.exists(), (
        "Bundled script not found — run `poetry run poe build.single` first."
    )
    assert pyproject.exists(), "pyproject.toml missing — project layout inconsistent."

    # --- Load declared version from pyproject.toml ---
    with pyproject.open("rb") as f:
        pyproject_data = cast(dict[str, Any], tomllib.load(f))  # type: ignore[attr-defined]

    project_section = cast(dict[str, Any], pyproject_data.get("project", {}))
    declared_version = cast(str, project_section.get("version"))
    assert declared_version, "Version not found in pyproject.toml"

    # --- Read bundled script text ---
    text = script.read_text(encoding="utf-8")

    # --- Metadata presence checks ---
    assert "# Pocket Build" in text
    assert "License: MIT-NOAI" in text
    assert "Version:" in text
    assert "Repo:" in text
    assert "auto-generated" in text

    # --- Version and commit format checks ---
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

    # --- Execution check (isolated temp dir) ---
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        dummy = tmp / "dummy.txt"
        dummy.write_text("hi", encoding="utf-8")

        config = tmp / ".pocket-build.json"
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
