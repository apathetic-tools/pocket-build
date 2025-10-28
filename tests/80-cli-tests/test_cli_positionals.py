# tests/test_cli_positionals.py

"""Tests for positional argument and flag interaction in package.cli."""

from pathlib import Path

import pytest
from pytest import MonkeyPatch

import pocket_build.cli as mod_cli

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_cli(monkeypatch: MonkeyPatch, tmp_path: Path, argv: list[str]) -> int:
    """Helper to run CLI with a temporary working directory."""
    full_argv = [*argv, "--log-level", "trace"]

    # --- patch and execute ---
    monkeypatch.chdir(tmp_path)
    code = mod_cli.main(full_argv)
    return code


def _make_src(tmp_path: Path, *names: str) -> Path:
    """Create dummy source files and return the directory."""
    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    for n in names:
        (src / n).write_text("x")
    return src


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Basic shorthand: src dist
# ---------------------------------------------------------------------------


def test_positional_include_and_out(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """`src dist/` should treat src as include and dist/ as out."""
    # --- setup ---
    _make_src(tmp_path, "file.txt")

    # --- patch and execute ---
    code = _run_cli(monkeypatch, tmp_path, ["src/", "dist"])

    # --- verify ---
    assert code == 0

    dist = tmp_path / "dist"
    assert (dist / "file.txt").exists()


def test_multiple_includes_and_out(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """`src1 src2 dist` should treat src1/src2 as includes and dist as out."""
    # --- setup ---
    (tmp_path / "src1").mkdir()
    (tmp_path / "src2").mkdir()
    (tmp_path / "src1" / "a.txt").write_text("A")
    (tmp_path / "src2" / "b.txt").write_text("B")

    # --- patch and execute ---
    code = _run_cli(monkeypatch, tmp_path, ["src1/", "src2/", "dist"])

    # --- verify ---
    assert code == 0

    dist = tmp_path / "dist"
    assert (dist / "a.txt").exists()
    assert (dist / "b.txt").exists()


# ---------------------------------------------------------------------------
# Explicit --out should make all positionals includes
# ---------------------------------------------------------------------------


def test_explicit_out_allows_many_includes(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """If --out is given, all positionals become includes."""
    # --- setup ---
    _make_src(tmp_path, "one.txt")
    src2 = tmp_path / "src2"
    src2.mkdir()
    (src2 / "two.txt").write_text("two")

    # --- patch and execute ---
    code = _run_cli(monkeypatch, tmp_path, ["src/", "src2/", "--out", "dist"])

    # --- verify ---
    assert code == 0

    dist = tmp_path / "dist"
    assert (dist / "one.txt").exists()
    assert (dist / "two.txt").exists()


# ---------------------------------------------------------------------------
# Explicit --include forbids any positionals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        ["src", "--include", "foo/**"],
        ["src", "out", "--include", "foo/**"],
    ],
)
def test_error_on_positional_with_include(
    monkeypatch: MonkeyPatch, tmp_path: Path, argv: list[str]
) -> None:
    """Any positional args combined with --include should error."""
    # --- setup ---
    _make_src(tmp_path, "a.txt")

    # --- patch, execute and verify ---
    with pytest.raises(SystemExit) as e:
        _run_cli(monkeypatch, tmp_path, argv)
    assert e.value.code == 2


def test_positional_with_dry_run(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    # --- setup ---
    _make_src(tmp_path, "x.txt")

    # --- patch and execute ---
    code = _run_cli(monkeypatch, tmp_path, ["src", "dist", "--dry-run"])

    # --- verify ---
    assert code == 0
    assert not (tmp_path / "dist").exists()


def test_trailing_slash_handled(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    # --- setup ---
    _make_src(tmp_path, "x.txt")

    # --- patch and execute ---
    code = _run_cli(monkeypatch, tmp_path, ["src/", "dist/"])

    # --- verify ---
    assert code == 0
    assert (tmp_path / "dist" / "x.txt").exists()
