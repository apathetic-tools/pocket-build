# src/pocket_build/utils.py


import json
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from fnmatch import fnmatchcase
from functools import lru_cache
from io import StringIO
from pathlib import Path
from typing import (
    Any,
    cast,
)

from .config_types import PathResolved
from .logs import get_logger


# --- types --------------------------------------------------------------------


@dataclass
class CapturedOutput:
    """Captured stdout, stderr, and merged streams."""

    stdout: StringIO
    stderr: StringIO
    merged: StringIO

    def __str__(self) -> str:
        """Human-friendly representation (merged output)."""
        return self.merged.getvalue()

    def as_dict(self) -> dict[str, str]:
        """Return contents as plain strings for serialization."""
        return {
            "stdout": self.stdout.getvalue(),
            "stderr": self.stderr.getvalue(),
            "merged": self.merged.getvalue(),
        }


# --- utils --------------------------------------------------------------------


def get_sys_version_info() -> tuple[int, int, int] | tuple[int, int, int, str, int]:
    return sys.version_info


def load_jsonc(path: Path) -> dict[str, Any] | list[Any] | None:
    """Load JSONC (JSON with comments and trailing commas)."""
    if not path.exists():
        xmsg = f"JSONC file not found: {path}"
        raise FileNotFoundError(xmsg)

    if not path.is_file():
        xmsg = f"Expected a file: {path}"
        raise ValueError(xmsg)

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
        xmsg = (
            f"Invalid JSONC syntax in {path}:"
            f" {e.msg} (line {e.lineno}, column {e.colno})"
        )
        raise ValueError(xmsg) from e

    # Guard against scalar roots (invalid config structure)
    if not isinstance(data, (dict, list)):
        xmsg = f"Invalid JSONC root type: {type(data).__name__}"
        raise ValueError(xmsg)  # noqa: TRY004

    # narrow type
    return cast("dict[str, Any] | list[Any]", data)


def is_standalone() -> bool:
    """Return True if running from a standalone single-file build."""
    return bool(globals().get("__STANDALONE__", False))


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


@contextmanager
def capture_output() -> Iterator[CapturedOutput]:
    """Temporarily capture stdout and stderr.

    Any exception raised inside the block is re-raised with
    the captured output attached as `exc.captured_output`.

    Example:
    from pocket_build.utils import capture_output
    from pocket_build.cli import main

    with capture_output() as (out, err):
        exit_code = main(["--config", "my.cfg", "--dry-run"])

    result = {
        "exit_code": exit_code,
        "stdout": out.getvalue(),
        "stderr": err.getvalue(),
        "merged": merged.getvalue(),
    }

    """
    merged = StringIO()

    class TeeStream(StringIO):
        def write(self, s: str) -> int:
            merged.write(s)
            return super().write(s)

    buf_out, buf_err = TeeStream(), TeeStream()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = buf_out, buf_err

    cap = CapturedOutput(stdout=buf_out, stderr=buf_err, merged=merged)
    try:
        yield cap
    except Exception as e:
        # Attach captured output to the raised exception for API introspection
        e.captured_output = cap  # type: ignore[attr-defined]
        raise
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def detect_runtime_mode() -> str:
    if getattr(sys, "frozen", False):
        return "frozen"
    if "__main__" in sys.modules and getattr(
        sys.modules["__main__"],
        __file__,
        "",
    ).endswith(".pyz"):
        return "zipapp"
    if "__STANDALONE__" in globals():
        return "standalone"
    return "installed"


def is_excluded(path_entry: PathResolved, exclude_patterns: list[PathResolved]) -> bool:
    """High-level helper for internal use.
    Accepts PathResolved entries and delegates to the smart matcher.
    """
    path = path_entry["path"]
    root = path_entry["root"]
    # Patterns are always normalized to PathResolved["path"] under config_resolve
    patterns = [str(e["path"]) for e in exclude_patterns]
    return is_excluded_raw(path, patterns, root)


@lru_cache(maxsize=512)
def _compile_glob_recursive(pattern: str) -> re.Pattern[str]:
    """
    Compile a glob pattern to regex, backporting recursive '**' on Python < 3.11.
    This translator handles literals, ?, *, **, and [] classes without relying on
    slicing fnmatch.translate() output, avoiding unbalanced parentheses.
    Always case-sensitive.
    """

    def _escape_lit(ch: str) -> str:
        # Escape regex metacharacters
        if ch in ".^$+{}[]|()\\":
            return "\\" + ch
        return ch

    i = 0
    n = len(pattern)
    pieces: list[str] = []
    while i < n:
        ch = pattern[i]

        # Character class: copy through closing ']'
        if ch == "[":
            j = i + 1
            if j < n and pattern[j] in "!^":
                j += 1
            # allow leading ']' inside class as a literal
            if j < n and pattern[j] == "]":
                j += 1
            while j < n and pattern[j] != "]":
                j += 1
            if j < n and pattern[j] == "]":
                # whole class, keep as-is (regex already)
                pieces.append(pattern[i : j + 1])
                i = j + 1
            else:
                # unmatched '[', treat literally
                pieces.append("\\[")
                i += 1
            continue

        # Recursive glob
        if ch == "*" and i + 1 < n and pattern[i + 1] == "*":
            # Collapse a run of consecutive '*' to detect '**'
            k = i + 2
            while k < n and pattern[k] == "*":
                k += 1
            # Treat any run >= 2 as recursive
            pieces.append(".*")
            i = k
            continue

        # Single-segment glob
        if ch == "*":
            pieces.append("[^/]*")
            i += 1
            continue

        # Single character
        if ch == "?":
            pieces.append("[^/]")
            i += 1
            continue

        # Path separator or literal
        pieces.append(_escape_lit(ch))
        i += 1

    inner = "".join(pieces)
    return re.compile(f"(?s:{inner})\\Z")


def fnmatchcase_portable(path: str, pattern: str) -> bool:
    """
    Case-sensitive glob pattern matching with Python 3.10 '**' backport.

    Uses fnmatchcase (case-sensitive) as the base, with backported support
    for recursive '**' patterns on Python 3.10.

    Args:
        path: The path to match against the pattern
        pattern: The glob pattern to match

    Returns:
        True if the path matches the pattern, False otherwise.
    """
    if get_sys_version_info() >= (3, 11) or "**" not in pattern:
        return fnmatchcase(path, pattern)
    return bool(_compile_glob_recursive(pattern).match(path))


def is_excluded_raw(  # noqa: PLR0911
    path: Path | str,
    exclude_patterns: list[str],
    root: Path | str,
) -> bool:
    """Smart matcher for normalized inputs.

    - Treats 'path' as relative to 'root' unless already absolute.
    - If 'root' is a file, match directly.
    - Handles absolute or relative glob patterns.

    Note:
    The function does not require `root` to exist; if it does not,
    a debug message is logged and matching is purely path-based.
    """
    logger = get_logger()
    root = Path(root).resolve()
    path = Path(path)

    # the callee really should deal with this, otherwise we might spam
    if not Path(root).exists():
        logger.debug("Exclusion root does not exist: %s", root)

    # If the root itself is a file, treat that as a direct exclusion target.
    if root.is_file():
        # If the given path resolves exactly to that file, exclude it.
        full_path = path if path.is_absolute() else (root.parent / path)
        return full_path.resolve() == root.resolve()

    # If no exclude patterns, nothing else to exclude
    if not exclude_patterns:
        return False

    # Otherwise, treat as directory root.
    full_path = path if path.is_absolute() else (root / path)

    try:
        rel = str(full_path.relative_to(root)).replace("\\", "/")
    except ValueError:
        # Path lies outside the root; skip matching
        return False

    for pattern in exclude_patterns:
        pat = pattern.replace("\\", "/")

        # If pattern is absolute and under root, adjust to relative form
        if pat.startswith(str(root)):
            try:
                pat_rel = str(Path(pat).relative_to(root)).replace("\\", "/")
            except ValueError:
                pat_rel = pat  # not under root; treat as-is
            if fnmatchcase_portable(rel, pat_rel):
                return True

        # Otherwise treat pattern as relative glob
        if fnmatchcase_portable(rel, pat):
            return True

        # Optional directory-only semantics
        if pat.endswith("/") and rel.startswith(pat.rstrip("/") + "/"):
            return True

    return False


def has_glob_chars(s: str) -> bool:
    return any(c in s for c in "*?[]")


def normalize_path_string(raw: str) -> str:
    r"""Normalize a user-supplied path string for cross-platform use.

    Industry-standard (Git/Node/Python) rules:
      - Treat both '/' and '\\' as valid separators and normalize all to '/'.
      - Replace escaped spaces ('\\ ') with real spaces.
      - Collapse redundant slashes (preserve protocol prefixes like 'file://').
      - Never resolve '.' or '..' or touch the filesystem.
      - Never raise for syntax; normalization is always possible.

    This is the pragmatic cross-platform normalization strategy used by
    Git, Node.js, and Python build tools.
    This function is purely lexical — it normalizes syntax, not filesystem state.
    """
    logger = get_logger()
    if not raw:
        return ""

    path = raw.strip()

    # Handle escaped spaces (common shell copy-paste)
    if "\\ " in path:
        fixed = path.replace("\\ ", " ")
        logger.warning("Normalizing escaped spaces in path: %r → %s", path, fixed)
        path = fixed

    # Normalize all backslashes to forward slashes
    path = path.replace("\\", "/")

    # Collapse redundant slashes (keep protocol //)
    collapsed_slashes = re.sub(r"(?<!:)//+", "/", path)
    if collapsed_slashes != path:
        logger.trace("Collapsed redundant slashes: %r → %r", path, collapsed_slashes)
        path = collapsed_slashes

    return path


def get_glob_root(pattern: str) -> Path:
    """Return the non-glob portion of a path like 'src/**/*.txt'.

    Normalizes paths to cross-platform.
    """
    if not pattern:
        return Path()

    # Normalize backslashes to forward slashes
    normalized = normalize_path_string(pattern)

    parts: list[str] = []
    for part in Path(normalized).parts:
        if re.search(r"[*?\[\]]", part):
            break
        parts.append(part)
    return Path(*parts) if parts else Path()
