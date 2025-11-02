# tests/test_config_resolve.py

"""Tests for pocket_build.config_resolve."""

import argparse
from argparse import Namespace
from pathlib import Path

import pytest

import pocket_build.config_resolve as mod_resolve
import pocket_build.config_types as mod_types
import pocket_build.logs as mod_logs
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


def test_resolve_build_config_from_config_paths(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Ensure config-based include/out/exclude resolve relative to config_dir."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], exclude=["*.tmp"], out="dist")
    args = _args()

    # --- patch and execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    inc = resolved["include"][0]
    exc = resolved["exclude"][0]
    out = resolved["out"]

    assert inc["root"] == tmp_path
    assert exc["root"] == tmp_path
    assert out["root"] == tmp_path
    assert resolved["log_level"].lower() == "info"
    assert resolved["respect_gitignore"] is True
    assert resolved["__meta__"]["config_root"] == tmp_path
    assert resolved["__meta__"]["cli_root"] == tmp_path


def test_resolve_build_config_cli_overrides_include_and_out(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """CLI --include and --out should override config include/out."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], out="dist")
    args = _args(include=["cli_src/**"], out="cli_dist")

    # --- patch and execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    inc = resolved["include"][0]
    out = resolved["out"]

    assert inc["path"] == "cli_src/**"
    assert inc["origin"] == "cli"
    assert out["path"] == "cli_dist"
    assert out["origin"] == "cli"


def test_resolve_build_config_add_include_extends(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """--add-include should append to config includes, not override."""
    # --- setup ---
    raw = make_build_input(include=["src/**"])
    args = _args(add_include=["extra/**"])

    # --- patch and execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    paths = [i["path"] for i in resolved["include"]]
    assert "src/**" in paths
    assert "extra/**" in paths
    origins = {i["origin"] for i in resolved["include"]}
    assert "config" in origins
    assert "cli" in origins


def test_resolve_build_config_gitignore_patterns_added(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """When .gitignore exists, its patterns should be appended as gitignore excludes."""
    # --- setup ---
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.log\n# comment\ncache/\n")
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- patch and execute ---
    with module_logger.use_level("debug"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    git_excludes = [e for e in resolved["exclude"] if e["origin"] == "gitignore"]
    patterns = [str(e["path"]) for e in git_excludes]
    assert "*.log" in patterns
    assert "cache/" in patterns


def test_resolve_build_config_respects_cli_exclude_override(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """CLI --exclude should override config excludes."""
    # --- setup ---
    raw = make_build_input(exclude=["*.tmp"], include=["src/**"])
    args = _args(exclude=["*.bak"])

    # --- patch and execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    excl = [str(e["path"]) for e in resolved["exclude"]]
    assert "*.bak" in excl
    assert "*.tmp" not in excl


def test_resolve_build_config_respects_dest_override(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """IncludeResolved with explicit dest should survive resolution unchanged."""
    # --- setup ---
    raw = make_build_input(include=["src/**"], out="dist")
    args = _args()

    # --- patch and execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    out = resolved["out"]
    assert out["origin"] == "config"
    assert out["root"] == tmp_path
    assert out["path"] == "dist"


def test_resolve_build_config_respect_gitignore_false(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """If --no-gitignore is passed, .gitignore patterns are not loaded."""
    # --- setup ---
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.log\n")
    raw = make_build_input(include=["src/**"], respect_gitignore=False)
    args = _args(respect_gitignore=False)

    # --- patch and execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    assert all(e["origin"] != "gitignore" for e in resolved["exclude"])
    assert resolved["respect_gitignore"] is False


def test_resolve_build_config_add_exclude_extends(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    # --- setup ---
    raw = make_build_input(exclude=["*.tmp"], include=["src/**"])
    args = _args(add_exclude=["*.log"])

    # --- patch and execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    patterns = [str(e["path"]) for e in resolved["exclude"]]
    assert "*.tmp" in patterns
    assert "*.log" in patterns
    origins = {e["origin"] for e in resolved["exclude"]}
    assert "config" in origins
    assert "cli" in origins


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
    assert inc["root"] == abs_src.resolve()
    assert inc["path"] == "."


def test_resolve_build_config_inherits_root_gitignore_setting(tmp_path: Path) -> None:
    # --- setup ---
    root_cfg: mod_types.RootConfig = {"respect_gitignore": False}
    raw = make_build_input(include=["src/**"])
    args = _args()

    # --- execute ---
    resolved = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path, root_cfg)

    # --- validate ---
    assert resolved["respect_gitignore"] is False


def test_resolve_build_config_preserves_trailing_slash(tmp_path: Path) -> None:
    # --- setup ---
    raw: mod_types.BuildConfig = {"include": ["src/"], "out": "dist"}
    args = Namespace()  # empty placeholder

    # --- execute ---
    result = mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path, {})
    inc_path = result["include"][0]["path"]

    # --- validate ---
    assert isinstance(inc_path, str)
    assert inc_path.endswith("/"), f"trailing slash lost: {inc_path!r}"


def test_resolve_build_config_warns_for_missing_include_root(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Warn if include root directory does not exist and pattern is not a glob."""
    # --- setup ---
    missing_root = tmp_path / "nonexistent_root"
    raw = make_build_input(include=[f"{missing_root}/src"])
    args = _args()

    # --- patch and execute ---
    with module_logger.use_level("info"):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    out = capsys.readouterr().err.lower()
    assert "Include root does not exist".lower() in out


def test_resolve_build_config_warns_for_missing_absolute_include(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Warn if absolute include path does not exist and pattern is not a glob."""
    # --- setup ---
    abs_missing = tmp_path / "abs_missing_dir"
    raw = make_build_input(include=[str(abs_missing)])
    args = _args()

    # --- patch and execute ---
    with module_logger.use_level("info"):
        mod_resolve.resolve_build_config(raw, args, tmp_path, tmp_path)

    # --- validate ---
    out = capsys.readouterr().err.lower()
    assert "Include path does not exist".lower() in out


def test_resolve_build_config_warns_for_missing_relative_include(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Warn if relative include path does not exist under an existing root."""
    # --- setup ---
    existing_root = tmp_path
    raw = make_build_input(include=["missing_rel_dir"])
    args = _args()

    # --- patch and execute ---
    with module_logger.use_level("info"):
        mod_resolve.resolve_build_config(raw, args, existing_root, tmp_path)

    # --- validate ---
    out = capsys.readouterr().err.lower()
    assert "Include path does not exist".lower() in out
