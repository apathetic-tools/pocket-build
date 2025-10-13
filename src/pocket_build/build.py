# src/pocket_build/build.py
import shutil
from pathlib import Path
from typing import List

from .types import BuildConfig, IncludeEntry, MetaBuildConfig
from .utils import (
    GREEN,
    YELLOW,
    colorize,
    debug_print,
    get_glob_root,
    has_glob_chars,
    is_excluded,
)


def copy_file(src: Path, dest: Path, root: Path, verbose: bool = False) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    if verbose:
        print(colorize(f"📄 {src.relative_to(root)} → {dest.relative_to(root)}", GREEN))


def copy_directory(
    src: Path,
    dest: Path,
    exclude_patterns: List[str],
    root: Path,
    verbose: bool = False,
) -> None:
    """Recursively copy directory contents, skipping excluded files."""
    for item in src.rglob("*"):
        if is_excluded(item, exclude_patterns, root):
            if verbose:
                print(f"🚫 Skipped: {item.relative_to(root)}")
            continue
        target = dest / item.relative_to(src)
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            if verbose:
                print(colorize(f"📄 {item.relative_to(root)}", GREEN))


def copy_item(
    src: Path,
    dest: Path,
    exclude_patterns: List[str],
    meta: MetaBuildConfig,
    verbose: bool = False,
) -> None:
    """Copy a file or directory, respecting excludes and meta base paths."""

    # Determine which base to use for exclusion checks
    if "exclude_base" not in meta:
        if "include_base" not in meta:
            debug_print("[WARN] Using fallback exclude_base — meta incomplete `.`")
        else:
            debug_print(
                "[WARN] Using fallback exclude_base — meta incomplete `include_base`"
            )
    exclude_base = Path(
        meta.get("exclude_base") or meta.get("include_base") or "."
    ).resolve()

    debug_print(
        f"[DEBUG COPY_ITEM] src={src} dest={dest} "
        f"exclude_base={exclude_base} patterns={exclude_patterns}"
    )

    if is_excluded(src, exclude_patterns, exclude_base):
        if verbose:
            print(f"🚫 Skipped (excluded): {src.relative_to(exclude_base)}")
        return
    if src.is_dir():
        copy_directory(src, dest, exclude_patterns, exclude_base, verbose)
    else:
        copy_file(src, dest, exclude_base, verbose)


def run_build(
    build_cfg: BuildConfig,
    verbose: bool = False,
) -> None:
    """Execute a single build task using a fully resolved config."""
    includes: list[str | IncludeEntry] = build_cfg.get("include", [])
    excludes: list[str] = build_cfg.get("exclude", [])
    out_dir = Path(build_cfg.get("out", "")).expanduser().resolve()

    meta = build_cfg.get("__meta__", {})
    include_base = Path(meta.get("include_base", ".")).resolve()

    debug_print(
        f"[DEBUG RUN_BUILD] include={includes}"
        f" out_dir={out_dir} include_base={include_base}"
    )

    # Clean and recreate output directory
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Iterate through include entries
    for entry in includes:
        entry_dict: IncludeEntry = {"src": entry} if isinstance(entry, str) else entry
        src_pattern = entry_dict.get("src")
        assert src_pattern is not None, f"Missing required 'src' in entry: {entry_dict}"

        if not src_pattern or src_pattern.strip() in {".", ""}:
            if verbose:
                print(
                    colorize(
                        f"⚠️  Skipping invalid include pattern: {src_pattern!r}", YELLOW
                    )
                )
            continue

        dest_name = entry_dict.get("dest")
        src_path = Path(src_pattern)
        glob_root = get_glob_root(src_pattern)

        # Find matches relative to that root
        if not has_glob_chars(src_pattern):
            # literal file or directory
            matches = [src_path.resolve()]
        else:
            glob_root = get_glob_root(src_pattern)
            matches = list(glob_root.rglob(src_path.relative_to(glob_root).as_posix()))

        debug_print(f"[DEBUG MATCHES] root={glob_root} matches={matches}")

        if not matches:
            if verbose:
                print(colorize(f"⚠️  No matches for {src_pattern}", YELLOW))
            continue

        for src in matches:
            if not src.exists():
                if verbose:
                    print(colorize(f"⚠️  Missing: {src}", YELLOW))
                continue

            # Compute destination
            if dest_name:
                dest = out_dir / dest_name
            else:
                if not has_glob_chars(src_pattern):
                    # preserve relative path from include_base
                    rel = src.relative_to(include_base)
                else:
                    rel = src.relative_to(glob_root)
                dest = out_dir / rel

            copy_item(src, dest, excludes, meta, verbose)

    print(f"✅ Build completed → {out_dir}\n")
