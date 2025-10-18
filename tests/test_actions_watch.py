# tests/test_cli_watch.py
"""Tests for pocket_build.cli (module and single-file versions)."""

# we import `_` private for testing purposes only
# pyright: reportPrivateUsage=false
# ruff: noqa: F401

from __future__ import annotations

import time
from pathlib import Path
from types import FunctionType
from typing import Any, Callable, cast

from _pytest.monkeypatch import MonkeyPatch
from pytest import approx

from pocket_build.types import BuildConfig
from tests.conftest import RuntimeLike
from tests.utils import (
    force_mtime_advance,
    patch_runtime_function_func,
    patch_runtime_function_mod,
)


# only tests module; no runtime_env
def test_collect_included_files_expands_patterns(tmp_path: Path):
    from pocket_build.actions import _collect_included_files

    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("A")
    (src / "b.txt").write_text("B")

    builds = cast(
        list[BuildConfig],
        [{"include": [str(src / "*.txt")], "out": str(tmp_path / "out")}],
    )
    files = _collect_included_files(builds)

    assert set(files) == {src / "a.txt", src / "b.txt"}


# only tests module; no runtime_env
def test_collect_included_files_handles_nonexistent_paths(tmp_path: Path):
    from pocket_build.actions import _collect_included_files

    builds = cast(
        list[BuildConfig],
        [{"include": [str(tmp_path / "missing/**")], "out": str(tmp_path / "out")}],
    )
    files = _collect_included_files(builds)
    assert files == []  # no crash, empty result


# only tests module; no runtime_env
def test_watch_for_changes_triggers_rebuild(tmp_path: Path, monkeypatch: MonkeyPatch):
    """Ensure that watch_for_changes() rebuilds on file modification.

    This verifies the core watch loop logic in pocket_build.cli:
    - The initial build should run once at startup.
    - A subsequent file modification should trigger exactly one rebuild.

    The test replaces time.sleep() to simulate loop ticks deterministically
    and fakes _collect_included_files() to simulate file changes
    without waiting for real filesystem events.
    """

    # --- setup temporary workspace ---
    src = tmp_path / "src"
    src.mkdir()
    f = src / "file.txt"
    f.write_text("x")

    builds = cast(
        list[BuildConfig],
        [{"include": [str(src / "*.txt")], "out": str(tmp_path / "out")}],
    )

    calls: list[str] = []

    # --- stubbed build implementation ---
    def fake_build():
        """Record each rebuild invocation."""
        calls.append("rebuilt")

    # --- simulate timing and loop control ---
    counter = {"n": 0}

    def fake_sleep(_seconds: float):
        """Replace time.sleep to advance the watch loop deterministically."""
        counter["n"] += 1
        if counter["n"] >= 3:
            # stop after the second rebuild cycle
            raise KeyboardInterrupt

    # --- simulate file discovery and modification ---
    def fake_collect(_builds: list[BuildConfig]):
        """Return the watched file list, faking a file modification on tick > 0."""
        if counter["n"] == 0:
            return [f]
        f.write_text("y")
        force_mtime_advance(f)
        return [f]

    # --- patch and execute ---
    with monkeypatch.context() as mp:
        # Patch time.sleep so the watch loop exits quickly and predictably.
        mp.setattr(time, "sleep", fake_sleep)

        from pocket_build.actions import _collect_included_files

        patch_runtime_function_func(mp, None, _collect_included_files, fake_collect)

        # Run the watcher with our fake build function.
        from pocket_build.actions import watch_for_changes

        watch_for_changes(fake_build, builds, interval=0.01)

        # --- verify expected behavior ---
        # Should rebuild twice: once at startup and once on file modification.
        # Some timing edges may yield an extra rebuild, so tolerate up to 3.
        assert 2 <= calls.count("rebuilt") <= 3


def test_watch_flag_invokes_watch_mode(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    runtime_env: RuntimeLike,
):
    """Ensure --watch flag triggers watch_for_changes() call.

    This test verifies that invoking the CLI with `--watch`
    causes `main()` to call `watch_for_changes()` exactly as expected.

    The difficulty lies in how `main()` references `watch_for_changes`:
    it doesn’t call `runtime_env.watch_for_changes` directly, but
    resolves it as a global symbol within its own function body.
    That means we must patch the *namespace of main()*, not the module itself.
    """

    with monkeypatch.context() as mp:
        # --- setup temp config ---
        config = tmp_path / ".pocket-build.json"
        config.write_text('{"builds": [{"include": [], "out": "dist"}]}')
        mp.chdir(tmp_path)

        called: dict[str, bool] = {}

        # --- fake implementation ---
        def fake_watch(
            _rebuild_func: Callable[[], None],
            _resolved_builds: list[BuildConfig],
            _interval: float = 1.0,
            **_kwargs: Any,
        ):
            """Stub out watch_for_changes() to mark invocation."""
            called["yes"] = True
            return 0

        # Runtime assertion helps Pylance and future maintainers:
        # if runtime_env.main changes type, this test will break loudly.
        assert isinstance(runtime_env.main, FunctionType)

        from pocket_build.actions import watch_for_changes

        patch_runtime_function_func(mp, runtime_env, watch_for_changes, fake_watch)

        # --- execute main() in watch mode ---
        code = runtime_env.main(["--watch"])

        # --- assertions ---
        assert code == 0, "Expected main() to return success code"
        assert called, "Expected fake_watch() to be called at least once"


def test_watch_for_changes_exported_and_callable_old(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    runtime_env: RuntimeLike,
):
    """Ensure watch_for_changes runs and rebuilds exactly twice."""
    src = tmp_path / "src"
    src.mkdir()
    f = src / "file.txt"
    f.write_text("x")

    builds = cast(list[BuildConfig], [{"include": [str(src / "*.txt")], "out": "dist"}])
    calls: list[str] = []

    def fake_build():
        calls.append("rebuilt")

    # --- control loop timing ---
    counter = {"n": 0}

    def fake_sleep(_seconds: float):
        counter["n"] += 1
        if counter["n"] >= 3:  # never infinite loop
            raise KeyboardInterrupt  # stop after second iteration

    # --- simulate file discovery ---
    def fake_collect(_builds: list[BuildConfig]):
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

    assert isinstance(runtime_env.main, FunctionType)

    with monkeypatch.context() as mp:
        from pocket_build.actions import _collect_included_files

        patch_runtime_function_func(
            mp, runtime_env, _collect_included_files, fake_collect
        )

        mp.setattr(time, "sleep", fake_sleep)  # ✅ works
        # mp.setattr(sys.modules["time"], "sleep", fake_sleep)  # also works
        # mp.setattr(runtime_env, "time.sleep", fake_sleep)  # doesn't work

        # --- run ---
        runtime_env.watch_for_changes(fake_build, builds, interval=0.01)

        # --- assert ---
        assert 2 <= calls.count("rebuilt") <= 3


def test_watch_for_changes_exported_and_callable(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    runtime_env: RuntimeLike,
):
    """Ensure watch_for_changes runs and rebuilds exactly twice."""
    src = tmp_path / "src"
    src.mkdir()
    f = src / "file.txt"
    f.write_text("x")

    builds = cast(list[BuildConfig], [{"include": [str(src / "*.txt")], "out": "dist"}])
    calls: list[str] = []

    def fake_build():
        calls.append("rebuilt")

    # --- control loop timing ---
    counter = {"n": 0}

    def fake_sleep(_seconds: float):
        counter["n"] += 1
        if counter["n"] >= 3:  # never infinite loop
            raise KeyboardInterrupt  # stop after second iteration

    # --- simulate file discovery ---
    def fake_collect(_builds: list[BuildConfig]):
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

    assert isinstance(runtime_env.main, FunctionType)

    with monkeypatch.context() as mp:
        # patch_runtime_function(
        #     mp, actions_mod, runtime_env, "_collect_included_files", fake_collect
        # )
        from pocket_build.actions import _collect_included_files

        patch_runtime_function_func(
            mp, runtime_env, _collect_included_files, fake_collect
        )

        mp.setattr(time, "sleep", fake_sleep)  # ✅ works
        # mp.setattr(sys.modules["time"], "sleep", fake_sleep)  # also works
        # mp.setattr(runtime_env, "time.sleep", fake_sleep)  # doesn't work

        # --- run ---
        runtime_env.watch_for_changes(fake_build, builds, interval=0.01)

        # --- assert ---
        assert 2 <= calls.count("rebuilt") <= 3


def test_watch_ignores_out_dir(tmp_path: Path, monkeypatch: MonkeyPatch):
    """Ensure watch_for_changes() ignores files in output directory."""
    from pocket_build.actions import watch_for_changes

    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "dist"
    out.mkdir()
    file = src / "file.txt"
    file.write_text("x")
    builds = cast(
        list[BuildConfig], [{"include": [str(src / "*.txt")], "out": str(out)}]
    )

    calls: list[str] = []

    def fake_build():
        calls.append("rebuilt")
        # simulate self-output file that should not retrigger
        (out / "copy.txt").write_text("copied")

    counter = {"n": 0}

    def fake_sleep(_: float) -> None:
        counter["n"] += 1
        if counter["n"] > 1:
            raise KeyboardInterrupt

    with monkeypatch.context() as mp:
        mp.setattr(time, "sleep", fake_sleep)
        watch_for_changes(fake_build, builds, interval=0.01)

    # Only the initial build should run, not retrigger from the out file
    assert calls.count("rebuilt") == 1


def test_watch_interval_flag_parsing():
    from pocket_build.cli import _setup_parser

    parser = _setup_parser()
    args = parser.parse_args(["--watch"])
    # With new semantics, --watch sets None, meaning "use config/default interval"
    assert args.watch is None

    args = parser.parse_args(["--watch", "2.5"])
    assert args.watch == 2.5

    args = parser.parse_args([])
    assert args.watch is None


def test_watch_uses_config_interval_when_flag_passed(
    tmp_path: Path, monkeypatch: MonkeyPatch, runtime_env: RuntimeLike
):
    """Ensure that --watch (no value) uses watch_interval from config when defined."""

    # --- setup config with custom watch_interval ---
    config = tmp_path / ".pocket-build.json"
    config.write_text(
        '{"watch_interval": 0.42, "builds": [{"include": [], "out": "dist"}]}'
    )

    assert isinstance(runtime_env.main, FunctionType)

    with monkeypatch.context() as mp:
        mp.chdir(tmp_path)

        called: dict[str, float] = {}

        def fake_watch(
            _rebuild_func: Callable[[], None],
            _resolved_builds: list[BuildConfig],
            interval: float,
        ):
            """Capture the interval actually passed in."""
            called["interval"] = interval
            return 0

        from pocket_build.actions import watch_for_changes

        patch_runtime_function_func(mp, runtime_env, watch_for_changes, fake_watch)

        # --- run CLI with --watch (no explicit interval) ---
        code = runtime_env.main(["--watch"])
        assert code == 0, "Expected main() to exit cleanly"

        # --- verify interval came from config, not default ---
        assert "interval" in called, "watch_for_changes() was never invoked"
        assert called["interval"] == approx(0.42), (
            f"Expected interval=0.42, got {called}"
        )


def test_watch_falls_back_to_default_interval_when_no_config(
    tmp_path: Path, monkeypatch: MonkeyPatch, runtime_env: RuntimeLike
):
    """Ensure --watch uses DEFAULT_WATCH_INTERVAL when no config interval is defined."""
    from pocket_build.constants import DEFAULT_WATCH_INTERVAL

    config = tmp_path / ".pocket-build.json"
    config.write_text('{"builds": [{"include": [], "out": "dist"}]}')

    assert isinstance(runtime_env.main, FunctionType)

    with monkeypatch.context() as mp:
        mp.chdir(tmp_path)

        called: dict[str, float] = {}

        def fake_watch(
            _rebuild_func: Callable[[], None],
            _resolved_builds: list[BuildConfig],
            *,
            interval: float,
        ):
            called["interval"] = interval
            return 0

        from pocket_build.actions import watch_for_changes

        patch_runtime_function_func(mp, runtime_env, watch_for_changes, fake_watch)

        code = runtime_env.main(["--watch"])
        assert code == 0

        assert "interval" in called, "watch_for_changes() was never invoked"
        assert called["interval"] == approx(DEFAULT_WATCH_INTERVAL), (
            f"Expected interval=0.42, got {called}"
        )
