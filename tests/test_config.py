# tests/test_config.py
"""Tests for pocket_build.config (module and single-file versions)."""

from __future__ import annotations

from typing import Any, Dict, List

from conftest import PocketBuildLike

from pocket_build.types import BuildConfig


def test_parse_builds_accepts_list_and_single_object(
    pocket_build_env: PocketBuildLike,
) -> None:
    """Ensure parse_builds accepts both a list and a single build object."""
    data_list: Dict[str, Any] = {"builds": [{"include": ["src"], "out": "dist"}]}
    data_single: Dict[str, Any] = {"include": ["src"], "out": "dist"}

    builds_from_list: List[BuildConfig] = pocket_build_env.parse_builds(data_list)
    builds_from_single: List[BuildConfig] = pocket_build_env.parse_builds(data_single)

    assert isinstance(builds_from_list, list)
    assert isinstance(builds_from_single, list)
    assert builds_from_list[0].get("out") == "dist"
    assert builds_from_single[0].get("out") == "dist"
