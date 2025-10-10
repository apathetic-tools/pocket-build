# tests/test_pocket_build.py
"""Unit tests for pocket_build.py."""

import json
from pathlib import Path

from pocket_build import pocket_build


# ------------------------------------------------------------
# 🔧 Config parsing
# ------------------------------------------------------------
def test_load_jsonc_strips_comments_and_trailing_commas(tmp_path: Path):
    cfg = tmp_path / "config.jsonc"
    cfg.write_text(
        """
        // a line comment
        # another comment
        {
          /* block comment */
          "foo": 123, // trailing comma next
        }
        """
    )
    result = pocket_build.load_jsonc(cfg)
    assert result == {"foo": 123}


def test_parse_builds_accepts_list_and_single_object():
    data_list = {"builds": [{"include": ["src"], "out": "dist"}]}
    data_single = {"include": ["src"], "out": "dist"}

    builds_from_list = pocket_build.parse_builds(data_list)
    builds_from_single = pocket_build.parse_builds(data_single)

    assert isinstance(builds_from_list, list)
    assert isinstance(builds_from_single, list)
    assert builds_from_list[0]["out"] == "dist"
    assert builds_from_single[0]["out"] == "dist"


# ------------------------------------------------------------
# 🚫 Exclusion matching
# ------------------------------------------------------------
def test_is_excluded_matches_patterns(tmp_path: Path):
    root = tmp_path
    file = root / "foo/bar.txt"
    file.parent.mkdir(parents=True)
    file.touch()
    assert pocket_build.is_excluded(file, ["foo/*"], root)
    assert not pocket_build.is_excluded(file, ["baz/*"], root)


# ------------------------------------------------------------
# 📄 Copy helpers
# ------------------------------------------------------------
def test_copy_file_creates_and_copies(tmp_path: Path, capsys):
    src = tmp_path / "a.txt"
    src.write_text("hi")
    dest = tmp_path / "out" / "a.txt"

    pocket_build.copy_file(src, dest, tmp_path)
    out = dest.read_text()
    assert out == "hi"
    captured = capsys.readouterr().out
    assert "📄" in captured


def test_copy_directory_respects_excludes(tmp_path: Path, capsys):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "keep.txt").write_text("ok")
    (src_dir / "skip.txt").write_text("no")

    dest = tmp_path / "out"
    pocket_build.copy_directory(src_dir, dest, ["**/skip.txt"], tmp_path)

    assert (dest / "keep.txt").exists()
    assert not (dest / "skip.txt").exists()

    captured = capsys.readouterr().out
    assert "🚫" in captured or "📄" in captured


def test_copy_item_handles_file_and_dir(tmp_path: Path):
    src_dir = tmp_path / "dir"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("data")

    dest = tmp_path / "out"
    pocket_build.copy_item(src_dir, dest, [], tmp_path)
    assert (dest / "a.txt").exists()


# ------------------------------------------------------------
# 🏗️ Build execution
# ------------------------------------------------------------
def test_run_build_creates_output_dir_and_copies(tmp_path: Path, capsys):
    # Arrange: create a small directory structure
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "foo.txt").write_text("foo")

    build_cfg = {
        "include": ["src"],
        "exclude": [],
        "out": "dist",
    }

    # Act
    pocket_build.run_build(build_cfg, tmp_path, None)

    # Assert
    dist = tmp_path / "dist"
    assert (dist / "src" / "foo.txt").exists()
    captured = capsys.readouterr().out
    assert "✅ Build completed" in captured


def test_run_build_handles_missing_match(tmp_path: Path, capsys):
    cfg = {"include": ["nonexistent"], "out": "dist"}
    pocket_build.run_build(cfg, tmp_path, None)
    captured = capsys.readouterr().out
    assert "⚠️" in captured


# ------------------------------------------------------------
# 🎛️ Main entry
# ------------------------------------------------------------
def test_main_no_config(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = pocket_build.main([])
    assert code == 1
    out = capsys.readouterr().out
    assert "No build config" in out


def test_main_with_config(tmp_path: Path, monkeypatch, capsys):
    config = tmp_path / ".pocket-build.json"
    config.write_text(json.dumps({"builds": [{"include": [], "out": "dist"}]}))
    monkeypatch.chdir(tmp_path)

    code = pocket_build.main([])
    out = capsys.readouterr().out
    assert code == 0
    assert "Build completed" in out
