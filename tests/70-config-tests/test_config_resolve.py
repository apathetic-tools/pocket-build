# tests/test_config_resolve.py

"""Tests for pocket_build.config_resolve."""

import argparse
from argparse import Namespace
from pathlib import Path

from pytest import MonkeyPatch

import pocket_build.config_resolve as mod_resolve
import pocket_build.constants as mod_const  # for changing constants using monkeypatch
import pocket_build.runtime as mod_runtime
from pocket_build.constants import DEFAULT_WATCH_INTERVAL
from pocket_build.types import BuildConfigInput, RootConfigInput
from tests.utils import (
    make_build_input,
)

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

# ---------------------------------------------------------------------------
# resolve_build_config()
# ---------------------------------------------------------------------------


def test_resolve_build_config_from_config_paths(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Ensure config-based include/out/exclude resolve relative to config_dir."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], exclude=["*.tmp"], out="dist")
    args = _args()

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    inc = resolved["include"][0]
    exc = resolved["exclude"][0]
    out = resolved["out"]

    assert inc["base"] == tmp_path
    assert exc["base"] == tmp_path
    assert out["base"] == tmp_path
    assert resolved["log_level"] == "info"
    assert resolved["respect_gitignore"] is True
    assert resolved["__meta__"]["config_base"] == tmp_path
    assert resolved["__meta__"]["cli_base"] == tmp_path


def test_resolve_build_config_cli_overrides_include_and_out(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """CLI --include and --out should override config include/out."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], out="dist")
    args = _args(include=["cli_src/**"], out="cli_dist")

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    inc = resolved["include"][0]
    out = resolved["out"]

    assert inc["path"] == "cli_src/**"
    assert inc["origin"] == "cli"
    assert out["path"] == "cli_dist"
    assert out["origin"] == "cli"


def test_resolve_build_config_add_include_extends(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """--add-include should append to config includes, not override."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    args = _args(add_include=["extra/**"])

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    paths = [i["path"] for i in resolved["include"]]
    assert "src/**" in paths
    assert "extra/**" in paths
    origins = {i["origin"] for i in resolved["include"]}
    assert "config" in origins and "cli" in origins


def test_resolve_build_config_gitignore_patterns_added(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """When .gitignore exists, its patterns should be appended as gitignore excludes."""
    # --- setup ---
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.log\n# comment\ncache/\n")
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "debug")
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    git_excludes = [e for e in resolved["exclude"] if e["origin"] == "gitignore"]
    patterns = [str(e["path"]) for e in git_excludes]
    assert "*.log" in patterns
    assert "cache/" in patterns


def test_resolve_build_config_respects_cli_exclude_override(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """CLI --exclude should override config excludes."""
    # --- setup ---
    raw = make_build_input(exclude=["*.tmp"], include=["src/**"])
    args = _args(exclude=["*.bak"])

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    excl = [str(e["path"]) for e in resolved["exclude"]]
    assert "*.bak" in excl
    assert "*.tmp" not in excl


def test_resolve_build_config_respects_dest_override(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """IncludeResolved with explicit dest should survive resolution unchanged."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], out="dist")
    args = _args()

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    out = resolved["out"]
    assert out["origin"] == "config"
    assert out["base"] == tmp_path
    assert out["path"] == "dist"


def test_resolve_build_config_respect_gitignore_false(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """If --no-gitignore is passed, .gitignore patterns are not loaded."""
    # --- setup ---
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.log\n")
    raw = make_build_input(include=["src/**"], respect_gitignore=False)
    args = _args(respect_gitignore=False)

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert all(e["origin"] != "gitignore" for e in resolved["exclude"])
    assert resolved["respect_gitignore"] is False


# ---------------------------------------------------------------------------
# resolve_config()
# ---------------------------------------------------------------------------


def test_resolve_config_aggregates_builds_and_defaults(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Ensure resolve_config merges builds and assigns default values."""
    # --- setup ---
    root: RootConfigInput = {
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
    assert len(builds) == 2
    assert all("include" in b for b in builds)
    assert resolved["log_level"] in ("warning", "info")  # env/cli may override
    assert isinstance(resolved["watch_interval"], float)
    assert resolved["strict_config"] is False


def test_resolve_config_env_overrides(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Environment variables for watch interval and log level should override."""
    # --- setup ---
    root: RootConfigInput = {"builds": [{"include": ["src/**"], "out": "dist"}]}
    args = _args()

    # --- patch and execute ---
    monkeypatch.setenv(mod_const.DEFAULT_ENV_WATCH_INTERVAL, "9.9")
    monkeypatch.setenv(mod_const.DEFAULT_ENV_LOG_LEVEL, "debug")
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    resolved = mod_resolve.resolve_config(root, args, tmp_path, tmp_path)

    # --- validate ---
    assert abs(resolved["watch_interval"] - 9.9) < 0.001
    assert resolved["log_level"] == "debug"


def test_resolve_config_invalid_env_watch_falls_back(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Invalid watch interval env var should log warning and use default."""
    # --- setup ---
    root: RootConfigInput = {"builds": [{"include": ["src/**"], "out": "dist"}]}
    args = _args()

    # --- patch and execute ---
    monkeypatch.setenv(mod_const.DEFAULT_ENV_WATCH_INTERVAL, "badvalue")
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    resolved = mod_resolve.resolve_config(root, args, tmp_path, tmp_path)

    # --- validate ---
    assert isinstance(resolved["watch_interval"], float)
    assert resolved["watch_interval"] == DEFAULT_WATCH_INTERVAL


def test_resolve_config_propagates_cli_log_level(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """CLI --log-level should propagate into resolved root and runtime."""
    # --- setup ---
    args = _args(log_level="trace")
    root: RootConfigInput = {"builds": [{"include": ["src/**"], "out": "dist"}]}

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    resolved = mod_resolve.resolve_config(root, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["log_level"] == "trace"
    assert mod_runtime.current_runtime["log_level"] == "trace"


def test_resolve_build_config_add_exclude_extends(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    # --- setup ---
    raw = make_build_input(exclude=["*.tmp"], include=["src/**"])
    args = _args(add_exclude=["*.log"])

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    patterns = [str(e["path"]) for e in resolved["exclude"]]
    assert "*.tmp" in patterns
    assert "*.log" in patterns
    origins = {e["origin"] for e in resolved["exclude"]}
    assert "config" in origins and "cli" in origins


def test_resolve_build_config_handles_empty_include(tmp_path: Path) -> None:
    # --- setup ---
    args = _args()
    raw = make_build_input(include=[])

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert resolved["include"] == []


def test_resolve_build_config_with_absolute_include(tmp_path: Path) -> None:
    # --- setup ---
    abs_src = tmp_path / "src"
    abs_src.mkdir()
    args = _args()
    raw = make_build_input(include=[str(abs_src)])

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    inc = resolved["include"][0]
    assert inc["base"] == abs_src.resolve()
    assert inc["path"] == "."


def test_resolve_build_config_inherits_root_gitignore_setting(tmp_path: Path) -> None:
    # --- setup ---
    root_cfg: RootConfigInput = {"respect_gitignore": False}
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path, root_cfg)

    # --- validate ---
    assert resolved["respect_gitignore"] is False


def test_resolve_build_config_preserves_trailing_slash(tmp_path: Path):
    # --- setup ---
    raw: BuildConfigInput = {"include": ["src/"], "out": "dist"}
    args = Namespace()  # empty placeholder

    # --- execute ---
    result = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path, {})
    inc_path = result["include"][0]["path"]

    # --- validate ---
    assert isinstance(inc_path, str)
    assert inc_path.endswith("/"), f"trailing slash lost: {inc_path!r}"
