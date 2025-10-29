# tests/70-config-tests/test_find_config.py

from argparse import Namespace
from pathlib import Path

import pocket_build.config as mod_config


def test_find_config_raises_for_directory(tmp_path: Path) -> None:
    """Explicit --config path pointing to a directory should raise ValueError."""
    # --- setup ---
    args = Namespace(config=str(tmp_path))

    # --- execute and verify ---
    try:
        mod_config.find_config(args, tmp_path)
    except ValueError as e:
        assert "directory" in str(e)
    else:
        raise AssertionError("Expected ValueError for directory config path.")
