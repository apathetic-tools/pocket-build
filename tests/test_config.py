# tests/test_config.py
"""Tests for package.config (module and single-file versions)."""

from __future__ import annotations

from typing import Any, Dict, List

from pocket_build.types import BuildConfig


def test_parse_builds_accepts_list_and_single_object() -> None:
    """Ensure parse_builds accepts both a list and a single build object."""
    import pocket_build.config as mod_config

    # --- setup ---
    data_list: Dict[str, Any] = {"builds": [{"include": ["src"], "out": "dist"}]}
    data_single: Dict[str, Any] = {"include": ["src"], "out": "dist"}

    # --- execute ---
    builds_from_list: List[BuildConfig] = mod_config.parse_builds(data_list)
    builds_from_single: List[BuildConfig] = mod_config.parse_builds(data_single)

    # --- verify ---
    assert isinstance(builds_from_list, list)
    assert isinstance(builds_from_single, list)
    assert builds_from_list[0].get("out") == "dist"
    assert builds_from_single[0].get("out") == "dist"


def test_parse_builds_handles_single_and_multiple() -> None:
    import pocket_build.config as mod_config

    # --- execute and verify ---
    assert mod_config.parse_builds({"builds": [{"include": []}]}) == [{"include": []}]
    assert mod_config.parse_builds({"include": []}) == [{"include": []}]
