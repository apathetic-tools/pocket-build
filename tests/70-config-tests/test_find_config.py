# tests/70-config-tests/test_find_config.py

from argparse import Namespace
from pathlib import Path

from pytest import raises

import pocket_build.config as mod_config


def test_find_config_raises_for_directory(tmp_path: Path) -> None:
    """Explicit --config path pointing to a directory should raise ValueError."""
    # --- setup ---
    args = Namespace(config=str(tmp_path))

    # --- execute and verify ---
    with raises(ValueError, match="directory"):
        mod_config.find_config(args, tmp_path)
