# tests/test_cli.py
"""Tests for pocket_build.cli (module and single-file versions)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest
from _pytest.monkeypatch import MonkeyPatch
from conftest import PocketBuildLike


def test_main_no_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Should print a warning and return exit code 1 when config is missing."""
    monkeypatch.chdir(tmp_path)

    code = pocket_build_env.main([])
    assert code == 1

    out = capsys.readouterr().out
    assert "No build config" in out


def test_main_with_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Should detect config, run one build, and exit cleanly."""
    config = tmp_path / ".pocket-build.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))
    monkeypatch.chdir(tmp_path)

    code = pocket_build_env.main([])
    out = capsys.readouterr().out

    assert code == 0
    assert "Build completed" in out


def test_help_flag(
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Should print usage information and exit cleanly when --help is passed."""
    # Capture SystemExit since argparse exits after printing help.
    with pytest.raises(SystemExit) as e:
        pocket_build_env.main(["--help"])

    # Argparse exits with code 0 for --help
    assert e.value.code == 0

    out = capsys.readouterr().out
    assert "usage:" in out.lower()
    assert "pocket-build" in out
    assert "--out" in out


def test_version_flag(
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Should print version and commit info cleanly."""
    code = pocket_build_env.main(["--version"])
    out = capsys.readouterr().out

    assert code == 0
    assert "Pocket Build" in out

    assert re.search(r"\d+\.\d+\.\d+", out)

    env_mod = cast(ModuleType, pocket_build_env)
    if "pocket_build_single" in env_mod.__name__:
        # Single-file build case
        if os.getenv("CI") or os.getenv("GIT_TAG") or os.getenv("GITHUB_REF"):
            assert re.search(r"\([0-9a-f]{4,}\)", out)
        else:
            assert "(unknown (local build))" in out
    else:
        # Modular source version — uses live Git
        assert re.search(r"\([0-9a-f]{4,}\)", out)


def test_quiet_flag(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Should suppress most output but still succeed."""
    config = tmp_path / ".pocket-build.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))
    monkeypatch.chdir(tmp_path)

    code = pocket_build_env.main(["--quiet"])
    out = capsys.readouterr().out

    assert code == 0
    # should not contain normal messages
    assert "Build completed" not in out
    assert "All builds complete" not in out


def test_verbose_flag(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Should print detailed file-level logs when --verbose is used."""
    # create a tiny input directory with a file to copy
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("hello")

    config = tmp_path / ".pocket-build.json"
    config.write_text(
        json.dumps({"builds": [{"include": ["src/**"], "exclude": [], "out": "dist"}]})
    )
    monkeypatch.chdir(tmp_path)

    code = pocket_build_env.main(["--verbose"])
    captured = capsys.readouterr()
    out = captured.out + captured.err

    assert code == 0
    # Verbose mode should show per-file details
    assert "📄" in out or "🚫" in out
    # It should still include summary
    assert "Build completed" in out
    assert "All builds complete" in out


def test_verbose_and_quiet_mutually_exclusive(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """Should fail when both --verbose and --quiet are provided."""
    config = tmp_path / ".pocket-build.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))
    monkeypatch.chdir(tmp_path)

    # argparse should exit with SystemExit(2)
    with pytest.raises(SystemExit) as e:
        pocket_build_env.main(["--quiet", "--verbose"])

    assert e.value.code == 2  # argparse error exit code

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "not allowed with argument" in combined or "mutually exclusive" in combined
    assert "--quiet" in combined and "--verbose" in combined


def test_custom_config_path(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
):
    cfg = tmp_path / "custom.json"
    cfg.write_text('{"builds": [{"include": [], "out": "dist"}]}')
    monkeypatch.chdir(tmp_path)
    code = pocket_build_env.main(["--config", str(cfg)])
    out = capsys.readouterr().out
    assert code == 0
    assert "Using config: custom.json" in out


def test_out_flag_overrides_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
):
    """Should use the --out flag instead of the config-defined output path."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("hello")

    config = tmp_path / ".pocket-build.json"
    config.write_text(
        json.dumps(
            {"builds": [{"include": ["src/**"], "exclude": [], "out": "ignored"}]}
        )
    )

    monkeypatch.chdir(tmp_path)
    code = pocket_build_env.main(["--out", "override-dist"])
    out = capsys.readouterr().out

    assert code == 0
    # Confirm it built into the override directory
    override_dir = tmp_path / "override-dist"
    assert override_dir.exists()
    assert (override_dir / "src" / "foo.txt").exists()
    # Optional: check output logs
    assert "override-dist" in out


def test_out_flag_relative_to_cwd(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
):
    """--out should be relative to where the command is run (cwd)."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "src").mkdir()
    (project / "src" / "file.txt").write_text("data")

    config = project / ".pocket-build.json"
    config.write_text(
        json.dumps({"builds": [{"include": ["src/**"], "out": "ignored"}]})
    )

    cwd = tmp_path / "runner"
    cwd.mkdir()

    monkeypatch.chdir(cwd)
    code = pocket_build_env.main(["--config", str(config), "--out", "output"])
    assert code == 0

    output_dir = cwd / "output"
    assert (output_dir / "src" / "file.txt").exists()
    # Ensure it didn't build near the config file
    assert not (project / "output").exists()


def test_config_out_relative_to_config_file(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
):
    """Out path in config should be relative to the config file itself."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "src").mkdir()
    (project / "src" / "file.txt").write_text("data")

    config = project / ".pocket-build.json"
    config.write_text(json.dumps({"builds": [{"include": ["src/**"], "out": "dist"}]}))

    cwd = tmp_path / "runner"
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    code = pocket_build_env.main(["--config", str(config)])
    assert code == 0

    dist_dir = project / "dist"
    assert (dist_dir / "src" / "file.txt").exists()
    # Ensure it didn't build relative to the CWD
    assert not (cwd / "dist").exists()


def test_include_flag_overrides_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """--include should override config include patterns."""
    # Prepare files
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("ok")

    other_dir = tmp_path / "other"
    other_dir.mkdir()
    (other_dir / "bar.txt").write_text("nope")

    # Config originally points to wrong folder
    config = tmp_path / ".pocket-build.json"
    config.write_text(
        json.dumps(
            {"builds": [{"include": ["other/**"], "exclude": [], "out": "dist"}]}
        )
    )

    monkeypatch.chdir(tmp_path)
    # Override include at CLI level
    code = pocket_build_env.main(["--include", "src/**"])
    out = capsys.readouterr().out

    assert code == 0
    dist_dir = tmp_path / "dist"
    # Should copy src contents, not 'other'
    assert (dist_dir / "src" / "foo.txt").exists()
    assert not (dist_dir / "other").exists()
    assert "Build completed" in out


def test_exclude_flag_overrides_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    pocket_build_env: PocketBuildLike,
) -> None:
    """--exclude should override config exclude patterns."""
    # Create input directory with two files
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "keep.txt").write_text("keep me")
    (src_dir / "ignore.tmp").write_text("ignore me")

    # Config has no exclude rules
    config = tmp_path / ".pocket-build.json"
    config.write_text(json.dumps({"builds": [{"include": ["src/**"], "out": "dist"}]}))

    monkeypatch.chdir(tmp_path)
    # Pass exclude override on CLI
    code = pocket_build_env.main(["--exclude", "*.tmp"])
    out = capsys.readouterr().out

    assert code == 0
    dist_dir = tmp_path / "dist"
    # The .tmp file should be excluded now
    assert (dist_dir / "src" / "keep.txt").exists()
    assert not (dist_dir / "src" / "ignore.tmp").exists()
    assert "Build completed" in out
