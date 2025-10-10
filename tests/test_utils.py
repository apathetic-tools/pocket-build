"""Tests for pocket_build.utils"""

from pathlib import Path

from pocket_build.utils import is_excluded, load_jsonc


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
    result = load_jsonc(cfg)
    assert result == {"foo": 123}


def test_is_excluded_matches_patterns(tmp_path: Path):
    root = tmp_path
    file = root / "foo/bar.txt"
    file.parent.mkdir(parents=True)
    file.touch()
    assert is_excluded(file, ["foo/*"], root)
    assert not is_excluded(file, ["baz/*"], root)
