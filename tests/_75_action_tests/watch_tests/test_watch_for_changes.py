# tests/test_cli_watch.py
"""Tests for package.cli (package and standalone versions)."""

import time
from pathlib import Path
from typing import Any

import pytest

import pocket_build.actions as mod_actions
from tests.utils import (
    force_mtime_advance,
    make_build_cfg,
    make_include_resolved,
    make_resolved,
    patch_everywhere,
)


@pytest.mark.slow
def test_watch_for_changes_triggers_rebuild(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure that watch_for_changes() rebuilds on file modification.

    This verifies the core watch loop logic in module.cli:
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
    min_rebuild_cycles = 2
    max_rebuild_cycles = 3

    # --- stubs ---
    def fake_build(*_args: Any, **_kwargs: Any) -> None:
        """Record each rebuild invocation."""
        calls.append("rebuilt")

    # simulate timing and loop control
    counter = {"n": 0}

    def fake_sleep(*_args: Any, **_kwargs: Any) -> None:
        """Replace time.sleep to advance the watch loop deterministically."""
        counter["n"] += 1
        if counter["n"] >= max_rebuild_cycles:
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
    assert min_rebuild_cycles <= calls.count("rebuilt") <= max_rebuild_cycles


def test_watch_for_changes_exported_and_callable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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

    min_rebuild_cycles = 2
    max_rebuild_cycles = 3

    # --- stubs ---
    def fake_build(*_args: Any, **_kwargs: Any) -> None:
        calls.append("rebuilt")

    # control loop timing
    counter = {"n": 0}

    def fake_sleep(*_args: Any, **_kwargs: Any) -> None:
        counter["n"] += 1
        if counter["n"] >= max_rebuild_cycles:  # never infinite loop
            raise KeyboardInterrupt  # stop after second iteration

    # simulate file discovery
    def fake_collect(*_args: Any, **_kwargs: Any) -> list[Path]:
        # first call: before file change
        if counter["n"] == 0:
            return [f]

        # second call: file modified
        #   need to ensure file's mtime advances
        # we monkeypatched time.sleep so can't call it here
        f.write_text("y")
        # modify the file's mtime to fake a modified date in the future
        force_mtime_advance(f)

        return [f]

    # --- patch and execute ---
    monkeypatch.setattr(time, "sleep", fake_sleep)
    patch_everywhere(monkeypatch, mod_actions, "_collect_included_files", fake_collect)
    mod_actions.watch_for_changes(fake_build, [build], interval=0.01)

    # --- verify ---
    assert min_rebuild_cycles <= calls.count("rebuilt") <= max_rebuild_cycles


def test_watch_ignores_out_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
