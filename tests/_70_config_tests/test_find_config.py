# tests/70-config-tests/test_find_config.py

from argparse import Namespace
from pathlib import Path

import pytest

import pocket_build.config as mod_config
import pocket_build.meta as mod_meta
import pocket_build.utils_using_runtime as mod_utils_runtime
from tests.utils import patch_everywhere


def test_find_config_raises_for_missing_file(tmp_path: Path) -> None:
    """Explicit --config path that doesn't exist should raise FileNotFoundError."""
    # --- setup ---
    args = Namespace(config=str(tmp_path / "nope.json"))

    # --- execute and verify ---
    with pytest.raises(FileNotFoundError, match="not found"):
        mod_config.find_config(args, tmp_path)


def test_find_config_returns_explicit_file(tmp_path: Path) -> None:
    """Should return the explicit file path when it exists."""
    # --- setup ---
    cfg = tmp_path / ".pocket_build.json"
    cfg.write_text("{}")
    args = Namespace(config=str(cfg))

    # --- execute ---
    result = mod_config.find_config(args, tmp_path)

    # --- verify ---
    assert result == cfg.resolve()


def test_find_config_logs_and_returns_none_when_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Should log and return None when no default config file exists."""
    # --- setup ---
    called: dict[str, bool] = {}
    args = Namespace(config=None)

    # --- stubs ---
    def fake_log(level: str, *_a: object, **_k: object) -> None:
        called["logged"] = True
        assert level == "error"

    # --- execute ---
    patch_everywhere(monkeypatch, mod_utils_runtime, "log", fake_log)
    result = mod_config.find_config(args, tmp_path)

    # --- verify ---
    assert result is None
    assert "logged" in called


def test_find_config_warns_for_multiple_candidates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """If multiple config files exist, should warn and use the first."""
    # --- setup ---
    prefix = mod_meta.PROGRAM_SCRIPT
    py = tmp_path / f".{prefix}.py"
    json = tmp_path / f".{prefix}json"
    jsonc = tmp_path / f".{prefix}.jsonc"
    for f in (py, json, jsonc):
        f.write_text("{}")

    messages: list[str] = []
    args = Namespace(config=None)

    # --- stubs ---
    def fake_log(level: str, *_args: object, **_kwargs: object) -> None:
        messages.append(level)

    # --- execute ---
    patch_everywhere(monkeypatch, mod_utils_runtime, "log", fake_log)
    result = mod_config.find_config(args, tmp_path)

    # --- verify ---
    assert result == py
    assert "warning" in messages


def test_find_config_raises_for_directory(tmp_path: Path) -> None:
    """Explicit --config path pointing to a directory should raise ValueError."""
    # --- setup ---
    args = Namespace(config=str(tmp_path))

    # --- execute and verify ---
    with pytest.raises(ValueError, match="directory"):
        mod_config.find_config(args, tmp_path)


def test_find_config_respects_missing_level(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """missing_level argument should control log level on missing config."""
    # --- setup ---
    levels: list[str] = []
    args = Namespace(config=None)

    # --- stubs ---
    def fake_log(level: str, *_a: object, **_k: object) -> None:
        levels.append(level)

    # --- execute ---
    patch_everywhere(monkeypatch, mod_utils_runtime, "log", fake_log)
    mod_config.find_config(args, tmp_path, missing_level="warning")

    # --- verify ---
    assert levels == ["warning"]
