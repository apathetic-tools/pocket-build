# tests/5_core/test_priv__get_metadata_from_header.py
"""Verify _get_metadata_from_header() works correctly."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

from pathlib import Path

import pocket_build.actions as mod_actions


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


def test__get_metadata_from_header_fallback_to_comments(tmp_path: Path) -> None:
    """Should fallback to comment headers if constants missing."""
    # --- setup ---
    text = """# Version: 2.3.4
# Commit: def5678
some code here
"""
    script = tmp_path / "script.py"
    script.write_text(text)

    # --- execute ---
    version, commit = mod_actions._get_metadata_from_header(script)

    # --- verify ---
    assert version == "2.3.4"
    assert commit == "def5678"


def test__get_metadata_from_header_missing_all(tmp_path: Path) -> None:
    # --- setup ---
    p = tmp_path / "script.py"
    p.write_text("# no metadata")

    # --- execute ---
    version, commit = mod_actions._get_metadata_from_header(p)

    # --- verify ---
    assert version == "unknown"
    assert commit == "unknown"


def test__get_metadata_from_header_handles_missing_file() -> None:
    """Should return 'unknown' when file doesn't exist."""
    # --- execute ---
    version, commit = mod_actions._get_metadata_from_header(
        Path("/nonexistent/path/file.py")
    )

    # --- verify ---
    assert version == "unknown"
    assert commit == "unknown"


def test__get_metadata_from_header_mixed_sources(tmp_path: Path) -> None:
    """Should prefer constants but fallback to comments for missing values."""
    # --- setup ---
    text = """
__version__ = "3.0.0"
# Commit: abc9999
"""
    script = tmp_path / "script.py"
    script.write_text(text)

    # --- execute ---
    version, commit = mod_actions._get_metadata_from_header(script)

    # --- verify ---
    assert version == "3.0.0"
    assert commit == "abc9999"
