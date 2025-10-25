# tests/private/test_build_compute_dest.py
"""Tests for _compute_dest() destination resolution logic.

Checklist:
- explicit_dest — explicit 'dest' field override.
- glob_pattern — strips non-glob prefix correctly (rsync-like flattening).
- non_glob_pattern — copies relative to base when no globs present.
- base_not_ancestor — falls back safely when base is not ancestor.
- directory_literal — includes directory itself under out_dir.
- star_star_glob — '**' behaves like 'src/**' (copies contents only).
- top_level_glob — '*.ext' copies files directly into out_dir.
"""

# we import `_` private for testing purposes only
# pyright: reportPrivateUsage=false
# ruff: noqa: F401

from pathlib import Path

from pocket_build.build import _compute_dest


def test_compute_dest_with_explicit_dest(tmp_path: Path) -> None:
    """Explicit 'dest' field overrides computed path."""
    # --- setup ---
    src = tmp_path / "a/b.txt"
    base = tmp_path
    out_dir = tmp_path / "out"
    dest_name = "custom"

    # --- execute ---
    result = _compute_dest(src, base, out_dir, "a/*.txt", dest_name)

    # --- verify ---
    assert result == out_dir / "custom"


def test_compute_dest_with_glob_pattern(tmp_path: Path) -> None:
    """Glob pattern strips non-glob prefix correctly (rsync-like flattening)."""
    # --- setup ---
    src = tmp_path / "a/sub/b.txt"
    base = tmp_path
    out_dir = tmp_path / "out"
    pattern = "a/*"

    # --- execute ---
    result = _compute_dest(src, base, out_dir, pattern, None)

    # --- verify ---
    # The prefix 'a/' (the glob root) is stripped — file goes under 'out/sub/b.txt'
    assert result == out_dir / "sub/b.txt"


def test_compute_dest_without_glob(tmp_path: Path) -> None:
    """Non-glob pattern copies relative to base."""
    # --- setup ---
    src = tmp_path / "docs/readme.md"
    base = tmp_path
    out_dir = tmp_path / "build"
    pattern = "docs/readme.md"

    # --- execute ---
    result = _compute_dest(src, base, out_dir, pattern, None)

    # --- verify ---
    assert result == out_dir / "docs/readme.md"


def test_compute_dest_base_not_ancestor(tmp_path: Path) -> None:
    """Falls back safely when base is not an ancestor of src."""
    # --- setup ---
    src = Path("/etc/hosts")
    base = tmp_path
    out_dir = tmp_path / "out"
    pattern = "*.txt"

    # --- execute ---
    result = _compute_dest(src, base, out_dir, pattern, None)

    # --- verify ---
    # When base and src don't align, fallback uses just the filename
    assert result == out_dir / "hosts"


def test_compute_dest_directory_literal(tmp_path: Path) -> None:
    """Including 'src' (no glob) should copy directory itself under out_dir."""
    # --- setup ---
    src = tmp_path / "src"
    base = tmp_path
    out_dir = tmp_path / "dist"
    pattern = "src"

    # --- execute ---
    result = _compute_dest(src, base, out_dir, pattern, None)

    # --- verify ---
    # Directory itself preserved → out/src
    assert result == out_dir / "src"


def test_compute_dest_star_star_glob(tmp_path: Path) -> None:
    """Including 'src/**' should copy contents only (flattened into out_dir)."""
    # --- setup ---
    src = tmp_path / "src" / "deep" / "x.txt"
    base = tmp_path
    out_dir = tmp_path / "dist"
    pattern = "src/**"

    # --- execute ---
    result = _compute_dest(src, base, out_dir, pattern, None)

    # --- verify ---
    # The 'src/' prefix is stripped
    assert result == out_dir / "deep/x.txt"


def test_compute_dest_top_level_glob(tmp_path: Path) -> None:
    """Including '*.txt' should place top-level files directly in out_dir."""
    # --- setup ---
    src = tmp_path / "a.txt"
    base = tmp_path
    out_dir = tmp_path / "out"
    pattern = "*.txt"

    # --- execute ---
    result = _compute_dest(src, base, out_dir, pattern, None)

    # --- verify ---
    # Pattern is at top level — file goes directly in out_dir
    assert result == out_dir / "a.txt"


def test_compute_dest_with_trailing_slash(tmp_path: Path) -> None:
    # --- setup ---
    src = tmp_path / "src" / "a.txt"
    src.parent.mkdir()
    src.write_text("x")
    base = tmp_path
    out_dir = tmp_path / "out"
    pattern = "src/"

    # --- execute ---
    result = _compute_dest(src, base, out_dir, pattern, None)

    # --- verify ---
    assert result == out_dir / "a.txt"
