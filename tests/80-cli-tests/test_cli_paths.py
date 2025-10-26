# tests/test_cli_paths.py
"""Tests for package.cli (module and single-file versions)."""

import json
from pathlib import Path

import pytest
from pytest import CaptureFixture, MonkeyPatch

import pocket_build.cli as mod_cli
from pocket_build.meta import PROGRAM_SCRIPT


def test_configless_run_with_include_flag(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    """Should run successfully without a config file when --include is provided."""
    # --- setup ---
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("hello")

    # --- patch and execute ---
    # No config file on purpose
    monkeypatch.chdir(tmp_path)
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
    capsys: CaptureFixture[str],
) -> None:
    """Should run in CLI-only mode when --add-include is provided (no config)."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "bar.txt").write_text("world")

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--add-include", "src/**", "--out", "outdir"])

    # --- verify ---
    out = capsys.readouterr().out

    assert code == 0
    assert (tmp_path / "outdir" / "bar.txt").exists()
    assert "CLI-only" in out or "no config file" in out


def test_custom_config_path(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    # --- setup ---
    cfg = tmp_path / "custom.json"
    cfg.write_text('{"builds": [{"include": [], "out": "dist"}]}')

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--config", str(cfg)])

    # --- verify ---
    out = capsys.readouterr().out
    assert code == 0
    assert "Using config: custom.json" in out


def test_out_flag_overrides_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    """Should use the --out flag instead of the config-defined output path."""
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
    monkeypatch.chdir(tmp_path)
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
    monkeypatch.chdir(cwd)
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
    # --- setup ---
    project = tmp_path / "project"
    project.mkdir()
    (project / "src").mkdir()
    (project / "src" / "file.txt").write_text("data")

    config = project / f".{PROGRAM_SCRIPT}.json"
    config.write_text(json.dumps({"builds": [{"include": ["src/**"], "out": "dist"}]}))

    # --- patch and execute ---
    cwd = tmp_path / "runner"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
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
    capsys: CaptureFixture[str],
) -> None:
    """A .script.py config should take precedence over .jsonc/.json."""
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
    monkeypatch.chdir(tmp_path)
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
    capsys: CaptureFixture[str],
    ext: str,
) -> None:
    """
    Both .script.jsonc and .script.json
    configs should be detected and used.
    """
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
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    out = capsys.readouterr().out

    assert code == 0
    dist = tmp_path / "dist"
    assert (dist / "hello.txt").exists()
    assert "Build completed" in out


# ---------------------------------------------------------------------------
# Path normalization and absolute handling
# ---------------------------------------------------------------------------


def test_absolute_include_and_out(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Absolute paths on CLI should copy correctly and not resolve relative to cwd."""
    import pocket_build.cli as mod_cli

    # --- setup ---
    abs_src = tmp_path / "abs_src"
    abs_src.mkdir()
    (abs_src / "x.txt").write_text("absolute")
    abs_out = tmp_path / "abs_out"

    # --- execute ---
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    monkeypatch.chdir(subdir)  # move cwd away from src/out

    code = mod_cli.main(["--include", str(abs_src / "**"), "--out", str(abs_out)])

    # --- verify ---
    assert code == 0
    assert (abs_out / "x.txt").exists()
    # should not create relative dist in cwd
    assert not (tmp_path / "subdir" / "abs_out").exists()


def test_relative_include_with_parent_reference(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Relative include like ../shared/** should resolve against cwd correctly."""
    # --- setup ---
    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "file.txt").write_text("data")
    cwd = tmp_path / "project"
    cwd.mkdir()

    # --- execute ---
    monkeypatch.chdir(cwd)
    code = mod_cli.main(["--include", "../shared/**", "--out", "dist"])

    # --- verify ---
    assert code == 0
    dist = cwd / "dist"
    assert (dist / "file.txt").exists()


def test_mixed_relative_and_absolute_includes(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Mixing relative and absolute include paths should work with distinct bases."""
    # --- setup ---
    rel_src = tmp_path / "rel_src"
    abs_src = tmp_path / "abs_src"
    rel_src.mkdir()
    abs_src.mkdir()
    (rel_src / "r.txt").write_text("r")
    (abs_src / "a.txt").write_text("a")

    abs_out = tmp_path / "mixed_out"

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(
        ["--include", "rel_src/**", str(abs_src / "**"), "--out", str(abs_out)]
    )

    # --- verify ---
    assert code == 0
    assert (abs_out / "r.txt").exists()
    assert (abs_out / "a.txt").exists()


def test_trailing_slash_include(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Ensure `src/` copies contents directly (not nested src/src)."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "inner.txt").write_text("ok")

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--include", "src/", "--out", "outdir"])

    # --- verify ---
    assert code == 0
    outdir = tmp_path / "outdir"
    assert (outdir / "inner.txt").exists()
    assert not (outdir / "src" / "inner.txt").exists()


def test_absolute_out_does_not_create_relative_copy(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Absolute --out should not create nested relative copies."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "one.txt").write_text("1")
    abs_out = tmp_path / "absolute_out"

    # --- execute ---
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    code = mod_cli.main(["--include", str(tmp_path / "src/**"), "--out", str(abs_out)])

    # --- verify ---
    assert code == 0
    assert (abs_out / "one.txt").exists()
    assert not (tmp_path / "subdir" / "absolute_out").exists()


def test_dot_prefix_include(monkeypatch: MonkeyPatch, tmp_path: Path):
    """'./src' include should behave the same as 'src'."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "file.txt").write_text("x")

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--include", "./src/**", "--out", "dist"])

    # --- verify ---
    assert code == 0
    assert (tmp_path / "dist" / "file.txt").exists()


def test_trailing_slash_on_out(monkeypatch: MonkeyPatch, tmp_path: Path):
    """Trailing slash in --out should not change output directory."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "foo.txt").write_text("bar")

    # --- execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--include", "src/**", "--out", "dist/"])

    # --- verify ---
    assert code == 0
    assert (tmp_path / "dist" / "foo.txt").exists()
