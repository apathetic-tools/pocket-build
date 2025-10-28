# tests/private/test_config_resolve_paths.py

"""Direct tests for _normalize_base_and_path, ensuring consistent path semantics."""

# pyright: reportPrivateUsage=false

from pathlib import Path

import pocket_build.config_resolve as mod_resolve


def test_relative_path_preserves_string(tmp_path: Path) -> None:
    # --- setup ---
    base = tmp_path
    rel = "src/"

    # --- execute ---
    b, p = mod_resolve._normalize_base_and_path(rel, base)

    # --- verify ---
    assert b == base.resolve()
    # stays a string, not a Path
    assert isinstance(p, str)
    assert p == "src/"


def test_relative_path_as_path_object(tmp_path: Path) -> None:
    # --- setup ---
    rel = Path("src")

    # --- execute ---
    b, p = mod_resolve._normalize_base_and_path(rel, tmp_path)

    # --- verify ---
    assert b == tmp_path.resolve()
    assert isinstance(p, Path)
    assert str(p) == "src"


def test_absolute_literal_dir(tmp_path: Path) -> None:
    # --- setup ---
    abs_dir = tmp_path / "absdir"
    abs_dir.mkdir()

    # --- execute ---
    b, p = mod_resolve._normalize_base_and_path(str(abs_dir), tmp_path)

    # --- verify ---
    assert b == abs_dir.resolve()
    assert p == "."


def test_absolute_trailing_slash_means_contents(tmp_path: Path) -> None:
    # --- setup ---
    abs_dir = tmp_path / "absdir"
    abs_dir.mkdir()
    raw = str(abs_dir) + "/"

    # --- execute ---
    b, p = mod_resolve._normalize_base_and_path(raw, tmp_path)

    # --- verify ---
    assert b == abs_dir.resolve()
    assert p == "**"  # trailing slash → copy contents


def test_absolute_glob_preserves_pattern(tmp_path: Path) -> None:
    # --- setup ---
    abs_dir = tmp_path / "absdir"
    abs_dir.mkdir()
    raw = str(abs_dir) + "/**"

    # --- execute ---
    b, p = mod_resolve._normalize_base_and_path(raw, tmp_path)

    # --- verify ---
    assert b == abs_dir.resolve()
    assert p == "**"


def test_returns_resolved_base_for_relative_context(tmp_path: Path) -> None:
    # --- setup ---
    cwd = tmp_path / "proj"
    cwd.mkdir()

    # --- execute ---
    b, p = mod_resolve._normalize_base_and_path("foo/**", cwd)

    # --- verify ---
    assert b == cwd.resolve()
    assert isinstance(p, str)
    assert p == "foo/**"


def test_handles_absolute_file(tmp_path: Path) -> None:
    # --- setup ---
    f = tmp_path / "file.txt"
    f.write_text("x")

    # --- execute ---
    b, p = mod_resolve._normalize_base_and_path(str(f), tmp_path)

    # --- verify ---
    assert b == f.resolve()
    assert p == "."
