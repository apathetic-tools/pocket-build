# src/pocket_build/config.py
from typing import Any, Dict, List, Union, cast

from .types import BuildConfig


def parse_builds(raw_config: Union[Dict[str, Any], List[Any]]) -> List[BuildConfig]:
    """
    Normalize any supported config shape into a list of BuildConfig objects.

    Accepted forms:
      - []                        → treated as single build with `include` = []
      - ["src/**", "assets/**"]   → treated as single build with those includes
      - {...}                     → treated as single build config
      - {"builds": [...]}         → treated as multi-build config
    """
    # Case 1: naked list (includes or empty)
    if isinstance(raw_config, list):
        return [cast(BuildConfig, {"include": raw_config})]

    # Case 2: dict with "builds" key (multi-build)
    builds = raw_config.get("builds")
    if isinstance(builds, list):
        return cast(List[BuildConfig], builds)

    # Defensive: if someone accidentally set builds=None, ignore it
    if builds is not None and not isinstance(builds, list):
        raise TypeError(f"Expected 'builds' to be a list, got {type(builds).__name__}")

    # Case 3: single build object
    return [cast(BuildConfig, raw_config)]
