# tests/utils/strip_common_prefix.py

from itertools import zip_longest
from pathlib import Path


def strip_common_prefix(path: str | Path, base: str | Path) -> str:
    """Return `path` relative to `base`'s common prefix.

    Example:
        strip_common_prefix(
            "/home/user/code/pocket-build/src/pocket_build/logs.py",
            "/home/user/code/pocket-build/tests/utils/patch_everywhere.py"
        )
        → "src/pocket_build/logs.py"
    """
    p = Path(path).resolve()
    b = Path(base).resolve()

    # Split both into parts and find the longest shared prefix
    common_len = 0
    for a, c in zip_longest(p.parts, b.parts):
        if a != c:
            break
        common_len += 1

    # Slice off the shared prefix
    remaining = Path(*p.parts[common_len:])
    return str(remaining) or "."
