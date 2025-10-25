# tests/test_config.py
"""Tests for package.config (module and single-file versions)."""

from typing import Any


def test_parse_builds_accepts_list_and_single_object() -> None:
    """Ensure parse_builds accepts both a list and a single build object."""
    import pocket_build.config as mod_config

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


def test_parse_builds_handles_single_and_multiple() -> None:
    import pocket_build.config as mod_config

    # --- execute and verify ---
    assert mod_config.parse_config({"builds": [{"include": []}]}) == {
        "builds": [{"include": []}]
    }
    assert mod_config.parse_config({"include": []}) == {"builds": [{"include": []}]}


def test_parse_config_returns_none_for_empty_values() -> None:
    import pocket_build.config as mod_config

    # --- execute and verify ---
    assert mod_config.parse_config(None) is None
    assert mod_config.parse_config({}) is None
    assert mod_config.parse_config([]) is None


def test_parse_config_list_of_strings_single_build() -> None:
    """List of strings should normalize into one build with include list."""
    import pocket_build.config as mod_config

    # --- execute ---
    result = mod_config.parse_config(["src/**", "lib/**"])

    # --- verify ---
    assert result == {"builds": [{"include": ["src/**", "lib/**"]}]}


def test_parse_config_dict_with_build_key() -> None:
    """Dict with a single 'build' key should lift it to builds=[...] form."""
    import pocket_build.config as mod_config

    # --- execute ---
    result = mod_config.parse_config({"build": {"include": ["src"], "out": "dist"}})

    # --- verify ---
    assert result == {"builds": [{"include": ["src"], "out": "dist"}]}


def test_parse_config_watch_interval_hoisting() -> None:
    import pocket_build.config as mod_config

    # --- execute ---
    result = mod_config.parse_config(
        [{"include": ["src"], "out": "dist", "watch_interval": 5.0}]
    )

    # --- verify ---
    assert result is not None
    assert result["watch_interval"] == 5.0
    assert "watch_interval" not in result["builds"][0]
