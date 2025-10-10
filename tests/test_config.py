"""Tests for pocket_build.config"""

from typing import Any, Dict

from pocket_build.config import parse_builds


def test_parse_builds_accepts_list_and_single_object():
    data_list: Dict[str, Any] = {"builds": [{"include": ["src"], "out": "dist"}]}
    data_single: Dict[str, Any] = {"include": ["src"], "out": "dist"}

    builds_from_list = parse_builds(data_list)
    builds_from_single = parse_builds(data_single)

    assert isinstance(builds_from_list, list)
    assert isinstance(builds_from_single, list)
    assert builds_from_list[0].get("out") == "dist"
    assert builds_from_single[0].get("out") == "dist"
