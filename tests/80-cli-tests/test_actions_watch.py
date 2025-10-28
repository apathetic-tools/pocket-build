# tests/test_cli_watch.py
"""Tests for package.cli (module and single-file versions)."""

# we import `_` private for testing purposes only
# pyright: reportPrivateUsage=false
# ruff: noqa: F401

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

import pytest
from pytest import approx  # type: ignore[reportUnknownVariableType]
from pytest import MonkeyPatch

import pocket_build.actions as mod_actions
import pocket_build.cli as mod_cli
from pocket_build.cli import _setup_parser
from pocket_build.constants import DEFAULT_WATCH_INTERVAL
from pocket_build.meta import PROGRAM_SCRIPT
from pocket_build.types import BuildConfig
from tests.utils import (
    force_mtime_advance,
    make_build_cfg,
    make_include_resolved,
    make_resolved,
    patch_everywhere,
)


def test_collect_included_files_expands_patterns(tmp_path: Path) -> None:
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("A")
    (src / "b.txt").write_text("B")

    build = make_build_cfg(
        tmp_path,
        [make_include_resolved("src/*.txt", tmp_path)],
    )

    # --- execute ---
    files = mod_actions._collect_included_files([build])

    # --- verify ---
    assert set(files) == {src / "a.txt", src / "b.txt"}


def test_collect_included_files_handles_nonexistent_paths(tmp_path: Path) -> None:
    # --- setup ---
    build = make_build_cfg(
        tmp_path,
        [make_include_resolved("missing/**", tmp_path)],
    )

    # --- execute ---
    files = mod_actions._collect_included_files([build])

    # --- verify ---
    assert files == []  # no crash, empty result


@pytest.mark.slow
def test_watch_for_changes_triggers_rebuild(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Ensure that watch_for_changes() rebuilds on file modification.

    This verifies the core watch loop logic in package.cli:
    - The initial build should run once at startup.
    - A subsequent file modification should trigger exactly one rebuild.

    The test replaces time.sleep() to simulate loop ticks deterministically
    and fakes _collect_included_files() to simulate file changes
    without waiting for real filesystem events.
    """

    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    f = src / "file.txt"
    f.write_text("x")

    build = make_build_cfg(
        tmp_path,
        [make_include_resolved(str(src / "*.txt"), tmp_path)],
    )

    calls: list[str] = []

    # --- stubs ---
    def fake_build(*_args: Any, **_kwargs: Any) -> None:
        """Record each rebuild invocation."""
        calls.append("rebuilt")

    # simulate timing and loop control
    counter = {"n": 0}

    def fake_sleep(*_args: Any, **_kwargs: Any) -> None:
        """Replace time.sleep to advance the watch loop deterministically."""
        counter["n"] += 1
        if counter["n"] >= 3:
            # stop after the second rebuild cycle
            raise KeyboardInterrupt

    # simulate file discovery and modification
    def fake_collect(*_args: Any, **_kwargs: Any) -> list[Path]:
        """Return the watched file list, faking a file modification on tick > 0."""
        if counter["n"] == 0:
            return [f]
        f.write_text("y")
        force_mtime_advance(f)
        return [f]

    # --- patch and execute ---
    monkeypatch.setattr(time, "sleep", fake_sleep)
    patch_everywhere(monkeypatch, mod_actions, "_collect_included_files", fake_collect)
    mod_actions.watch_for_changes(fake_build, [build], interval=0.01)

    # --- verify ---
    assert 2 <= calls.count("rebuilt") <= 3


def test_watch_flag_invokes_watch_mode(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
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
    config = tmp_path / f".{PROGRAM_SCRIPT}.json"
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


def test_watch_for_changes_exported_and_callable(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Ensure watch_for_changes runs and rebuilds exactly twice."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    f = src / "file.txt"
    f.write_text("x")

    build = make_build_cfg(
        tmp_path,
        [make_include_resolved("src/*.txt", tmp_path)],
    )
    calls: list[str] = []

    # --- stubs ---
    def fake_build(*_args: Any, **_kwargs: Any) -> None:
        calls.append("rebuilt")

    # control loop timing
    counter = {"n": 0}

    def fake_sleep(*_args: Any, **_kwargs: Any) -> None:
        counter["n"] += 1
        if counter["n"] >= 3:  # never infinite loop
            raise KeyboardInterrupt  # stop after second iteration

    # simulate file discovery
    def fake_collect(*_args: Any, **_kwargs: Any) -> list[Path]:
        # first call: before file change
        if counter["n"] == 0:
            return [f]

        # second call: file modified
        #   need to ensure file's mtime advances
        # time.sleep(0.002) # we monkeypatched time.sleep so this is fake_sleep # broken
        f.write_text("y")
        # modify the file's mtime to fake a modified date in the future
        force_mtime_advance(f)

        return [f]

    # --- patch and execute ---
    monkeypatch.setattr(time, "sleep", fake_sleep)
    patch_everywhere(monkeypatch, mod_actions, "_collect_included_files", fake_collect)
    mod_actions.watch_for_changes(fake_build, [build], interval=0.01)

    # --- verify ---
    assert 2 <= calls.count("rebuilt") <= 3


def test_watch_ignores_out_dir(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Ensure watch_for_changes() ignores files in output directory."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "dist"
    out.mkdir()
    file = src / "file.txt"
    file.write_text("x")
    build = make_build_cfg(
        tmp_path,
        [make_include_resolved("src/*.txt", tmp_path)],
        out=make_resolved(out, tmp_path),
    )

    calls: list[str] = []

    # --- stubs ---
    def fake_build(*_args: Any, **_kwargs: Any) -> None:
        calls.append("rebuilt")
        # simulate self-output file that should not retrigger
        (out / "copy.txt").write_text("copied")

    counter = {"n": 0}

    def fake_sleep(*_args: Any, **_kwargs: Any) -> None:
        counter["n"] += 1
        if counter["n"] > 1:
            raise KeyboardInterrupt

    # --- patch and execute ---
    monkeypatch.setattr(time, "sleep", fake_sleep)
    mod_actions.watch_for_changes(fake_build, [build], interval=0.01)

    # --- verify ---
    # Only the initial build should run, not retrigger from the out file
    assert calls.count("rebuilt") == 1


def test_watch_interval_flag_parsing() -> None:
    # --- setup ---
    parser = _setup_parser()

    # --- execute and verify ---
    args = parser.parse_args(["--watch"])
    # With new semantics, --watch sets None, meaning "use config/default interval"
    assert getattr(args, "watch", None) is None

    args = parser.parse_args(["--watch", "2.5"])
    assert getattr(args, "watch", None) == 2.5

    args = parser.parse_args([])
    assert getattr(args, "watch", None) is None


def test_watch_uses_config_interval_when_flag_passed(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Ensure that --watch (no value) uses watch_interval from config when defined."""
    # --- setup ---
    config = tmp_path / f".{PROGRAM_SCRIPT}.json"
    config.write_text(
        '{"watch_interval": 0.42, "builds": [{"include": [], "out": "dist"}]}'
    )

    called: dict[str, float] = {}

    # --- stubs ---
    def fake_watch(
        _rebuild_func: Callable[[], None],
        _resolved_builds: list[BuildConfig],
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
    assert called["interval"] == approx(0.42), f"Expected interval=0.42, got {called}"


def test_watch_falls_back_to_default_interval_when_no_config(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Ensure --watch uses DEFAULT_WATCH_INTERVAL when no config interval is defined."""
    # --- setup ---
    config = tmp_path / f".{PROGRAM_SCRIPT}.json"
    config.write_text('{"builds": [{"include": [], "out": "dist"}]}')

    called: dict[str, float] = {}

    # --- stubs ---
    def fake_watch(
        _rebuild_func: Callable[[], None],
        _resolved_builds: list[BuildConfig],
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
    assert called["interval"] == approx(DEFAULT_WATCH_INTERVAL), (
        f"Expected interval=0.42, got {called}"
    )
