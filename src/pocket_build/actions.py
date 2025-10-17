# src/pocket_build/actions.py
import argparse
import glob
import re
import subprocess
import time
from pathlib import Path
from typing import Callable

from .build import run_build
from .config import parse_builds, resolve_build_config
from .constants import DEFAULT_WATCH_INTERVAL
from .meta import PROGRAM_DISPLAY, PROGRAM_SCRIPT, Metadata
from .runtime import current_runtime
from .types import BuildConfig
from .utils_runtime import log


def _collect_included_files(resolved_builds: list[BuildConfig]) -> list[Path]:
    """Flatten all include globs into a unique list of files."""
    log("trace", "real_collect_included_files", __name__, id(_collect_included_files))
    files: set[Path] = set()
    for b in resolved_builds:
        for pattern in b.get("include", []):
            if isinstance(pattern, str):
                for match in glob.glob(pattern, recursive=True):
                    p = Path(match)
                    if p.is_file():
                        files.add(p.resolve())
    return sorted(files)


def watch_for_changes(
    rebuild_func: Callable[[], None],
    resolved_builds: list[BuildConfig],
    interval: float = DEFAULT_WATCH_INTERVAL,
) -> None:
    """Poll file modification times and rebuild when changes are detected.

    Features:
    - Skips files inside each build’s output directory.
    - Re-expands include patterns every loop to detect newly created files.
    - Polling interval defaults to 1 second (tune 0.5–2.0 for balance).
    Stops on KeyboardInterrupt.
    """

    log("trace", "real_watch_for_changes", __name__, id(watch_for_changes))
    log(
        "info",
        f"👀 Watching for changes (interval={interval:.2f}s)... Press Ctrl+C to stop.",
    )

    # discover at start
    included_files = _collect_included_files(resolved_builds)
    log("trace", "watch_for_changes", "initial files", [str(f) for f in included_files])

    mtimes: dict[Path, float] = {
        f: f.stat().st_mtime for f in included_files if f.exists()
    }

    # Collect all output directories to ignore
    out_dirs = [Path(b["out"]).resolve() for b in resolved_builds if "out" in b]

    rebuild_func()  # initial build

    try:
        while True:
            log("trace", "watch_for_changes", "sleep")
            time.sleep(interval)
            log("trace", "watch_for_changes", "loop")

            # 🔁 re-expand every tick so new/removed files are tracked
            included_files = _collect_included_files(resolved_builds)

            changed: list[Path] = []
            for f in included_files:
                log("trace", "watch_for_changes", "could be out dir?", f)
                # skip anything inside any build's output directory
                if any(f.is_relative_to(out_dir) for out_dir in out_dirs):
                    continue  # ignore output folder
                old_m = mtimes.get(f)
                log("trace", "watch_for_changes", "check", f, old_m)
                if not f.exists():
                    if old_m is not None:
                        changed.append(f)
                        mtimes.pop(f, None)
                    continue
                new_m = f.stat().st_mtime
                if old_m is None or new_m > old_m:
                    changed.append(f)
                    mtimes[f] = new_m

            if changed:
                print(f"\n🔁 Detected {len(changed)} modified file(s). Rebuilding...")
                rebuild_func()
                # refresh timestamps after rebuild
                mtimes = {f: f.stat().st_mtime for f in included_files if f.exists()}
    except KeyboardInterrupt:
        print("\n🛑 Watch stopped.")


def _get_metadata_from_header(script_path: Path) -> tuple[str, str]:
    """Extract version and commit from bundled script.

    Prefers in-file constants (__version__, __commit__) if present;
    falls back to commented header tags.
    """
    version = "unknown"
    commit = "unknown"

    try:
        text = script_path.read_text(encoding="utf-8")

        # --- Prefer Python constants if defined ---
        const_version = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text)
        const_commit = re.search(r"__commit__\s*=\s*['\"]([^'\"]+)['\"]", text)
        if const_version:
            version = const_version.group(1)
        if const_commit:
            commit = const_commit.group(1)

        # --- Fallback: header lines ---
        if version == "unknown" or commit == "unknown":
            for line in text.splitlines():
                if line.startswith("# Version:") and version == "unknown":
                    version = line.split(":", 1)[1].strip()
                elif line.startswith("# Commit:") and commit == "unknown":
                    commit = line.split(":", 1)[1].strip()

    except Exception:
        pass

    return version, commit


def get_metadata() -> Metadata:
    """
    Return (version, commit) tuple for this tool.
    - Bundled script → parse from header
    - Source package → read pyproject.toml + git
    """
    script_path = Path(__file__)

    # --- Heuristic: bundled script lives outside `src/` ---
    if "src" not in str(script_path):
        version, commit = _get_metadata_from_header(script_path)
        return Metadata(version, commit)

    # --- Modular / source package case ---

    # Source package case
    version = "unknown"
    commit = "unknown"

    # Try pyproject.toml for version
    root = Path(__file__).resolve().parents[2]

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text()
        match = re.search(r'(?m)^\s*version\s*=\s*["\']([^"\']+)["\']', text)
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

    return Metadata(version, commit)


def run_selftest() -> bool:
    """Run a lightweight functional test of the tool itself."""
    import shutil
    import tempfile

    log("info", "🧪 Running self-test...")

    tmp_dir = Path(tempfile.mkdtemp(prefix=f"{PROGRAM_SCRIPT}-selftest-"))
    src = tmp_dir / "src"
    out = tmp_dir / "out"
    src.mkdir()

    # Create a tiny file to copy
    file = src / "hello.txt"
    file.write_text(f"hello {PROGRAM_DISPLAY}!", encoding="utf-8")

    # Minimal fake config for internal run
    config: dict[str, list[BuildConfig]] = {
        "builds": [
            {"include": [str(src / "**")], "out": str(out)},
        ]
    }

    try:
        log("debug", f"[SELFTEST] using temp dir: {tmp_dir}")
        builds = parse_builds(config)
        for b in builds:
            resolved = resolve_build_config(
                b,
                argparse.Namespace(
                    include=None,
                    exclude=None,
                    add_include=None,
                    add_exclude=None,
                    out=None,
                    dry_run=False,
                    respect_gitignore=None,
                    log_level=current_runtime.get("log_level", "info"),
                ),
                config_dir=tmp_dir,
                cwd=tmp_dir,
                root_cfg={"respect_gitignore": False},
            )
            run_build(resolved)

        # Verify file copy
        copied = out / "hello.txt"
        if (
            copied.exists()
            and copied.read_text().strip() == f"hello {PROGRAM_DISPLAY}!"
        ):
            log(
                "info", f"✅ Self-test passed — {PROGRAM_DISPLAY} is working correctly."
            )
            return True

        log("error", "Self-test failed: output file not found or invalid.")
        return False

    except Exception as e:
        log("error", f"Self-test failed: {e}")
        return False

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
