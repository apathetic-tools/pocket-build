# src/pocket_build/cli.py
import argparse
import contextlib
import io
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .build import run_build
from .config import parse_builds
from .utils import RESET, YELLOW, load_jsonc


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

    # --- Heuristic: bundled script lives outside `src/` ---
    if "src" not in str(script_path):
        return get_metadata_from_header(script_path)

    # --- Modular / source package case ---

    # Source package case
    version = "unknown"
    commit = "unknown"

    # Try pyproject.toml for version
    root = Path(__file__).resolve().parents[2]

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        import re

        text = pyproject.read_text()
        match = re.search(r'(?m)^\s*version\s*=\s*["\']([^"\']+)["\']', text)
        if match:
            version = match.group(1)

    # Try git for commit
    try:
        import subprocess

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
    parser.add_argument("-o", "--out", help="Override output directory")
    parser.add_argument(
        # -v already used by verbose
        "--version",
        action="store_true",
        help="Show version information and exit",
    )
    parser.add_argument(
        "-c",
        "--config",
        help="Path to custom build config file (default: .pocket-build.json in cwd)",
    )

    # Quiet and verbose cannot coexist
    noise_group = parser.add_mutually_exclusive_group()
    noise_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress non-error output",
    )
    noise_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed logs for each file operation",
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

    # --- Config path handling ---
    config_path: Optional[Path] = None
    if args.config:
        config_path = Path(args.config).expanduser().resolve()
        if not config_path.exists():
            print(f"{YELLOW}⚠️  Config file not found: {config_path}{RESET}")
            return 1
    else:
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
                run_build(
                    build_cfg, config_dir, args.out, verbose=args.verbose or False
                )
        # still return 0 to indicate success
        return 0

    # --- Normal / verbose mode ---
    print(f"🔧 Using config: {config_path.name}")
    print(f"📁 Config base: {config_dir}")
    print(f"📂 Invoked from: {cwd}\n")
    print(f"🔧 Running {len(builds)} build(s)\n")

    for i, build_cfg in enumerate(builds, 1):
        print(f"▶️  Build {i}/{len(builds)}")
        run_build(build_cfg, config_dir, args.out, verbose=args.verbose or False)

    print("🎉 All builds complete.")
    return 0
