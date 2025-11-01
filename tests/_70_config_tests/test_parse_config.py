# tests/test_config.py
"""Tests for package.config (package and standalone versions)."""

from typing import Any

import pytest

import pocket_build.config as mod_config


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
        "builds": [{"include": []}],
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
    # --- setup ---
    interval = 5.0

    # --- execute ---
    result = mod_config.parse_config(
        [{"include": ["src"], "out": "dist", "watch_interval": interval}],
    )

    # --- verify ---
    assert result is not None
    assert result["watch_interval"] == interval
    assert "watch_interval" not in result["builds"][0]


def test_parse_config_coerces_build_list_to_builds(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dict with 'build' as a list should coerce to 'builds' with a warning."""
    # --- setup ---
    data: dict[str, Any] = {"build": [{"include": ["src"]}, {"include": ["assets"]}]}

    # --- patch and execute ---
    # Patch log() to capture warnings instead of printing
    result = mod_config.parse_config(data)

    # --- verify ---
    assert result == {"builds": [{"include": ["src"]}, {"include": ["assets"]}]}
    out = capsys.readouterr().err.lower()
    assert "Config key 'build' was a list".lower() in out


def test_parse_config_coerces_builds_dict_to_build(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dict with 'builds' as a dict should coerce to 'build' list with a warning."""
    # --- setup ---
    data: dict[str, Any] = {"builds": {"include": ["src"], "out": "dist"}}

    # --- patch and execute ---
    result = mod_config.parse_config(data)

    # --- verify ---
    assert result == {"builds": [{"include": ["src"], "out": "dist"}]}
    out = capsys.readouterr().err.lower()
    assert "Config key 'builds' was a dict".lower() in out


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
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Explicit 'builds' list should pass through without coercion or warning."""
    # --- setup ---
    data: dict[str, Any] = {"builds": [{"include": ["src"]}, {"include": ["lib"]}]}

    # --- patch and execute ---
    result = mod_config.parse_config(data)

    # --- verify ---
    assert result == data
    out = capsys.readouterr().err.lower()
    assert not out


def test_parse_config_rejects_invalid_root_type() -> None:
    """Non-dict or non-list root should raise a TypeError."""
    # --- execute and verify ---
    with pytest.raises(TypeError) as excinfo:
        mod_config.parse_config("not_a_dict_or_list")  # type: ignore[arg-type]

    msg = str(excinfo.value)
    assert "Invalid top-level value" in msg
    assert "expected object" in msg


def test_parse_config_build_list_does_not_warn_when_builds_also_present(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """If both 'build' and 'builds' exist,
    even if 'build' is a list, do not warn or coerce.
    """
    # --- setup ---
    data: dict[str, Any] = {
        "build": [{"include": ["src"]}],
        "builds": [{"include": ["lib"]}],
    }

    # --- patch and execute ---
    result = mod_config.parse_config(data)

    # --- verify ---
    assert result == data
    out = capsys.readouterr().err.lower()
    assert not out


def test_parse_config_build_dict_with_extra_root_fields() -> None:
    """Flat single build dict should hoist only shared keys, keep extras in build."""
    # --- setup ---
    interval = 3.5
    data: dict[str, Any] = {
        "include": ["src"],
        "out": "dist",
        "watch_interval": interval,  # shared field, should be hoisted
        "mystery": True,  # unknown field, should remain inside build
    }

    # --- execute ---
    result = mod_config.parse_config(data)

    # --- verify ---
    assert result is not None
    assert "builds" in result
    assert result["watch_interval"] == interval
    build = result["builds"][0]
    assert "mystery" in build
    assert build["mystery"] is True
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
    first watch_interval and clear it from builds.
    """
    # --- setup ---
    interval = 10.0
    data: list[dict[str, Any]] = [
        {"include": ["src"], "watch_interval": interval},
        {"include": ["lib"]},
    ]

    # --- execute ---
    result = mod_config.parse_config(data)

    # --- verify ---
    assert result is not None
    assert result["watch_interval"] == interval
    assert all("watch_interval" not in b for b in result["builds"])


def test_parse_config_prefers_builds_when_both_are_dicts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """If both 'builds' and 'build' are dicts,
    parser should use 'builds' and not warn.
    """
    # --- setup ---
    data: dict[str, Any] = {
        "builds": {"include": ["src"]},
        "build": {"include": ["lib"]},
    }

    # --- patch and execute ---
    result = mod_config.parse_config(data)

    # --- verify ---
    assert result is not None
    # 'builds' dict is normalized to a single-item list
    assert result["builds"] == [{"include": ["src"]}]
    # 'build' remains present and unchanged
    assert "build" in result
    assert result["build"] == {"include": ["lib"]}
    # warning was emitted for coercing 'builds' dict → list
    out = capsys.readouterr().err.lower()
    assert "Config key 'builds' was a dict".lower() in out


def test_parse_config_rejects_mixed_type_list() -> None:
    """Mixed-type list should raise TypeError (must be all strings or all objects)."""
    # --- setup ---
    # This list contains both a string and a dict — invalid mix.
    bad_config: list[object] = ["src/**", {"out": "dist"}]

    # --- execute & verify ---
    with pytest.raises(TypeError, match="Invalid mixed-type list"):
        mod_config.parse_config(bad_config)
