# src/pocket_build/utils.py
import json
import os
import re
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, cast

# Terminal colors (ANSI)
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


def load_jsonc(path: Path) -> Dict[str, Any]:
    """Load JSONC (JSON with comments and trailing commas)."""
    text = path.read_text(encoding="utf-8")

    # Strip // and # comments
    text = re.sub(r"(?<!:)//.*|#.*", "", text)
    # Strip block comments
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    # Remove trailing commas
    text = re.sub(r",(\s*[}\]])", r"\1", text)

    return cast(Dict[str, Any], json.loads(text))


def is_excluded(path: Path, exclude_patterns: List[str], root: Path) -> bool:
    rel = str(path.relative_to(root)).replace("\\", "/")
    return any(fnmatch(rel, pattern) for pattern in exclude_patterns)


def should_use_color() -> bool:
    """Return True if colored output should be enabled."""
    # Respect explicit overrides
    if "NO_COLOR" in os.environ:
        return False
    if os.environ.get("FORCE_COLOR", "").lower() in {"1", "true", "yes"}:
        return True

    # Auto-detect: use color if output is a TTY
    return sys.stdout.isatty()


def colorize(text: str, color: str, use_color: bool | None = None) -> str:
    # Initialize a "static" cache variable on first call
    if not hasattr(colorize, "_system_default"):
        setattr(colorize, "_system_default", should_use_color())  # cache result

    if use_color is not None:
        actual_use_color = use_color
    else:
        actual_use_color = getattr(colorize, "_system_default")

    if actual_use_color:
        return f"{color}{text}{RESET}"
    return text
