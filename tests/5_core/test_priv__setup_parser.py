# tests/test_cli_watch.py
"""Tests for package.cli (package and standalone versions)."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

import pocket_build.cli as mod_cli


def test_watch_interval_flag_parsing() -> None:
    # --- setup ---
    parser = mod_cli._setup_parser()

    # --- execute and verify ---
    args = parser.parse_args(["--watch"])
    # With new semantics, --watch sets None, meaning "use config/default interval"
    assert getattr(args, "watch", None) is None

    interval = 2.5
    args = parser.parse_args(["--watch", str(interval)])
    assert getattr(args, "watch", None) == interval

    args = parser.parse_args([])
    assert getattr(args, "watch", None) is None
