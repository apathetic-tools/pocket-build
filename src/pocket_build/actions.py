# src/pocket_build/actions.py
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

from .build import run_build
from .config_types import BuildConfigResolved
from .constants import DEFAULT_WATCH_INTERVAL
from .logs import get_logger
from .meta import PROGRAM_DISPLAY, PROGRAM_SCRIPT, Metadata
from .utils_types import make_includeresolved, make_pathresolved


def _collect_included_files(resolved_builds: list[BuildConfigResolved]) -> list[Path]:
    """Flatten all include globs into a unique list of files."""
    logger = get_logger()
    logger.trace("_collect_included_files", __name__, id(_collect_included_files))
    files: set[Path] = set()

    for b in resolved_builds:
        for inc in b.get("include", []):
            # Merge root and path into a single glob pattern (as before)
            full_pattern = Path(inc["root"]) / inc["path"]

            # Use Path.glob/rglob equivalently to glob.glob(recursive=True)
            if "**" in str(full_pattern):
                matches = full_pattern.parent.rglob(full_pattern.name)
            else:
                matches = full_pattern.parent.glob(full_pattern.name)

            for p in matches:
                if p.is_file():
                    files.add(p.resolve())

    return sorted(files)


def watch_for_changes(
    rebuild_func: Callable[[], None],
    resolved_builds: list[BuildConfigResolved],
    interval: float = DEFAULT_WATCH_INTERVAL,
) -> None:
    """Poll file modification times and rebuild when changes are detected.

    Features:
    - Skips files inside each build’s output directory.
    - Re-expands include patterns every loop to detect newly created files.
    - Polling interval defaults to 1 second (tune 0.5–2.0 for balance).
    Stops on KeyboardInterrupt.
    """
    logger = get_logger()
    logger.trace("_watch_for_changes", __name__, id(watch_for_changes))
    logger.info(
        "👀 Watching for changes (interval=%.2fs)... Press Ctrl+C to stop.", interval
    )

    # discover at start
    included_files = _collect_included_files(resolved_builds)
    logger.trace(
        "_watch_for_changes", "initial files", [str(f) for f in included_files]
    )

    mtimes: dict[Path, float] = {
        f: f.stat().st_mtime for f in included_files if f.exists()
    }

    # Collect all output directories to ignore
    out_dirs: list[Path] = [
        (b["out"]["root"] / b["out"]["path"]).resolve() for b in resolved_builds
    ]

    rebuild_func()  # initial build

    try:
        while True:
            logger.trace("watch_for_changes", "sleep")
            time.sleep(interval)
            logger.trace("watch_for_changes", "loop")

            # 🔁 re-expand every tick so new/removed files are tracked
            included_files = _collect_included_files(resolved_builds)

            changed: list[Path] = []
            for f in included_files:
                logger.trace("watch_for_changes", "could be out dir?", f)
                # skip anything inside any build's output directory
                if any(f.is_relative_to(out_dir) for out_dir in out_dirs):
                    continue  # ignore output folder
                old_m = mtimes.get(f)
                logger.trace("watch_for_changes", "check", f, old_m)
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
                logger.info(
                    "\n🔁 Detected %d modified file(s). Rebuilding...", len(changed)
                )
                rebuild_func()
                # refresh timestamps after rebuild
                mtimes = {f: f.stat().st_mtime for f in included_files if f.exists()}
    except KeyboardInterrupt:
        logger.info("\n🛑 Watch stopped.")


def _get_metadata_from_header(script_path: Path) -> tuple[str, str]:
    """Extract version and commit from standalone script.

    Prefers in-file constants (__version__, __commit__) if present;
    falls back to commented header tags.
    """
    logger = get_logger()
    version = "unknown"
    commit = "unknown"

    logger.trace("reading commit from header:", script_path)

    with suppress(Exception):
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

    return version, commit


def get_metadata() -> Metadata:
    """Return (version, commit) tuple for this tool.

    - Standalone script → parse from header
    - Source installed → read pyproject.toml + git
    """
    script_path = Path(__file__)
    logger = get_logger()
    logger.trace("get_metadata ran from:", Path(__file__).resolve())

    # --- Heuristic: standalone script lives outside `src/` ---
    if globals().get("__STANDALONE__", False):
        version, commit = _get_metadata_from_header(script_path)
        logger.trace(f"got standalone version {version} with commit {commit}")
        return Metadata(version, commit)

    # --- Modular / source installed case ---

    # Source package case
    version = "unknown"
    commit = "unknown"

    # Try pyproject.toml for version
    root = Path(__file__).resolve().parents[2]
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        logger.trace(f"trying to read metadata from {pyproject}")
        text = pyproject.read_text()
        match = re.search(r'(?m)^\s*version\s*=\s*["\']([^"\']+)["\']', text)
        if match:
            version = match.group(1)

    # Try git for commit
    with suppress(Exception):
        logger.trace("trying to get commit from git")
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        commit = result.stdout.strip()

    logger.trace(f"got package version {version} with commit {commit}")
    return Metadata(version, commit)


def run_selftest() -> bool:
    """Run a lightweight functional test of the tool itself."""
    logger = get_logger()
    logger.info("🧪 Running self-test...")

    tmp_dir: Path | None = None
    try:
        tmp_dir = Path(tempfile.mkdtemp(prefix=f"{PROGRAM_SCRIPT}-selftest-"))
        src = tmp_dir / "src"
        out = tmp_dir / "out"
        src.mkdir()

        # Create a tiny file to copy
        file = src / "hello.txt"
        file.write_text(f"hello {PROGRAM_DISPLAY}!", encoding="utf-8")

        # --- Construct minimal BuildConfigResolved using helpers ---
        build_cfg: BuildConfigResolved = {
            "include": [make_includeresolved(str(src / "**"), tmp_dir, "code")],
            "exclude": [],
            "out": make_pathresolved(out, tmp_dir, "code"),
            "respect_gitignore": False,
            "log_level": "info",
            "dry_run": False,
            "__meta__": {"cli_root": tmp_dir, "config_root": tmp_dir},
        }

        logger.debug("[SELFTEST] using temp dir: %s", tmp_dir)

        # --- Run the build directly ---
        for dry_run in (True, False):
            build_cfg["dry_run"] = dry_run
            run_build(build_cfg)

        # Verify file copy
        copied = out / "hello.txt"
        if (
            copied.exists()
            and copied.read_text().strip() == f"hello {PROGRAM_DISPLAY}!"
        ):
            logger.info(
                "✅ Self-test passed — %s is working correctly.", PROGRAM_DISPLAY
            )
            return True

        logger.error("Self-test failed: output file not found or invalid.")
        return False

    except PermissionError:
        logger.error("Self-test failed: insufficient permissions.")  # noqa: TRY400
        return False
    except FileNotFoundError:
        logger.error("Self-test failed: missing file or directory.")  # noqa: TRY400
        return False
    except Exception:
        # Unexpected bug — show traceback and ask for a bug report
        logger.exception(
            "Unexpected self-test failure. "
            "Please report this issue with the following traceback:"
        )
        return False

    finally:
        if tmp_dir and tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
