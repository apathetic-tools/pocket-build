# tests/test_cli.py
"""Tests for package.cli (package and standalone versions)."""

import os
import re

import pytest

import pocket_build.cli as mod_cli
import pocket_build.meta as mod_meta


def test_version_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should print version and commit info cleanly."""
    # --- execute ---
    code = mod_cli.main(["--version"])
    out = capsys.readouterr().out

    # --- verify ---
    assert code == 0
    assert mod_meta.PROGRAM_DISPLAY in out
    assert re.search(r"\d+\.\d+\.\d+", out)

    if os.getenv("RUNTIME_MODE") in {"singlefile"}:
        # Standalone version — commit may be known or local
        if os.getenv("CI") or os.getenv("GIT_TAG") or os.getenv("GITHUB_REF"):
            assert re.search(r"\([0-9a-f]{4,}\)", out)
        else:
            assert "(unknown (local build))" in out
    else:
        # installed (source) version — should always have a live git commit hash
        assert re.search(r"\([0-9a-f]{4,}\)", out)
