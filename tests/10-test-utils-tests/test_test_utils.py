# tests/test-utils-tests/test_test_utils.py

from pathlib import Path

from tests.utils import make_build_cfg, make_include_resolved


def test_make_build_cfg_preserves_trailing_slash(tmp_path: Path):
    # --- setup and execute ---
    inc = make_include_resolved("src/", tmp_path)
    cfg = make_build_cfg(tmp_path, [inc])
    path_val = cfg["include"][0]["path"]

    # --- verify ---
    assert isinstance(path_val, str)
    assert path_val.endswith("/"), f"expected 'src/', got {path_val!r}"
