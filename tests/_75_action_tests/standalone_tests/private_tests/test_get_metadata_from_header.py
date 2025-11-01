# tests/test_standalone_metadata.py
"""Verify that the standalone standalone version (`bin/script.py`)
was generated correctly — includes metadata, license header,
and matches the declared version from pyproject.toml.
"""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

from pathlib import Path

import pocket_build.actions as mod_actions


# --- only for singlefile runs ---
__runtime_mode__ = "singlefile"


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
