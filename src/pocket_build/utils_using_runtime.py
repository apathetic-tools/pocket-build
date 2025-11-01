# src/pocket_build/utils_using_runtime.py


import os
import re
import sys
from contextlib import suppress
from fnmatch import fnmatch
from pathlib import Path
from typing import TextIO, cast

from .config_types import PathResolved
from .meta import PROGRAM_ENV
from .runtime import current_runtime
from .utils import safe_log


# Terminal colors (ANSI)
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

LEVEL_ORDER = [
    "trace",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    "silent",  # disables all logging
]

_LOG_PREFIXES: dict[str, str | None] = {
    "trace": "[TRACE] ",
    "debug": "[DEBUG] ",
    "info": None,
    "warning": "⚠️ ",
    "error": "❌ ",
    "critical": "💥 ",
}
_LOG_PREFIXES_COLOR: dict[str, str | None] = {
    "trace": YELLOW,
    "debug": GREEN,
    "info": None,
    "warning": None,
    "error": None,
    "critical": None,
}
_LOG_MSG_COLOR: dict[str, str | None] = {
    "trace": None,
    "debug": None,
    "info": None,
    "warning": None,
    "error": None,
    "critical": None,
}


def get_log_level() -> str:
    """Return the current log level, or 'error' if undefined or invalid."""
    level = cast("str | None", current_runtime.get("log_level"))  # type: ignore[redundant-cast]
    if level is None:
        safe_log("[LOGGER ERROR] ❌ Runtime does not specify log_level")
        return "error"

    if level not in LEVEL_ORDER:
        safe_log(f"[LOGGER ERROR] ❌ Unknown log level: {level!r}")
        return "error"

    return level


def is_bypass_capture() -> bool:
    """Return True if capture bypass env vars are active."""
    # this fixes runtime tests and is only microsecond slower than a file global
    return (
        os.getenv(f"{PROGRAM_ENV}_BYPASS_CAPTURE") == "1"
        or os.getenv("BYPASS_CAPTURE") == "1"
    )


def _should_log(level: str, current: str) -> bool:
    """Return True if a message at `level` should be emitted under
    the current log level `current`. Never logs if either level is 'silent'.
    """
    if level == "silent" or current == "silent":
        return False

    if level not in LEVEL_ORDER:
        safe_log(f"[LOGGER ERROR] ❌ Unknown log level: {level!r}")
        return False

    return LEVEL_ORDER.index(level) >= LEVEL_ORDER.index(current)


def _is_error_level(level: str) -> bool:
    """Return True if this log level represents a problem or warning."""
    return level in {"warning", "error", "critical"}


def _resolve_output_stream(level: str, file: TextIO | None) -> TextIO:
    """Decide whether to print to stdout or stderr, respecting BYPASS_CAPTURE."""
    if file is not None:
        return file

    if is_bypass_capture():
        return (
            getattr(sys, "__stderr__", sys.stderr)
            if _is_error_level(level)
            else getattr(sys, "__stdout__", sys.stdout)
        )
    return sys.stderr if _is_error_level(level) else sys.stdout


def _format_log_message(
    level: str,
    values: tuple[object, ...],
    sep: str,
    prefix: str | None,
) -> str:
    """Apply prefix and color formatting to the log message."""
    prefix_color = _LOG_PREFIXES_COLOR.get(level)
    msg_color = _LOG_MSG_COLOR.get(level)

    # Safely coerce prefix
    actual_prefix = prefix if prefix is not None else (_LOG_PREFIXES.get(level) or "")

    # Helper lambdas to treat None/"" as unset
    def is_set(value: str | None) -> bool:
        return bool(value and value.strip())

    # If no whole-line color, apply prefix color
    if not is_set(msg_color) and is_set(prefix_color):
        actual_prefix = colorize(actual_prefix, cast("str", prefix_color))

    message = sep.join([actual_prefix] + [str(v) for v in values])
    if is_set(msg_color):
        message = colorize(message, cast("str", msg_color))
    return message


def log(
    level: str,
    *values: object,
    sep: str = " ",
    end: str = "\n",
    file: TextIO | None = None,
    flush: bool = False,
    prefix: str | None = None,
) -> None:
    """Print a message respecting current log level and routing to
    stdout/stderr appropriately.

    - Prefix color and message color are mutually exclusive:
      if a message color is set, prefix color is skipped.
    - Safe for use in captured output; respects BYPASS_CAPTURE
    """
    if getattr(log, "_in_log", False):
        stream = cast("TextIO", sys.__stderr__)
        with suppress(Exception):
            stream.write("[LOGGER ERROR] ❌ Recursive log call suppressed\n")
        return
    log._in_log = True  # type: ignore[attr-defined] # noqa: SLF001

    try:
        if level not in LEVEL_ORDER:
            safe_log(f"[LOGGER ERROR] ❌ Unknown log level: {level!r}")
            return

        current_level = get_log_level()
        if not _should_log(level, current_level):
            return

        stream = _resolve_output_stream(level, file)
        message = _format_log_message(level, values, sep, prefix)
        print(message, end=end, file=stream, flush=flush)
    except Exception as e:  # noqa: BLE001
        safe_log(f"[LOGGER FAILURE] {e}")
    finally:
        log._in_log = False  # type: ignore[attr-defined] # noqa: SLF001


def colorize(text: str, color: str, *, use_color: bool | None = None) -> str:
    if use_color is None:
        use_color = current_runtime["use_color"]
    return f"{color}{text}{RESET}" if use_color else text


def is_excluded(path_entry: PathResolved, exclude_patterns: list[PathResolved]) -> bool:
    """High-level helper for internal use.
    Accepts PathResolved entries and delegates to the smart matcher.
    """
    path = path_entry["path"]
    root = path_entry["root"]
    # Patterns are always normalized to PathResolved["path"] under config_resolve
    patterns = [str(e["path"]) for e in exclude_patterns]
    return is_excluded_raw(path, patterns, root)


def is_excluded_raw(  # noqa: PLR0911
    path: Path | str,
    exclude_patterns: list[str],
    root: Path | str,
) -> bool:
    """Smart matcher for normalized inputs.

    - Treats 'path' as relative to 'root' unless already absolute.
    - If 'root' is a file, match directly.
    - Handles absolute or relative glob patterns.
    """
    root = Path(root).resolve()
    path = Path(path)

    # the callee really should deal with this, otherwise we might spam
    if not Path(root).exists():
        log("debug", f"Exclusion root does not exist: {root}")

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

        if "**" in pat and sys.version_info < (3, 11):
            log(
                "trace",
                f"'**' behaves non-recursively on Python {sys.version_info[:2]}",
            )

        # If pattern is absolute and under root, adjust to relative form
        if pat.startswith(str(root)):
            try:
                pat_rel = str(Path(pat).relative_to(root)).replace("\\", "/")
            except ValueError:
                pat_rel = pat  # not under root; treat as-is
            if fnmatch(rel, pat_rel):
                return True

        # Otherwise treat pattern as relative glob
        if fnmatch(rel, pat):
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
    if not raw:
        return ""

    path = raw.strip()

    # Handle escaped spaces (common shell copy-paste)
    if "\\ " in path:
        fixed = path.replace("\\ ", " ")
        log("warning", f"Normalizing escaped spaces in path: {path!r} → {fixed}")
        path = fixed

    # Normalize all backslashes to forward slashes
    path = path.replace("\\", "/")

    # Collapse redundant slashes (keep protocol //)
    collapsed_slashes = re.sub(r"(?<!:)//+", "/", path)
    if collapsed_slashes != path:
        log("trace", f"Collapsed redundant slashes: {path!r} → {collapsed_slashes!r}")
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
