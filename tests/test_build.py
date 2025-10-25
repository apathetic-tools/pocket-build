# tests/test_build.py
"""Tests for package.build (module and single-file versions)."""

from pathlib import Path

from pytest import MonkeyPatch

from pocket_build.types import PathResolved
from tests.utils import make_build_cfg, make_include_resolved

# ---------------------------------------------------------------------------
# Local helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# End-to-end tests for run_build()
# ---------------------------------------------------------------------------


def test_run_build_includes_directory_itself(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Including 'src' should copy directory itself → dist/src/..."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("A")

    cfg = make_build_cfg(tmp_path, [make_include_resolved("src", tmp_path)])

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    mod_build.run_build(cfg)

    # --- verify ---
    dist = tmp_path / "dist"
    assert (dist / "src" / "a.txt").exists()


def test_run_build_includes_directory_contents_slash(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Including 'src/' should copy contents only → dist/..."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "b.txt").write_text("B")

    cfg = make_build_cfg(tmp_path, [make_include_resolved("src/**", tmp_path)])

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    mod_build.run_build(cfg)

    # --- verify ---
    dist = tmp_path / "dist"
    assert (dist / "b.txt").exists()
    assert not (dist / "src" / "b.txt").exists()


def test_run_build_includes_directory_contents_single_star(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Including 'src/*' should copy non-hidden immediate contents → dist/...
    Also ensures that the original pattern is stored in PathResolved entries."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "one.txt").write_text("1")
    sub = src / "nested"
    sub.mkdir()
    (sub / "deep.txt").write_text("x")

    pattern = "src/*"
    cfg = make_build_cfg(tmp_path, [make_include_resolved("src/*", tmp_path)])

    # --- capture PathResolved entries passed to copy_item ---
    called: list[PathResolved] = []
    real_copy_item = mod_build.copy_item

    def fake_copy_item(
        src_entry: PathResolved,
        dest_entry: PathResolved,
        exclude_patterns: list[PathResolved],
        dry_run: bool,
    ) -> None:
        called.append(src_entry)
        return real_copy_item(src_entry, dest_entry, exclude_patterns, dry_run)

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    monkeypatch.setattr(mod_build, "copy_item", fake_copy_item)
    mod_build.run_build(cfg)

    # --- verify ---
    dist = tmp_path / "dist"
    # only top-level from src copied
    assert (dist / "one.txt").exists()
    assert not (dist / "nested" / "deep.txt").exists()

    # --- verify metadata propagation ---
    assert called, "copy_item should have been called at least once"
    for entry in called:
        assert "pattern" in entry, "pattern should be preserved in PathResolved"
        assert entry["pattern"] == pattern


def test_run_build_includes_directory_contents_double_star(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Including 'src/**' should copy recursive contents → dist/..."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src = tmp_path / "src"
    nested = src / "deep"
    nested.mkdir(parents=True)
    (nested / "c.txt").write_text("C")

    cfg = make_build_cfg(tmp_path, [make_include_resolved("src/**", tmp_path)])

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    mod_build.run_build(cfg)

    # --- verify ---
    dist = tmp_path / "dist"
    assert (dist / "deep" / "c.txt").exists()
    assert not (dist / "src" / "deep" / "c.txt").exists()


def test_run_build_includes_single_file(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Including a single file should copy it directly to out."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    file = tmp_path / "only.txt"
    file.write_text("one")

    cfg = make_build_cfg(tmp_path, [make_include_resolved(file, tmp_path)])

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    mod_build.run_build(cfg)

    # --- verify ---
    dist = tmp_path / "dist"
    assert (dist / "only.txt").exists()


def test_run_build_includes_nested_subdir_glob(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Including 'src/utils/**' should copy contents of utils only → dist/..."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src = tmp_path / "src" / "utils"
    src.mkdir(parents=True)
    (src / "deep.txt").write_text("deep")

    cfg = make_build_cfg(tmp_path, [make_include_resolved("src/utils/**", tmp_path)])

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    mod_build.run_build(cfg)

    # --- verify ---
    dist = tmp_path / "dist"
    assert (dist / "deep.txt").exists()
    assert not (dist / "src" / "utils" / "deep.txt").exists()


def test_run_build_includes_multiple_glob_patterns(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Including both 'src/*' and 'lib/**' should merge multiple roots cleanly."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src = tmp_path / "src"
    lib = tmp_path / "lib" / "core"
    src.mkdir()
    lib.mkdir(parents=True)
    (src / "file1.txt").write_text("A")
    (lib / "file2.txt").write_text("B")

    cfg = make_build_cfg(
        tmp_path,
        [
            make_include_resolved("src/*", tmp_path),
            make_include_resolved("lib/**", tmp_path),
        ],
    )

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    mod_build.run_build(cfg)

    # --- verify ---
    dist = tmp_path / "dist"
    assert (dist / "file1.txt").exists()
    assert (dist / "core" / "file2.txt").exists()


def test_run_build_includes_top_level_glob_only(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Including '*.txt' should copy all top-level files only → dist/..."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    subdir = tmp_path / "nested"
    subdir.mkdir()
    (subdir / "c.txt").write_text("c")

    cfg = make_build_cfg(tmp_path, [make_include_resolved("*.txt", tmp_path)])

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    mod_build.run_build(cfg)

    # --- verify ---
    dist = tmp_path / "dist"
    assert (dist / "a.txt").exists()
    assert (dist / "b.txt").exists()
    assert not (dist / "nested" / "c.txt").exists()


def test_run_build_skips_missing_matches(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Missing include pattern should not raise or create anything."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    cfg = make_build_cfg(tmp_path, [make_include_resolved("doesnotexist/**", tmp_path)])

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "debug")
    mod_build.run_build(cfg)

    # --- verify ---
    assert not any((tmp_path / "dist").iterdir())


def test_run_build_respects_dest_override(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """IncludeResolved with explicit dest should place inside that subfolder."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src = tmp_path / "source"
    src.mkdir()
    (src / "f.txt").write_text("Z")

    cfg = make_build_cfg(
        tmp_path, [make_include_resolved("source", tmp_path, dest="renamed")]
    )

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    mod_build.run_build(cfg)

    # --- verify ---
    dist = tmp_path / "dist"
    assert (dist / "renamed" / "f.txt").exists()
    assert not (dist / "source" / "f.txt").exists()


def test_run_build_dry_run_does_not_write(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Dry-run mode should not create dist folder or copy files."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "file.txt").write_text("x")

    cfg = make_build_cfg(
        tmp_path, [make_include_resolved("src", tmp_path)], dry_run=True
    )

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "debug")
    mod_build.run_build(cfg)

    # --- verify ---
    dist = tmp_path / "dist"
    assert not (dist / "src" / "file.txt").exists()


def test_run_build_dry_run_does_not_delete_existing_out(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Existing out_dir should not be deleted or modified during dry-run builds."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "new.txt").write_text("new")

    out_dir = tmp_path / "dist"
    out_dir.mkdir()
    (out_dir / "old.txt").write_text("old")

    # Build config: include src/**, dry-run enabled
    cfg = make_build_cfg(
        tmp_path, [make_include_resolved("src/**", tmp_path)], dry_run=True
    )

    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "debug")

    # --- execute ---
    mod_build.run_build(cfg)

    # --- verify ---
    # The existing out_dir and its files should remain intact
    assert (out_dir / "old.txt").exists(), "dry-run should not remove existing files"
    # No new files should appear, since dry-run prevents copying
    assert not (out_dir / "src").exists()
    assert not (out_dir / "new.txt").exists()


def test_run_build_no_includes_warns(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
):
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    cfg = make_build_cfg(tmp_path, [])

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    mod_build.run_build(cfg)

    # --- verify ---
    assert (tmp_path / "dist").exists()
    assert not any((tmp_path / "dist").iterdir())


def test_run_build_preserves_pattern_and_shallow_behavior(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Each PathResolved should preserve its original pattern,
    and shallow globs ('*') should not recurse."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime
    from pocket_build.utils_types import PathResolved

    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "root.txt").write_text("R")
    sub = src / "nested"
    sub.mkdir()
    (sub / "deep.txt").write_text("D")

    # We'll include only top-level entries
    pattern = "src/*"
    cfg = make_build_cfg(tmp_path, [make_include_resolved(pattern, tmp_path)])

    # --- capture copy_item calls ---
    called: list[PathResolved] = []
    real_copy_item = mod_build.copy_item

    def fake_copy_item(
        src_entry: PathResolved,
        dest_entry: PathResolved,
        exclude_patterns: list[PathResolved],
        dry_run: bool,
    ) -> None:
        called.append(src_entry)
        return real_copy_item(src_entry, dest_entry, exclude_patterns, dry_run)

    # --- patch and execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "debug")
    monkeypatch.setattr(mod_build, "copy_item", fake_copy_item)
    mod_build.run_build(cfg)

    # --- verify ---
    assert called, "expected copy_item to be called at least once"

    # Every source entry should carry the original pattern
    for entry in called:
        assert "pattern" in entry, "pattern should be preserved in PathResolved"
        assert entry["pattern"] == pattern

    # Normal build logic: shallow pattern should not recurse into nested dirs
    dist = tmp_path / "dist"
    assert (dist / "root.txt").exists()
    assert not (dist / "nested" / "deep.txt").exists()


def test_run_build_includes_directory_contents_trailing_slash(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    """Including 'src/' should copy the contents only (rsync/git-style) → dist/..."""
    import pocket_build.build as mod_build
    import pocket_build.runtime as mod_runtime

    # --- setup ---
    src = tmp_path / "src"
    src.mkdir()
    (src / "inner.txt").write_text("data")

    cfg = make_build_cfg(tmp_path, [make_include_resolved("src/", tmp_path)])

    # --- execute ---
    monkeypatch.setitem(mod_runtime.current_runtime, "log_level", "info")
    mod_build.run_build(cfg)

    # --- verify ---
    dist = tmp_path / "dist"
    # contents copied directly, not nested under "src/"
    assert (dist / "inner.txt").exists()
    assert not (dist / "src" / "inner.txt").exists()
