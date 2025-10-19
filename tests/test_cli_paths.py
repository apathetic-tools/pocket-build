# tests/test_cli_paths.py
"""Tests for pocket_build.cli (module and single-file versions)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from pocket_build.meta import PROGRAM_SCRIPT


def test_configless_run_with_include_flag(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should run successfully without a config file when --include is provided."""
    import pocket_build.cli as mod_cli

    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("hello")

    # --- patch and execute ---
    with monkeypatch.context() as mp:
        # No config file on purpose
        mp.chdir(tmp_path)
        code = mod_cli.main(["--include", "src/**", "--out", "dist"])

    # --- verify ---
    captured = capsys.readouterr()
    out = captured.out + captured.err

    # Should exit successfully
    assert code == 0

    # Output directory should exist and contain copied files
    dist = tmp_path / "dist"
    assert dist.exists()
    assert (dist / "foo.txt").exists()

    # Log output should mention CLI-only mode
    assert "CLI-only mode" in out or "no config file" in out
    assert "Build completed" in out


def test_configless_run_with_add_include_flag(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should run in CLI-only mode when --add-include is provided (no config)."""
    import pocket_build.cli as mod_cli

    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "bar.txt").write_text("world")

    # --- patch and execute ---
    with monkeypatch.context() as mp:
        mp.chdir(tmp_path)
        code = mod_cli.main(["--add-include", "src/**", "--out", "outdir"])

    # --- verify ---
    out = capsys.readouterr().out

    assert code == 0
    assert (tmp_path / "outdir" / "bar.txt").exists()
    assert "CLI-only" in out or "no config file" in out


def test_custom_config_path(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import pocket_build.cli as mod_cli

    # --- setup ---
    cfg = tmp_path / "custom.json"
    cfg.write_text('{"builds": [{"include": [], "out": "dist"}]}')

    # --- patch and execute ---
    with monkeypatch.context() as mp:
        mp.chdir(tmp_path)
        code = mod_cli.main(["--config", str(cfg)])

    # --- verify ---
    out = capsys.readouterr().out
    assert code == 0
    assert "Using config: custom.json" in out


def test_out_flag_overrides_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Should use the --out flag instead of the config-defined output path."""
    import pocket_build.cli as mod_cli

    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("hello")

    config = tmp_path / f".{PROGRAM_SCRIPT}.json"
    config.write_text(
        json.dumps(
            {"builds": [{"include": ["src/**"], "exclude": [], "out": "ignored"}]}
        )
    )

    # --- patch and execute ---
    with monkeypatch.context() as mp:
        mp.chdir(tmp_path)
        code = mod_cli.main(["--out", "override-dist"])

    # --- verify ---
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
) -> None:
    """--out should be relative to where the command is run (cwd)."""
    import pocket_build.cli as mod_cli

    # --- setup ---
    project = tmp_path / "project"
    project.mkdir()
    (project / "src").mkdir()
    (project / "src" / "file.txt").write_text("data")

    config = project / f".{PROGRAM_SCRIPT}.json"
    config.write_text(
        json.dumps({"builds": [{"include": ["src/**"], "out": "ignored"}]})
    )

    cwd = tmp_path / "runner"
    cwd.mkdir()

    # --- patch and execute ---
    with monkeypatch.context() as mp:
        mp.chdir(cwd)
        code = mod_cli.main(["--config", str(config), "--out", "output"])

    # --- verify ---
    assert code == 0

    output_dir = cwd / "output"
    assert (output_dir / "file.txt").exists()
    # Ensure it didn't build the script near the config file, but cwd instead
    assert not (project / "output").exists()


def test_config_out_relative_to_config_file(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Out path in config should be relative to the config file itself."""
    import pocket_build.cli as mod_cli

    # --- setup ---
    project = tmp_path / "project"
    project.mkdir()
    (project / "src").mkdir()
    (project / "src" / "file.txt").write_text("data")

    config = project / f".{PROGRAM_SCRIPT}.json"
    config.write_text(json.dumps({"builds": [{"include": ["src/**"], "out": "dist"}]}))

    # --- patch and execute ---
    with monkeypatch.context() as mp:
        cwd = tmp_path / "runner"
        cwd.mkdir()
        mp.chdir(cwd)
        code = mod_cli.main(["--config", str(config)])

    # --- verify ---
    assert code == 0

    dist_dir = project / "dist"
    # Contents of src should be copied directly into dist/
    assert (dist_dir / "file.txt").exists()
    # Ensure it didn't build relative to the CWD
    assert not (cwd / "dist").exists()


def test_python_config_preferred_over_json(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A .script.py config should take precedence over .jsonc/.json."""
    import pocket_build.cli as mod_cli

    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "from_py.txt").write_text("hello from py")
    (src_dir / "from_json.txt").write_text("hello from json")

    # Create both config types — the Python one should win.
    py_cfg = tmp_path / f".{PROGRAM_SCRIPT}.py"
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

    jsonc_cfg = tmp_path / f".{PROGRAM_SCRIPT}.jsonc"
    jsonc_cfg.write_text(json_dump)

    json_cfg = tmp_path / f".{PROGRAM_SCRIPT}.json"
    json_cfg.write_text(json_dump)

    # --- patch and execute ---
    with monkeypatch.context() as mp:
        mp.chdir(tmp_path)
        code = mod_cli.main([])

    # --- verify ---
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
    ext: str,
) -> None:
    """
    Both .script.jsonc and .script.json
    configs should be detected and used.
    """
    import pocket_build.cli as mod_cli

    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "hello.txt").write_text("hello")

    jsonc_cfg = tmp_path / f".{PROGRAM_SCRIPT}{ext}"
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

    # --- patch and execute ---
    with monkeypatch.context() as mp:
        mp.chdir(tmp_path)
        code = mod_cli.main([])

    # --- verify ---
    out = capsys.readouterr().out

    assert code == 0
    dist = tmp_path / "dist"
    assert (dist / "hello.txt").exists()
    assert "Build completed" in out
