# src/pocket_build/utils.py
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import (
    Any,
    cast,
)


def should_use_color() -> bool:
    """Return True if colored output should be enabled."""
    # Respect explicit overrides
    if "NO_COLOR" in os.environ:
        return False
    if os.getenv("FORCE_COLOR", "").lower() in {"1", "true", "yes"}:
        return True

    # Auto-detect: use color if output is a TTY
    return sys.stdout.isatty()


def load_jsonc(path: Path) -> dict[str, Any] | list[Any] | None:
    """Load JSONC (JSON with comments and trailing commas)."""
    text = path.read_text(encoding="utf-8")

    # Remove // and # comments (but not URLs like "http://")
    text = re.sub(r'(?<!["\'])\s*(?<!:)//.*|(?<!["\'])\s*#.*', "", text)

    # Remove block comments /* ... */
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    # Remove trailing commas before } or ]
    text = re.sub(r",(?=\s*[}\]])", "", text)

    # Trim whitespace
    text = text.strip()

    if not text:
        # Empty or only comments → interpret as "no config"
        return None

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSONC syntax in {path}: {e}") from e

    # Guard against scalar roots (invalid config structure)
    if not isinstance(data, (dict, list)):
        raise ValueError(f"Invalid config root type: {type(data).__name__}")

    # narrow type
    return cast(dict[str, Any] | list[Any], data)


def is_stitched() -> bool:
    """
    Return True if running from a stitched single-file build.
    """
    return bool(globals().get("__STITCHED__", False))
