# tests/test_config.py
"""Tests for package.config (module and single-file versions)."""

from typing import Any, TextIO

from pytest import MonkeyPatch, raises

import pocket_build.config as mod_config
import pocket_build.utils_using_runtime as mod_utils_runtime
from tests.utils import patch_everywhere


def test_parse_config_builds_accepts_list_and_single_object() -> None:
    """Ensure parse_builds accepts both a list and a single build object."""

    # --- setup ---
    data_list: dict[str, Any] = {"builds": [{"include": ["src"], "out": "dist"}]}
    data_single: dict[str, Any] = {"include": ["src"], "out": "dist"}

    # --- execute ---
    parsed_list = mod_config.parse_config(data_list)
    parsed_single = mod_config.parse_config(data_single)

    # --- verify ---
    # Expected canonical structure
    assert parsed_list == {"builds": [{"include": ["src"], "out": "dist"}]}
    assert parsed_single == {
        "builds": [{"include": ["src"]}],
        "out": "dist",  # hoisted to root
    }


def test_parse_config_builds_handles_single_and_multiple() -> None:
    # --- execute and verify ---
    assert mod_config.parse_config({"builds": [{"include": []}]}) == {
        "builds": [{"include": []}]
    }
    assert mod_config.parse_config({"include": []}) == {"builds": [{"include": []}]}


def test_parse_config_returns_none_for_empty_values() -> None:
    # --- execute and verify ---
    assert mod_config.parse_config(None) is None
    assert mod_config.parse_config({}) is None
    assert mod_config.parse_config([]) is None


def test_parse_config_list_of_strings_single_build() -> None:
    """List of strings should normalize into one build with include list."""
    # --- execute ---
    result = mod_config.parse_config(["src/**", "lib/**"])

    # --- verify ---
    assert result == {"builds": [{"include": ["src/**", "lib/**"]}]}


def test_parse_config_dict_with_build_key() -> None:
    """Dict with a single 'build' key should lift it to builds=[...] form."""
    # --- execute ---
    result = mod_config.parse_config({"build": {"include": ["src"], "out": "dist"}})

    # --- verify ---
    assert result == {"builds": [{"include": ["src"], "out": "dist"}]}


def test_parse_config_watch_interval_hoisting() -> None:
    # --- execute ---
    result = mod_config.parse_config(
        [{"include": ["src"], "out": "dist", "watch_interval": 5.0}]
    )

    # --- verify ---
    assert result is not None
    assert result["watch_interval"] == 5.0
    assert "watch_interval" not in result["builds"][0]


def test_parse_config_coerces_build_list_to_builds(monkeypatch: MonkeyPatch) -> None:
    """Dict with 'build' as a list should coerce to 'builds' with a warning."""
    # --- setup ---
    data: dict[str, Any] = {"build": [{"include": ["src"]}, {"include": ["assets"]}]}
    logged: list[tuple[str, str]] = []

    # --- stubs ---
    def fake_log(
        level: str,
        *values: object,
        _sep: str = " ",
        _end: str = "\n",
        _file: TextIO | None = None,
        _flush: bool = False,
        _prefix: str | None = None,
    ) -> None:
        msg = _sep.join(str(v) for v in values)
        logged.append((level, msg))

    # --- patch and execute ---
    # Patch log() to capture warnings instead of printing
    patch_everywhere(monkeypatch, mod_utils_runtime, "log", fake_log)
    result = mod_config.parse_config(data)

    # --- verify ---
    assert result == {"builds": [{"include": ["src"]}, {"include": ["assets"]}]}
    assert any("Config key 'build' was a list" in msg for _, msg in logged)


def test_parse_config_coerces_builds_dict_to_build(monkeypatch: MonkeyPatch) -> None:
    """Dict with 'builds' as a dict should coerce to 'build' list with a warning."""
    # --- setup ---
    data: dict[str, Any] = {"builds": {"include": ["src"], "out": "dist"}}
    logged: list[tuple[str, str]] = []

    # --- stubs ---
    def fake_log(
        level: str,
        *values: object,
        sep: str = " ",
        _end: str = "\n",
        _file: TextIO | None = None,
        _flush: bool = False,
        _prefix: str | None = None,
    ) -> None:
        msg = sep.join(str(v) for v in values)
        logged.append((level, msg))

    # --- patch and execute ---
    patch_everywhere(monkeypatch, mod_utils_runtime, "log", fake_log)
    result = mod_config.parse_config(data)

    # --- verify ---
    assert result == {"builds": [{"include": ["src"], "out": "dist"}]}
    assert any("Config key 'builds' was a dict" in msg for _, msg in logged)


def test_parse_config_does_not_coerce_when_both_keys_present() -> None:
    """If both 'build' and 'builds' exist, parser should not guess."""
    # --- setup ---
    data: dict[str, Any] = {
        "build": [{"include": ["src"]}],
        "builds": [{"include": ["lib"]}],
    }

    # --- execute ---
    result = mod_config.parse_config(data)

    # --- verify ---
    # The parser should leave the structure unchanged for later validation
    assert result == data


def test_parse_config_accepts_explicit_builds_list_no_warning(
    monkeypatch: MonkeyPatch,
) -> None:
    """Explicit 'builds' list should pass through without coercion or warning."""
    # --- setup ---
    data: dict[str, Any] = {"builds": [{"include": ["src"]}, {"include": ["lib"]}]}
    logged: list[tuple[str, str]] = []

    # --- stubs ---
    def fake_log(
        level: str,
        *values: object,
        sep: str = " ",
        _end: str = "\n",
        _file: TextIO | None = None,
        _flush: bool = False,
        _prefix: str | None = None,
    ) -> None:
        msg = sep.join(str(v) for v in values)
        logged.append((level, msg))

    # --- patch and execute ---
    patch_everywhere(monkeypatch, mod_utils_runtime, "log", fake_log)
    result = mod_config.parse_config(data)

    # --- verify ---
    assert result == data
    assert not logged


def test_parse_config_rejects_invalid_root_type() -> None:
    """Non-dict or non-list root should raise a TypeError."""
    # --- execute and verify ---
    with raises(TypeError) as excinfo:
        mod_config.parse_config("not_a_dict_or_list")  # type: ignore[arg-type]

    msg = str(excinfo.value)
    assert "Invalid top-level value" in msg
    assert "expected object" in msg


def test_parse_config_build_list_does_not_warn_when_builds_also_present(
    monkeypatch: MonkeyPatch,
):
    """If both 'build' and 'builds' exist,
    even if 'build' is a list, do not warn or coerce."""
    # --- setup ---
    data: dict[str, Any] = {
        "build": [{"include": ["src"]}],
        "builds": [{"include": ["lib"]}],
    }
    logged: list[tuple[str, str]] = []

    # --- stubs ---
    def fake_log(
        level: str,
        *values: object,
        sep: str = " ",
        _end: str = "\n",
        _file: TextIO | None = None,
        _flush: bool = False,
        _prefix: str | None = None,
    ) -> None:
        msg = sep.join(str(v) for v in values)
        logged.append((level, msg))

    # --- patch and execute ---
    patch_everywhere(monkeypatch, mod_utils_runtime, "log", fake_log)
    result = mod_config.parse_config(data)

    # --- verify ---
    assert result == data
    assert not logged


def test_parse_config_build_dict_with_extra_root_fields() -> None:
    """Flat single build dict should hoist only shared keys, keep extras in build."""
    # --- setup ---
    data: dict[str, Any] = {
        "include": ["src"],
        "out": "dist",
        "watch_interval": 3.5,  # shared field, should be hoisted
        "mystery": True,  # unknown field, should remain inside build
    }

    # --- execute ---
    result = mod_config.parse_config(data)

    # --- verify ---
    assert result is not None
    assert "builds" in result
    assert result["watch_interval"] == 3.5
    build = result["builds"][0]
    assert "mystery" in build and build["mystery"] is True
    assert "watch_interval" not in build


def test_parse_config_empty_dict_inside_builds_list() -> None:
    """Ensure even an empty dict inside builds list is accepted as a valid build."""
    # --- setup ---
    data: dict[str, Any] = {"builds": [{}]}

    # --- execute ---
    result = mod_config.parse_config(data)

    # --- verify ---
    assert result == {"builds": [{}]}


def test_parse_config_builds_empty_list_is_returned_as_is() -> None:
    """An explicit empty builds list should not trigger coercion or defaults."""
    # --- setup ---
    data: dict[str, Any] = {"builds": []}

    # --- execute ---
    result = mod_config.parse_config(data)

    # --- verify ---
    # Parser shouldn't add fake builds or coerce structure
    assert result == {"builds": []}


def test_parse_config_list_of_dicts_hoists_first_watch_interval() -> None:
    """Multi-build shorthand list should hoist
    first watch_interval and clear it from builds."""
    # --- setup ---
    data: list[dict[str, Any]] = [
        {"include": ["src"], "watch_interval": 10.0},
        {"include": ["lib"]},
    ]

    # --- execute ---
    result = mod_config.parse_config(data)

    # --- verify ---
    assert result is not None
    assert result["watch_interval"] == 10.0
    assert all("watch_interval" not in b for b in result["builds"])


def test_parse_config_prefers_builds_when_both_are_dicts(
    monkeypatch: MonkeyPatch,
) -> None:
    """If both 'builds' and 'build' are dicts,
    parser should use 'builds' and not warn."""
    # --- setup ---
    data: dict[str, Any] = {
        "builds": {"include": ["src"]},
        "build": {"include": ["lib"]},
    }
    logged: list[tuple[str, str]] = []

    # --- stubs ---
    def fake_log(
        level: str,
        *values: object,
        sep: str = " ",
        _end: str = "\n",
        _file: TextIO | None = None,
        _flush: bool = False,
        _prefix: str | None = None,
    ) -> None:
        msg = sep.join(str(v) for v in values)
        logged.append((level, msg))

    # --- patch and execute ---
    patch_everywhere(monkeypatch, mod_utils_runtime, "log", fake_log)
    result = mod_config.parse_config(data)

    # --- verify ---
    assert result is not None
    # 'builds' dict is normalized to a single-item list
    assert result["builds"] == [{"include": ["src"]}]
    # 'build' remains present and unchanged
    assert "build" in result and result["build"] == {"include": ["lib"]}
    # warning was emitted for coercing 'builds' dict → list
    assert any("Config key 'builds' was a dict" in msg for _, msg in logged)


def test_parse_config_rejects_mixed_type_list() -> None:
    """Mixed-type list should raise TypeError (must be all strings or all objects)."""
    # --- setup ---
    # This list contains both a string and a dict — invalid mix.
    bad_config: list[object] = ["src/**", {"out": "dist"}]

    # --- execute & verify ---
    with raises(TypeError, match="Invalid mixed-type list"):
        mod_config.parse_config(bad_config)
