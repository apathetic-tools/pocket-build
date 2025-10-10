# tests/test_basic.py

from pocket_build import pocket_build


def test_load_jsonc_basic(tmp_path):
    """Sanity check: JSONC loader parses simple config."""
    f = tmp_path / ".pocket-build.json"
    f.write_text(
        """
        // Commented line
        { "builds": [ { "include": ["src"], "out": "dist" } ], }
        """
    )
    result = pocket_build.load_jsonc(f)
    assert "builds" in result
    assert result["builds"][0]["out"] == "dist"
