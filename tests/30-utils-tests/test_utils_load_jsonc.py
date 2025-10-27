# tests/test_load_jsonc.py
"""Tests for package.utils (module and single-file versions)."""

from pathlib import Path

import pytest

import pocket_build.utils as mod_utils_core


def test_load_jsonc_empty_file(tmp_path: Path) -> None:
    """Empty JSONC file should return {} or raise clean error."""
    # --- setup ---
    cfg = tmp_path / "empty.jsonc"
    cfg.write_text("")

    # --- execute ---
    result = mod_utils_core.load_jsonc(cfg)

    # --- verify ---
    assert result is None


def test_load_jsonc_only_comments(tmp_path: Path) -> None:
    """File with only comments should behave like empty."""
    # --- setup ---
    cfg = tmp_path / "comments.jsonc"
    cfg.write_text("// comment only\n/* another */")

    # --- execute ---
    result = mod_utils_core.load_jsonc(cfg)

    # --- verify ---
    assert result is None


def test_load_jsonc_trailing_comma_in_list(tmp_path: Path) -> None:
    """Trailing commas in top-level lists should be handled."""
    # --- setup ---
    cfg = tmp_path / "list.jsonc"
    cfg.write_text('[ "a", "b", ]')

    # --- execute ---
    result = mod_utils_core.load_jsonc(cfg)

    # --- verify ---
    assert result == ["a", "b"]


def test_load_jsonc_inline_block_comment(tmp_path: Path) -> None:
    """Inline block comments should be removed cleanly."""
    # --- setup ---
    cfg = tmp_path / "inline.jsonc"
    cfg.write_text('{"foo": 1, /* skip */ "bar": 2}')

    # --- execute ---
    result = mod_utils_core.load_jsonc(cfg)

    # --- verify ---
    assert result == {"foo": 1, "bar": 2}


def test_load_jsonc_comment_in_array(tmp_path: Path) -> None:
    """Line comments in arrays should be stripped."""
    # --- setup ---
    cfg = tmp_path / "array.jsonc"
    cfg.write_text("[1, 2, // hi\n 3]")

    # --- execute ---
    result = mod_utils_core.load_jsonc(cfg)

    # --- verify ---
    assert result == [1, 2, 3]


@pytest.mark.parametrize("ext", ["json", "jsonc"])
def test_load_jsonc_strips_comments_and_trailing_commas(
    tmp_path: Path,
    ext: str,
) -> None:
    """Ensure both JSONC loader removes
    comments and trailing commas in JSON and JSONC files."""
    # --- setup ---
    cfg = tmp_path / f"config.{ext}"
    cfg.write_text(
        """
        // comment
        {
          "foo": 1,
          "bar": [2, 3,],  // trailing comma
          /* block comment */
          "nested": { "x": 10, },
        }
        """
    )

    # --- execute ---
    result = mod_utils_core.load_jsonc(cfg)

    # --- verify ---
    assert result == {
        "foo": 1,
        "bar": [2, 3],
        "nested": {"x": 10},
    }


def test_load_jsonc_preserves_urls(tmp_path: Path) -> None:
    """Ensure JSONC loader does not strip // inside string literals (e.g. URLs)."""
    # --- setup ---
    cfg = tmp_path / "config.jsonc"
    cfg.write_text(
        """
        {
          "url": "https://example.com/resource",
          "nested": {
            "comment_like": "http://localhost:8080/api"
          }
        }
        """
    )

    # --- execute ---
    result = mod_utils_core.load_jsonc(cfg)

    # --- verify ---
    assert result == {
        "url": "https://example.com/resource",
        "nested": {"comment_like": "http://localhost:8080/api"},
    }


def test_load_jsonc_invalid_json(tmp_path: Path) -> None:
    """Invalid JSONC should raise ValueError with file context."""
    # --- setup ---
    cfg = tmp_path / "bad.jsonc"
    cfg.write_text("{ unquoted_key: 1 }")

    # --- execute ---
    with pytest.raises(ValueError) as e:
        mod_utils_core.load_jsonc(cfg)

    # --- verify ---
    assert "bad.jsonc" in str(e.value)


def test_load_jsonc_rejects_scalar_root(tmp_path: Path):
    # --- setup ---
    cfg = tmp_path / "scalar.jsonc"
    cfg.write_text('"hello"')

    # --- execute and verify ---
    with pytest.raises(ValueError, match="Invalid JSONC root type"):
        mod_utils_core.load_jsonc(cfg)


def test_load_jsonc_multiline_block_comment(tmp_path: Path):
    # --- setup ---
    cfg = tmp_path / "multi.jsonc"
    cfg.write_text('{"a": 1, /* comment\nspanning\nlines */ "b": 2}')

    # --- execute ---
    result = mod_utils_core.load_jsonc(cfg)

    # --- verify ---
    assert result == {"a": 1, "b": 2}
