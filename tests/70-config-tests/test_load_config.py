# tests/70-config-tests/test_load_config.py

from pathlib import Path

from pytest import raises

import pocket_build.config as mod_config


def test_load_config_rejects_invalid_config_type(tmp_path: Path) -> None:
    """A .py config defining an invalid config type should raise TypeError."""
    # --- setup ---
    config_file = tmp_path / ".pocket_build.py"
    config_file.write_text("config = 123  # invalid type", encoding="utf-8")

    # --- execute and verify ---
    with raises(TypeError, match="must be a dict, list, or None"):
        mod_config.load_config(config_file)
