# src/pocket_build/config.py
from typing import Any, Dict, List, cast

from .types import BuildConfig


def parse_builds(raw_config: Dict[str, Any]) -> List[BuildConfig]:
    builds = raw_config.get("builds")
    if isinstance(builds, list):
        return cast(List[BuildConfig], builds)
    return [cast(BuildConfig, raw_config)]
