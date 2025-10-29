# tests/test_cli_gitignore.py
"""Tests for .gitignore handling and precedence in module.cli."""

import json
import shutil
from pathlib import Path

import pytest
from pytest import MonkeyPatch

import pocket_build.cli as mod_cli
import pocket_build.meta as mod_meta

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_config(tmp_path: Path, builds: list[dict[str, object]]) -> Path:
    """Helper to write a .script.json file."""
    cfg = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    cfg.write_text(json.dumps({"builds": builds}))
    return cfg


def write_gitignore(tmp_path: Path, patterns: str) -> Path:
    path = tmp_path / ".gitignore"
    path.write_text(patterns)
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_default_respects_gitignore(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """By default, .gitignore patterns are respected."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "keep.txt").write_text("ok")
    (src / "skip.tmp").write_text("no")

    write_gitignore(tmp_path, "*.tmp\n")
    make_config(tmp_path, [{"include": ["src/**"], "out": "dist"}])

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    out = capsys.readouterr().out
    dist = tmp_path / "dist"

    assert code == 0
    assert (dist / "keep.txt").exists()
    assert not (dist / "skip.tmp").exists()
    assert "Build completed" in out


def test_config_disables_gitignore(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Root config can globally disable .gitignore."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "file.tmp").write_text("ignored?")

    write_gitignore(tmp_path, "*.tmp\n")

    cfg = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    cfg.write_text(
        json.dumps(
            {
                "respect_gitignore": False,
                "builds": [{"include": ["src/**"], "out": "dist"}],
            }
        )
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    out = capsys.readouterr().out
    dist = tmp_path / "dist"

    assert code == 0
    # file.tmp should NOT be excluded since gitignore disabled
    assert (dist / "file.tmp").exists()
    assert "Build completed" in out


def test_build_enables_gitignore_even_if_root_disabled(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A specific build can override root and re-enable .gitignore."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "x.tmp").write_text("ignored?")
    (src / "x.txt").write_text("keep")

    write_gitignore(tmp_path, "*.tmp\n")

    cfg = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    cfg.write_text(
        json.dumps(
            {
                "respect_gitignore": False,
                "builds": [
                    {"include": ["src/**"], "out": "dist", "respect_gitignore": True}
                ],
            }
        )
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    out = capsys.readouterr().out
    dist = tmp_path / "dist"

    assert code == 0
    assert (dist / "x.txt").exists()
    assert not (dist / "x.tmp").exists()
    assert "Build completed" in out


def test_cli_disables_gitignore_even_if_enabled_in_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--no-gitignore should always take precedence over config."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "ignore.tmp").write_text("ignore")
    (src / "keep.txt").write_text("keep")

    write_gitignore(tmp_path, "*.tmp\n")
    make_config(tmp_path, [{"include": ["src/**"], "out": "dist"}])

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--no-gitignore"])

    # --- verify ---
    out = capsys.readouterr().out
    dist = tmp_path / "dist"

    assert code == 0
    # .gitignore ignored
    assert (dist / "ignore.tmp").exists()
    assert (dist / "keep.txt").exists()
    assert "Build completed" in out


def test_cli_enables_gitignore_even_if_config_disables_it(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--gitignore should re-enable even if config disables it."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "skip.tmp").write_text("ignored?")
    (src / "keep.txt").write_text("keep")

    write_gitignore(tmp_path, "*.tmp\n")

    cfg = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    cfg.write_text(
        json.dumps(
            {
                "respect_gitignore": False,
                "builds": [{"include": ["src/**"], "out": "dist"}],
            }
        )
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(["--gitignore"])

    # --- verify ---
    out = capsys.readouterr().out
    dist = tmp_path / "dist"

    assert code == 0
    assert (dist / "keep.txt").exists()
    assert not (dist / "skip.tmp").exists()
    assert "Build completed" in out


def test_gitignore_patterns_append_to_existing_excludes(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Patterns from .gitignore should merge with config exclude list."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "foo.tmp").write_text("tmp")
    (src / "bar.log").write_text("log")
    (src / "baz.txt").write_text("ok")

    write_gitignore(tmp_path, "*.log\n")

    make_config(
        tmp_path, [{"include": ["src/**"], "exclude": ["*.tmp"], "out": "dist"}]
    )

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main([])

    # --- verify ---
    out = capsys.readouterr().out
    dist = tmp_path / "dist"

    assert code == 0
    assert not (dist / "foo.tmp").exists()  # excluded by config
    assert not (dist / "bar.log").exists()  # excluded by gitignore
    assert (dist / "baz.txt").exists()  # should survive
    assert "Build completed" in out


def test_cli_gitignore_disable_then_enable(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
):
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.tmp").write_text("x")
    (src / "b.txt").write_text("y")
    write_gitignore(tmp_path, "*.tmp\n")
    make_config(tmp_path, [{"include": ["src/**"], "out": "dist"}])

    # --- patch, execute and verify ---
    monkeypatch.chdir(tmp_path)
    mod_cli.main(["--no-gitignore"])
    assert (tmp_path / "dist/a.tmp").exists()
    shutil.rmtree(tmp_path / "dist")
    mod_cli.main(["--gitignore"])
    assert not (tmp_path / "dist/a.tmp").exists()
