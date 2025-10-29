# tests/70-config-tests/test_load_config.py

from pathlib import Path

from pytest import raises

import pocket_build.config as mod_config
import pocket_build.meta as mod_meta


def test_load_config_accepts_valid_dict(tmp_path: Path) -> None:
    """Valid .py config defining a dict should return that dict."""
    # --- setup ---
    cfg = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.py"
    cfg.write_text("config = {'a': 1}", encoding="utf-8")

    # --- execute ---
    result = mod_config.load_config(cfg)

    # --- verify ---
    assert isinstance(result, dict)
    assert result == {"a": 1}


def test_load_config_accepts_valid_list(tmp_path: Path) -> None:
    """Valid .py config defining a list should return that list."""
    # --- setup ---
    cfg = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.py"
    cfg.write_text("builds = [{'out': 'dist'}]", encoding="utf-8")

    # --- execute ---
    result = mod_config.load_config(cfg)

    # --- verify ---
    assert isinstance(result, list)
    assert result == [{"out": "dist"}]


def test_load_config_returns_none_for_explicit_none(tmp_path: Path) -> None:
    """If a .py config sets config = None, it should return None."""
    # --- setup ---
    cfg = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.py"
    cfg.write_text("config = None", encoding="utf-8")

    # --- execute ---
    result = mod_config.load_config(cfg)

    # --- verify ---
    assert result is None


def test_load_config_raises_if_no_expected_vars(tmp_path: Path) -> None:
    """A .py config defining none of the expected vars should raise ValueError."""
    # --- setup ---
    cfg = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.py"
    cfg.write_text("x = 42", encoding="utf-8")

    # --- execute and verify ---
    with raises(ValueError, match="did not define"):
        mod_config.load_config(cfg)


def test_load_config_raises_runtimeerror_on_exec_failure(tmp_path: Path) -> None:
    """A .py config that crashes at import time should raise RuntimeError."""
    # --- setup ---
    cfg = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.py"
    cfg.write_text("raise Exception('boom')", encoding="utf-8")

    # --- execute and verify ---
    with raises(RuntimeError, match="Error while executing Python config"):
        mod_config.load_config(cfg)


def test_load_config_jsonc_success(tmp_path: Path) -> None:
    """Valid .jsonc config should load and return its parsed object."""
    # --- setup ---
    cfg = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.jsonc"
    cfg.write_text("{ 'a': 1 }".replace("'", '"'), encoding="utf-8")

    # --- execute ---
    result = mod_config.load_config(cfg)

    # --- verify ---
    assert result == {"a": 1}


def test_load_config_jsonc_invalid(tmp_path: Path) -> None:
    """Invalid JSONC syntax should raise a ValueError with filename context."""
    # --- setup ---
    cfg = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.jsonc"
    cfg.write_text("{ bad json }", encoding="utf-8")

    # --- execute and verify ---
    with raises(ValueError, match="Error while loading configuration file"):
        mod_config.load_config(cfg)


def test_load_config_cleans_error_message(tmp_path: Path) -> None:
    """Error message should not repeat the file path multiple times."""
    # --- setup ---
    cfg = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.json"
    cfg.write_text("{ bad json }", encoding="utf-8")

    # --- execute and verify ---
    with raises(ValueError) as exc_info:
        mod_config.load_config(cfg)

    msg = str(exc_info.value)
    assert msg.count(cfg.name) == 1


def test_load_config_rejects_invalid_config_type(tmp_path: Path) -> None:
    """A .py config defining an invalid config type should raise TypeError."""
    # --- setup ---
    config_file = tmp_path / f".{mod_meta.PROGRAM_SCRIPT}.py"
    config_file.write_text("config = 123  # invalid type", encoding="utf-8")

    # --- execute and verify ---
    with raises(TypeError, match="must be a dict, list, or None"):
        mod_config.load_config(config_file)
