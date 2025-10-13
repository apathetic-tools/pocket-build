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

from tests.conftest import RuntimeLike


def test_main_no_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """Should print a warning and return exit code 1 when config is missing."""
    monkeypatch.chdir(tmp_path)

    code = runtime_env.main([])
    assert code == 1

    out = capsys.readouterr().out
    assert "No build config" in out


def test_main_with_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """Should detect config, run one build, and exit cleanly."""
    config = tmp_path / ".pocket-build.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))
    monkeypatch.chdir(tmp_path)

    code = runtime_env.main([])
    out = capsys.readouterr().out

    assert code == 0
    assert "Build completed" in out


def test_help_flag(
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """Should print usage information and exit cleanly when --help is passed."""
    # Capture SystemExit since argparse exits after printing help.
    with pytest.raises(SystemExit) as e:
        runtime_env.main(["--help"])

    # Argparse exits with code 0 for --help
    assert e.value.code == 0

    out = capsys.readouterr().out
    assert "usage:" in out.lower()
    assert "pocket-build" in out
    assert "--out" in out


def test_version_flag(
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """Should print version and commit info cleanly."""
    code = runtime_env.main(["--version"])
    out = capsys.readouterr().out

    assert code == 0
    assert "Pocket Build" in out

    assert re.search(r"\d+\.\d+\.\d+", out)

    env_mod = cast(ModuleType, runtime_env)
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
    runtime_env: RuntimeLike,
) -> None:
    """Should suppress most output but still succeed."""
    config = tmp_path / ".pocket-build.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))
    monkeypatch.chdir(tmp_path)

    code = runtime_env.main(["--quiet"])
    out = capsys.readouterr().out

    assert code == 0
    # should not contain normal messages
    assert "Build completed" not in out
    assert "All builds complete" not in out


def test_verbose_flag(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
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

    code = runtime_env.main(["--verbose"])
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
    runtime_env: RuntimeLike,
) -> None:
    """Should fail when both --verbose and --quiet are provided."""
    config = tmp_path / ".pocket-build.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))
    monkeypatch.chdir(tmp_path)

    # argparse should exit with SystemExit(2)
    with pytest.raises(SystemExit) as e:
        runtime_env.main(["--quiet", "--verbose"])

    assert e.value.code == 2  # argparse error exit code

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "not allowed with argument" in combined or "mutually exclusive" in combined
    assert "--quiet" in combined and "--verbose" in combined


def test_custom_config_path(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
):
    cfg = tmp_path / "custom.json"
    cfg.write_text('{"builds": [{"include": [], "out": "dist"}]}')
    monkeypatch.chdir(tmp_path)
    code = runtime_env.main(["--config", str(cfg)])
    out = capsys.readouterr().out
    assert code == 0
    assert "Using config: custom.json" in out


def test_out_flag_overrides_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
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
    code = runtime_env.main(["--out", "override-dist"])
    out = capsys.readouterr().out

    assert code == 0
    # Confirm it built into the override directory
    override_dir = tmp_path / "override-dist"
    assert override_dir.exists()

    # Confirm it built into the override directory (contents only)
    assert (override_dir / "foo.txt").exists()

    # Optional: check output logs
    assert "override-dist" in out


def test_out_flag_relative_to_cwd(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
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
    code = runtime_env.main(["--config", str(config), "--out", "output"])
    assert code == 0

    output_dir = cwd / "output"
    assert (output_dir / "file.txt").exists()
    # Ensure it didn't build the script near the config file, but cwd instead
    assert not (project / "output").exists()


def test_config_out_relative_to_config_file(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
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

    code = runtime_env.main(["--config", str(config)])
    assert code == 0

    dist_dir = project / "dist"
    # Contents of src should be copied directly into dist/
    assert (dist_dir / "file.txt").exists()
    # Ensure it didn't build relative to the CWD
    assert not (cwd / "dist").exists()


def test_include_flag_overrides_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
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
    code = runtime_env.main(["--include", "src/**"])
    out = capsys.readouterr().out

    assert code == 0
    dist_dir = tmp_path / "dist"
    # Should copy src contents (flattened), not 'other'
    assert (dist_dir / "foo.txt").exists()
    assert not (dist_dir / "other").exists()
    assert "Build completed" in out


def test_exclude_flag_overrides_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
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
    code = runtime_env.main(["--exclude", "*.tmp"])
    out = capsys.readouterr().out

    assert code == 0
    dist_dir = tmp_path / "dist"
    # The .tmp file should be excluded now
    assert (dist_dir / "keep.txt").exists()
    assert not (dist_dir / "ignore.tmp").exists()
    assert "Build completed" in out


def test_python_config_preferred_over_json(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
) -> None:
    """A .pocket-build.py config should take precedence over .jsonc/.json."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "from_py.txt").write_text("hello from py")
    (src_dir / "from_json.txt").write_text("hello from json")

    # Create both config types — the Python one should win.
    py_cfg = tmp_path / ".pocket-build.py"
    py_cfg.write_text(
        """
builds = [
    {"include": ["src/from_py.txt"], "exclude": [], "out": "dist"}
]
"""
    )

    json_dump = json.dumps(
        {"builds": [{"include": ["src/from_json.txt"], "out": "dist"}]}
    )

    jsonc_cfg = tmp_path / ".pocket-build.jsonc"
    jsonc_cfg.write_text(json_dump)

    json_cfg = tmp_path / ".pocket-build.json"
    json_cfg.write_text(json_dump)

    monkeypatch.chdir(tmp_path)
    code = runtime_env.main([])
    out = capsys.readouterr().out

    assert code == 0
    dist = tmp_path / "dist"
    # Only the Python config file's include should have been used
    assert (dist / "src" / "from_py.txt").exists()
    assert not (dist / "src" / "from_json.txt").exists()
    assert "Build completed" in out


@pytest.mark.parametrize("ext", [".jsonc", ".json"])
def test_json_and_jsonc_config_supported(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_env: RuntimeLike,
    ext: str,
) -> None:
    """
    Both .pocket-build.jsonc and .pocket-build.json
    configs should be detected and used.
    """
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "hello.txt").write_text("hello")

    jsonc_cfg = tmp_path / f".pocket-build{ext}"
    jsonc_cfg.write_text(
        """
        // comment allowed in JSONC
        {
            "builds": [
                {
                    "include": ["src/**"],
                    "out": "dist" // trailing comment
                }
            ]
        }
        """
    )

    monkeypatch.chdir(tmp_path)
    code = runtime_env.main([])
    out = capsys.readouterr().out

    assert code == 0
    dist = tmp_path / "dist"
    assert (dist / "hello.txt").exists()
    assert "Build completed" in out
