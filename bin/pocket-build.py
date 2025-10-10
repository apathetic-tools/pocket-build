#!/usr/bin/env python3
# Pocket Build — a tiny build system that fits in your pocket.
# License: MIT-NOAI
# Full text: https://github.com/apathetic-tools/pocket-build/blob/main/LICENSE

# Version: 0.1.0
# Commit: 1894643
# Repo: https://github.com/apathetic-tools/pocket-build

"""
Pocket Build — a tiny build system that fits in your pocket.
This single-file version is auto-generated from modular sources.
Version: 0.1.0
Commit: 1894643
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


# === types.py ===
class IncludeEntry(TypedDict, total=False):
    src: str
    dest: NotRequired[str]


class BuildConfig(TypedDict, total=False):
    include: List[Union[str, IncludeEntry]]
    exclude: List[str]
    out: str


class RootConfig(TypedDict, total=False):
    builds: List[BuildConfig]


# === utils.py ===
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


# === config.py ===
def parse_builds(raw_config: Dict[str, Any]) -> List[BuildConfig]:
    builds = raw_config.get("builds")
    if isinstance(builds, list):
        return cast(List[BuildConfig], builds)
    return [cast(BuildConfig, raw_config)]


# === build.py ===
def copy_file(src: Path, dest: Path, root: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print(f"📄 {src.relative_to(root)} → {dest.relative_to(root)}")


def copy_directory(
    src: Path, dest: Path, exclude_patterns: List[str], root: Path
) -> None:
    """Recursively copy directory contents, skipping excluded files."""
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

        dest_name = entry_dict.get("dest")
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


# === cli.py ===
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="pocket-build")
    parser.add_argument("--out", help="Override output directory")
    args = parser.parse_args(argv)

    if sys.version_info < (3, 10):
        sys.exit("❌ pocket-build requires Python 3.10 or newer.")

    cwd = Path.cwd().resolve()
    config_path: Optional[Path] = None

    for candidate in [".pocket-build.json"]:
        p = cwd / candidate
        if p.exists():
            config_path = p
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
