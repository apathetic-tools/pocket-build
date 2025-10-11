#!/usr/bin/env python3
# Pocket Build — a tiny build system that fits in your pocket.
# License: MIT-NOAI
# Full text: https://github.com/apathetic-tools/pocket-build/blob/main/LICENSE

# Version: 0.1.0
# Commit: f7e8c12
# Repo: https://github.com/apathetic-tools/pocket-build

"""
Pocket Build — a tiny build system that fits in your pocket.
This single-file version is auto-generated from modular sources.
Version: 0.1.0
Commit: f7e8c12
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import shutil
import subprocess
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

        if not src_pattern or src_pattern.strip() in {".", ""}:
            print(
                f"{YELLOW}⚠️  Skipping invalid include pattern: {src_pattern!r}{RESET}"
            )
            continue

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
# src/pocket_build/cli.py


def get_metadata_from_header(script_path: Path) -> tuple[str, str]:
    """Extract version and commit from bundled header if present."""
    version = "unknown"
    commit = "unknown"

    try:
        text = script_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("# Version:"):
                version = line.split(":", 1)[1].strip()
            elif line.startswith("# Commit:"):
                commit = line.split(":", 1)[1].strip()
    except Exception:
        pass

    return version, commit


def get_metadata() -> tuple[str, str]:
    """
    Return (version, commit) tuple for Pocket Build.
    - Bundled script → parse from header
    - Source package → read pyproject.toml + git
    """
    script_path = Path(__file__)
    # Bundled single-file case
    if script_path.name == "pocket-build.py":
        return get_metadata_from_header(script_path)

    # Source package case
    version = "unknown"
    commit = "unknown"

    # Try pyproject.toml for version
    root = Path(__file__).resolve().parent.parent.parent
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        match = re.search(
            r'(?m)^\s*version\s*=\s*["\']([^"\']+)["\']', pyproject.read_text()
        )
        if match:
            version = match.group(1)

    # Try git for commit
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        commit = result.stdout.strip()
    except Exception:
        pass

    return version, commit


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="pocket-build")
    parser.add_argument("--out", help="Override output directory")
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information and exit",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress non-error output",
    )
    args = parser.parse_args(argv)

    # --- Version flag ---
    if args.version:
        version, commit = get_metadata()
        print(f"Pocket Build {version} ({commit})")
        return 0

    # --- Python version check ---
    if sys.version_info < (3, 10):
        sys.exit("❌ pocket-build requires Python 3.10 or newer.")

    cwd = Path.cwd().resolve()
    config_path: Optional[Path] = None

    for candidate in [".pocket-build.json"]:
        p = cwd / candidate
        if p.exists():
            config_path = p
            break

    # --- Handle missing config ---
    if not config_path:
        print(f"{YELLOW}⚠️  No build config found (.pocket-build.json).{RESET}")
        return 1

    config_dir = config_path.parent.resolve()

    # --- Load configuration (shared) ---
    raw_config: Dict[str, Any] = load_jsonc(config_path)
    builds = parse_builds(raw_config)

    # --- Quiet mode: temporarily suppress stdout ---
    if args.quiet:
        buffer = io.StringIO()
        # everything printed inside this block is discarded
        with contextlib.redirect_stdout(buffer):
            for i, build_cfg in enumerate(builds, 1):
                run_build(build_cfg, config_dir, args.out)
        # still return 0 to indicate success
        return 0

    # --- Normal mode ---
    print(f"🔧 Using config: {config_path.name}")
    print(f"📁 Config base: {config_dir}")
    print(f"📂 Invoked from: {cwd}\n")
    print(f"🔧 Running {len(builds)} build(s)\n")

    for i, build_cfg in enumerate(builds, 1):
        print(f"▶️  Build {i}/{len(builds)}")
        run_build(build_cfg, config_dir, args.out)

    print("🎉 All builds complete.")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
