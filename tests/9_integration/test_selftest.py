# tests/test_cli_selftest.py
"""Tests for --selftest flag in pocket-build CLI."""

import pytest

import pocket_build.cli as mod_cli


def test_selftest_flag_success(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--selftest should run the self-test and exit with code 0 on success."""
    # --- execute ---
    code = mod_cli.main(["--selftest"])

    # --- verify ---
    assert code == 0

    # Check output mentions self-test
    captured = capsys.readouterr()
    out = (captured.out + captured.err).lower()
    assert "self-test" in out or "selftest" in out.replace("-", "")


def test_selftest_ignores_other_flags(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--selftest should run and exit early, ignoring other CLI flags."""
    # --- execute ---
    # --selftest should exit immediately without requiring a config or includes
    code = mod_cli.main(["--selftest", "--verbose", "--dry-run"])

    # --- verify ---
    assert code == 0

    # Output should indicate self-test ran
    captured = capsys.readouterr()
    out = (captured.out + captured.err).lower()
    assert "self-test" in out or "selftest" in out.replace("-", "")
