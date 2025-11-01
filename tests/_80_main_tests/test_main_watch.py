# tests/test_cli_watch.py
"""Tests for package.cli (package and standalone versions)."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import pocket_build.actions as mod_actions
import pocket_build.cli as mod_cli
import pocket_build.constants as mod_constants
import pocket_build.meta as mod_meta
import pocket_build.types as mod_types
from tests.utils import (
    patch_everywhere,
)


def test_watch_flag_invokes_watch_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure --watch flag triggers watch_for_changes() call.

    This test verifies that invoking the CLI with `--watch`
    causes `main()` to call `watch_for_changes()` exactly as expected.

    The difficulty lies in how `main()` references `watch_for_changes`:
    it doesn’t call `runtime_env.watch_for_changes` directly, but
    resolves it as a global symbol within its own function body.
    That means we must patch the *namespace of main()*, not the module itself.
    """
    # --- setup ---
    config = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    config.write_text('{"builds": [{"include": [], "out": "dist"}]}')

    called: dict[str, bool] = {}

    # --- stubs ---
    def fake_watch(*_args: Any, **_kwargs: Any) -> None:
        """Stub out watch_for_changes() to mark invocation."""
        called["yes"] = True

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    patch_everywhere(monkeypatch, mod_actions, "watch_for_changes", fake_watch)
    code = mod_cli.main(["--watch"])

    # --- verify ---
    assert code == 0, "Expected main() to return success code"
    assert called, "Expected fake_watch() to be called at least once"


def test_watch_uses_config_interval_when_flag_passed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure that --watch (no value) uses watch_interval from config when defined."""
    # --- setup ---
    config = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    config.write_text(
        '{"watch_interval": 0.42, "builds": [{"include": [], "out": "dist"}]}',
    )

    called: dict[str, float] = {}

    # --- stubs ---
    def fake_watch(
        _rebuild_func: Callable[[], None],
        _resolved_builds: list[mod_types.BuildConfigResolved],
        interval: float,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        """Capture the interval actually passed in."""
        called["interval"] = interval

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    patch_everywhere(monkeypatch, mod_actions, "watch_for_changes", fake_watch)
    # run CLI with --watch (no explicit interval)
    code = mod_cli.main(["--watch"])

    # --- verify ---
    assert code == 0, "Expected main() to exit cleanly"
    assert "interval" in called, "watch_for_changes() was never invoked"
    assert called["interval"] == pytest.approx(0.42), (  # pyright: ignore[reportUnknownMemberType]
        f"Expected interval=0.42, got {called}"
    )


def test_watch_falls_back_to_default_interval_when_no_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure --watch uses DEFAULT_WATCH_INTERVAL when no config interval is defined."""
    # --- setup ---
    config = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    config.write_text('{"builds": [{"include": [], "out": "dist"}]}')

    called: dict[str, float] = {}

    # --- stubs ---
    def fake_watch(
        _rebuild_func: Callable[[], None],
        _resolved_builds: list[mod_types.BuildConfigResolved],
        interval: float,
        *_args: Any,
        **_kwargs: Any,
    ) -> None:
        called["interval"] = interval

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    patch_everywhere(monkeypatch, mod_actions, "watch_for_changes", fake_watch)
    code = mod_cli.main(["--watch"])

    # --- verify ---
    assert code == 0
    assert "interval" in called, "watch_for_changes() was never invoked"
    assert called["interval"] == pytest.approx(mod_constants.DEFAULT_WATCH_INTERVAL), (  # pyright: ignore[reportUnknownMemberType]
        f"Expected interval=0.42, got {called}"
    )
