# tests/test_config_resolve.py

"""Tests for pocket_build.config_resolve."""

import argparse
from pathlib import Path

import pytest

import pocket_build.config_resolve as mod_resolve
import pocket_build.constants as mod_constants
import pocket_build.constants as mod_mutate_const  # for monkeypatch
import pocket_build.runtime as mod_runtime
import pocket_build.types as mod_types
from tests.utils import make_build_input


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _args(**kwargs: object) -> argparse.Namespace:
    """Build a fake argparse.Namespace with common CLI defaults."""
    arg_namespace = argparse.Namespace()
    # default fields expected by resolver
    arg_namespace.include = None
    arg_namespace.exclude = None
    arg_namespace.add_include = None
    arg_namespace.add_exclude = None
    arg_namespace.out = None
    arg_namespace.watch = None
    arg_namespace.log_level = None
    arg_namespace.respect_gitignore = None
    arg_namespace.use_color = None
    arg_namespace.config = None
    arg_namespace.dry_run = False
    for k, v in kwargs.items():
        setattr(arg_namespace, k, v)
    return arg_namespace


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_resolve_config_aggregates_builds_and_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure resolve_config merges builds and assigns default values."""
    # --- setup ---
    root: mod_types.RootConfig = {
        "builds": [
            make_build_input(include=["src/**"], out="dist"),
            make_build_input(include=["lib/**"], out="libout"),
        ],
        "log_level": "warning",
    }
    args = _args()

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    resolved = mod_resolve.resolve_config(root, args, tmp_path, tmp_path)

    # --- validate ---
    builds = resolved["builds"]
    assert len(builds) == len(root["builds"])
    assert all("include" in b for b in builds)
    assert resolved["log_level"] in ("warning", "info")  # env/cli may override
    assert isinstance(resolved["watch_interval"], float)
    assert resolved["strict_config"] is False


def test_resolve_config_env_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Environment variables for watch interval and log level should override."""
    # --- setup ---
    root: mod_types.RootConfig = {"builds": [{"include": ["src/**"], "out": "dist"}]}
    args = _args()
    interval = 9.9

    # --- patch and execute ---
    monkeypatch.setenv(mod_mutate_const.DEFAULT_ENV_WATCH_INTERVAL, str(interval))
    monkeypatch.setenv(mod_mutate_const.DEFAULT_ENV_LOG_LEVEL, "debug")
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    resolved = mod_resolve.resolve_config(root, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["watch_interval"] == pytest.approx(interval)  # pyright: ignore[reportUnknownMemberType]
    assert resolved["log_level"] == "debug"


def test_resolve_config_invalid_env_watch_falls_back(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Invalid watch interval env var should log warning and use default."""
    # --- setup ---
    root: mod_types.RootConfig = {"builds": [{"include": ["src/**"], "out": "dist"}]}
    args = _args()

    # --- patch and execute ---
    monkeypatch.setenv(mod_mutate_const.DEFAULT_ENV_WATCH_INTERVAL, "badvalue")
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    resolved = mod_resolve.resolve_config(root, args, tmp_path, tmp_path)

    # --- validate ---
    assert isinstance(resolved["watch_interval"], float)
    assert resolved["watch_interval"] == mod_constants.DEFAULT_WATCH_INTERVAL


def test_resolve_config_propagates_cli_log_level(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI --log-level should propagate into resolved root and runtime."""
    # --- setup ---
    args = _args(log_level="trace")
    root: mod_types.RootConfig = {"builds": [{"include": ["src/**"], "out": "dist"}]}

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    resolved = mod_resolve.resolve_config(root, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["log_level"] == "trace"
    assert mod_runtime.current_runtime["log_level"] == "trace"
