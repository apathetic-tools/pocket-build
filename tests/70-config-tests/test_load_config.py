# tests/70-config-tests/test_load_config.py

from pathlib import Path

import pocket_build.config as mod_config


def test_load_config_rejects_invalid_config_type(tmp_path: Path) -> None:
    """A .py config defining an invalid config type should raise TypeError."""

    config_file = tmp_path / ".pocket_build.py"
    config_file.write_text("config = 123  # invalid type", encoding="utf-8")

    try:
        mod_config.load_config(config_file)
    except TypeError as e:
        assert "must be a dict, list, or None" in str(e)
    else:
        raise AssertionError("Expected TypeError for invalid config type.")
