# src/pocket_build/utils.py
import json
import os
import re
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, cast


def should_use_color() -> bool:
    """Return True if colored output should be enabled."""
    # Respect explicit overrides
    if "NO_COLOR" in os.environ:
        return False
    if os.getenv("FORCE_COLOR", "").lower() in {"1", "true", "yes"}:
        return True

    # Auto-detect: use color if output is a TTY
    return sys.stdout.isatty()


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


def has_glob_chars(s: str) -> bool:
    return any(c in s for c in "*?[]")


def get_glob_root(pattern: str) -> Path:
    """Return the non-glob portion of a path like 'src/**/*.txt'."""
    parts: List[str] = []  # ✅ explicitly typed
    for part in Path(pattern).parts:
        if re.search(r"[*?\[\]]", part):
            break
        parts.append(part)
    return Path(*parts) if parts else Path(".")
