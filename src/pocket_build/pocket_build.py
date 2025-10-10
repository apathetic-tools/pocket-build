#!/usr/bin/env python3
# src/pocket_build/pocket_build.py
"""
A tiny build system that fits in your pocket.
Because not everything needs a toolchain.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, Union, cast

from typing_extensions import NotRequired

# -----------------------------------------------------------
# Types
# -----------------------------------------------------------


class IncludeEntry(TypedDict, total=False):
    src: str
    dest: NotRequired[str]


class BuildConfig(TypedDict, total=False):
    include: List[Union[str, IncludeEntry]]
    exclude: List[str]
    out: str


class RootConfig(TypedDict, total=False):
    builds: List[BuildConfig]


# -----------------------------------------------------------
# Terminal Vars
# -----------------------------------------------------------

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

# -----------------------------------------------------------
# Config loaders
# -----------------------------------------------------------


# JSONC comments + trailing commas
def load_jsonc(path: Path) -> Dict[str, Any]:
    """Load JSONC (comments + trailing commas) using built-in json."""
    text = path.read_text(encoding="utf-8")

    # Remove // or # comments anywhere (but not in strings)
    text = re.sub(r"(?<!:)//.*|#.*", "", text)

    # Remove block comments (/* ... */)
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)

    # Remove trailing commas before closing braces/brackets
    text = re.sub(r",(\s*[}\]])", r"\1", text)

    return cast(Dict[str, Any], json.loads(text))


def parse_builds(raw_config: Dict[str, Any]) -> List[BuildConfig]:
    builds = raw_config.get("builds")
    if isinstance(builds, list):
        return cast(List[BuildConfig], builds)
    return [cast(BuildConfig, raw_config)]


# -----------------------------------------------------------
# Exclude matching
# -----------------------------------------------------------
def is_excluded(path: Path, exclude_patterns: List[str], root: Path) -> bool:
    rel = str(path.relative_to(root)).replace("\\", "/")
    return any(fnmatch(rel, pattern) for pattern in exclude_patterns)


# -----------------------------------------------------------
# Copy helpers
# -----------------------------------------------------------
def copy_file(src: Path, dest: Path, root: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print(f"📄 {src.relative_to(root)} → {dest.relative_to(root)}")


def copy_directory(
    src: Path, dest: Path, exclude_patterns: List[str], root: Path
) -> None:
    """Copy a directory recursively, skipping excluded files."""
    for item in src.rglob("*"):
        if is_excluded(item, exclude_patterns, root):
            print(f"🚫 Skipped: {item.relative_to(root)}")
            continue
        target = dest / item.relative_to(src)
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            print(f"{GREEN}📄{RESET} {item.relative_to(root)}")


def copy_item(src: Path, dest: Path, exclude_patterns: List[str], root: Path) -> None:
    if is_excluded(src, exclude_patterns, root):
        print(f"🚫 Skipped (excluded): {src.relative_to(root)}")
        return
    if src.is_dir():
        copy_directory(src, dest, exclude_patterns, root)
    else:
        copy_file(src, dest, root)


# -----------------------------------------------------------
# Build execution
# -----------------------------------------------------------
def run_build(
    build_cfg: BuildConfig, config_dir: Path, out_override: Optional[str]
) -> None:
    includes = build_cfg.get("include", [])
    excludes = build_cfg.get("exclude", [])
    out_dir: Path = config_dir / (out_override or build_cfg.get("out", "dist"))

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for entry in includes:
        entry_dict: IncludeEntry = {"src": entry} if isinstance(entry, str) else entry
        src_pattern = entry_dict.get("src")
        assert src_pattern is not None, f"Missing required 'src' in entry: {entry_dict}"

        dest_name: Optional[str] = entry_dict.get("dest")
        matches = (
            list(config_dir.rglob(src_pattern))
            if "**" in src_pattern
            else list(config_dir.glob(src_pattern))
        )
        if not matches:
            print(f"{YELLOW}⚠️  No matches for {src_pattern}{RESET}")
            continue

        for src in matches:
            if not src.exists():
                print(f"{YELLOW}⚠️  Missing: {src}{RESET}")
                continue

            dest: Path = out_dir / (dest_name or src.name)
            copy_item(src, dest, excludes, config_dir)

    print(f"✅ Build completed → {out_dir}\n")


# -----------------------------------------------------------
# Entry point
# -----------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", help="Override output directory")
    args = parser.parse_args(argv)

    cwd = Path.cwd().resolve()
    config_path: Optional[Path] = None

    if sys.version_info < (3, 10):
        sys.exit("❌ pocket-build requires Python 3.10 or newer.")

    # Prefer .pocket-build.json, fallback to .site-repo.json
    for candidate in [".pocket-build.json"]:
        cwd_candidate = cwd / candidate
        if cwd_candidate.exists():
            config_path = cwd_candidate
            break

    if not config_path:
        print(f"{YELLOW}⚠️  No build config found (.pocket-build.json).{RESET}")
        return 1

    config_dir = config_path.parent.resolve()
    print(f"🔧 Using config: {config_path.name}")
    print(f"📁 Config base: {config_dir}")
    print(f"📂 Invoked from: {cwd}\n")

    raw_config: Dict[str, Any] = load_jsonc(config_path)
    builds = parse_builds(raw_config)
    print(f"🔧 Running {len(builds)} build(s)\n")

    for i, build_cfg in enumerate(builds, 1):
        print(f"▶️  Build {i}/{len(builds)}")
        run_build(build_cfg, config_dir, args.out)

    print("🎉 All builds complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
