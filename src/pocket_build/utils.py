# src/pocket_build/utils.py


import json
import os
import re
import sys
from pathlib import Path
from typing import (
    Any,
    TextIO,
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
    if not path.exists():
        raise FileNotFoundError(f"JSONC file not found: {path}")

    if not path.is_file():
        raise ValueError(f"Expected a file: {path}")

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
        raise ValueError(
            f"Invalid JSONC syntax in {path}:"
            f" {e.msg} (line {e.lineno}, column {e.colno})"
        ) from e

    # Guard against scalar roots (invalid config structure)
    if not isinstance(data, (dict, list)):
        raise ValueError(f"Invalid JSONC root type: {type(data).__name__}")

    # narrow type
    return cast(dict[str, Any] | list[Any], data)


def is_stitched() -> bool:
    """
    Return True if running from a stitched single-file build.
    """
    return bool(globals().get("__STITCHED__", False))


def remove_path_in_error_message(inner_msg: str, path: Path) -> str:
    """Remove redundant file path mentions (and nearby filler)
    from error messages.

    Useful when wrapping a lower-level exception that already
    embeds its own file reference, so the higher-level message
    can use its own path without duplication.

     Example:
        "Invalid JSONC syntax in /abs/path/config.jsonc: Expecting value"
        → "Invalid JSONC syntax: Expecting value"
    """
    # Normalize both path and name for flexible matching
    full_path = str(path)
    filename = path.name

    # Common redundant phrases we might need to remove
    candidates = [
        f"in {full_path}",
        f"in '{full_path}'",
        f'in "{full_path}"',
        f"in {filename}",
        f"in '{filename}'",
        f'in "{filename}"',
        full_path,
        filename,
    ]

    clean_msg = inner_msg
    for pattern in candidates:
        clean_msg = clean_msg.replace(pattern, "").strip(": ").strip()

    # Normalize leftover spaces and colons
    clean_msg = re.sub(r"\s{2,}", " ", clean_msg)
    clean_msg = re.sub(r"\s*:\s*", ": ", clean_msg)

    return clean_msg


def plural(obj: Any) -> str:
    """Return 's' if obj represents a plural count.

    Accepts ints, floats, and any object implementing __len__().
    Returns '' for singular or zero.
    """
    count: int | float
    try:
        count = len(obj)
    except TypeError:
        # fallback for numbers or uncountable types
        count = obj if isinstance(obj, (int, float)) else 0
    return "s" if count != 1 else ""


def safe_log(msg: str) -> None:
    """Emergency logger that never fails."""
    stream = cast(TextIO, sys.__stderr__)
    try:
        print(msg, file=stream)
    except Exception:
        # As final guardrail — never crash during crash reporting
        try:
            stream.write(f"[INTERNAL] {msg}\n")
        except Exception:
            pass
