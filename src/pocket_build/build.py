# src/pocket_build/build.py


import contextlib
import re
import shutil
from pathlib import Path

from .config_types import BuildConfigResolved, IncludeResolved, PathResolved
from .constants import DEFAULT_DRY_RUN
from .logs import get_logger
from .utils import (
    has_glob_chars,
    is_excluded_raw,
)
from .utils_logs import TEST_TRACE
from .utils_types import cast_hint, make_pathresolved


# --------------------------------------------------------------------------- #
# internal helper
# --------------------------------------------------------------------------- #


def _compute_dest(  # noqa: PLR0911
    src: Path,
    root: Path,
    *,
    out_dir: Path,
    src_pattern: str,
    dest_name: Path | str | None,
) -> Path:
    """Compute destination path under out_dir for a matched source file/dir.

    Rules:
      - If dest_name is set → place inside out_dir/dest_name
      - Else if pattern has globs → strip non-glob prefix before computing relative path
      - Else → use src path relative to root
      - If root is not an ancestor of src → fall back to filename only
    """
    logger = get_logger()
    logger.trace(
        f"[DEST] src={src}, root={root}, out_dir={out_dir},"
        f" pattern={src_pattern!r}, dest_name={dest_name}",
    )

    if dest_name:
        result = out_dir / dest_name
        logger.trace(f"[DEST] dest_name override → {result}")
        return result

    # Treat trailing slashes as if they implied recursive includes
    if src_pattern.endswith("/"):
        src_pattern = src_pattern.rstrip("/")
        # pretend it's a glob-like pattern for relative computation
        try:
            rel = src.relative_to(root / src_pattern)
            result = out_dir / rel
            logger.trace(f"[DEST] trailing-slash include → rel={rel}, result={result}")

        except ValueError:
            logger.trace("[DEST] trailing-slash fallback (ValueError)")
            return out_dir / src.name

        else:
            return result

    try:
        if has_glob_chars(src_pattern):
            # For glob patterns, strip non-glob prefix
            prefix = _non_glob_prefix(src_pattern)
            rel = src.relative_to(root / prefix)
            result = out_dir / rel
            logger.trace(
                f"[DEST] glob include → prefix={prefix}, rel={rel}, result={result}",
            )
            return result
        # For literal includes (like "src" or "file.txt"), preserve full structure
        rel = src.relative_to(root)
        result = out_dir / rel
        logger.trace(f"[DEST] literal include → rel={rel}, result={result}")

    except ValueError:
        # Fallback when src isn't under root
        logger.trace(f"[DEST] fallback (src not under root) → using name={src.name}")
        return out_dir / src.name

    else:
        return result


def _non_glob_prefix(pattern: str) -> Path:
    """Return the non-glob leading portion of a pattern, as a Path."""
    parts: list[str] = []
    for part in Path(pattern).parts:
        if re.search(r"[*?\[\]]", part):
            break
        parts.append(part)
    return Path(*parts)


def copy_file(
    src: Path | str,
    dest: Path | str,
    *,
    src_root: Path | str,
    dry_run: bool,
) -> None:
    logger = get_logger()
    TEST_TRACE(
        "enter copy_file",
        f"id={id(logger)}",
        f"level={logger.level_name}",
        f"handlers={[type(h).__name__ for h in logger.handlers]}",
    )
    src = Path(src)
    dest = Path(dest)
    src_root = Path(src_root)

    try:
        rel_src = src.relative_to(src_root)
    except ValueError:
        rel_src = src
    try:
        rel_dest = dest.relative_to(src_root)
    except ValueError:
        rel_dest = dest
    logger.debug("📄 %s → %s", rel_src, rel_dest)

    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def copy_directory(
    src: Path | str,
    dest: Path | str,
    exclude_patterns: list[str],
    *,
    src_root: Path | str,
    dry_run: bool,
) -> None:
    """Recursively copy directory contents, skipping excluded files/dirs.

    Both src and dest can be Path or str. Exclusion matching is done
    relative to 'src_root', which should normally be the original include root.

    Exclude patterns ending with '/' are treated as directory-wide excludes.
    """
    logger = get_logger()
    TEST_TRACE(
        "enter copy_directory",
        f"id={id(logger)}",
        f"level={logger.level_name}",
        f"handlers={[type(h).__name__ for h in logger.handlers]}",
    )
    src = Path(src)
    src_root = Path(src_root).resolve()
    src = (src_root / src).resolve() if not src.is_absolute() else src.resolve()
    dest = Path(dest)  # relative, we resolve later

    # Normalize excludes: 'name/' → also match '**/name' and '**/name/**'
    normalized_excludes: list[str] = []
    for p in exclude_patterns:
        normalized_excludes.append(p)
        if p.endswith("/"):
            core = p.rstrip("/")
            normalized_excludes.append(core)  # match the dir itself
            normalized_excludes.append(f"**/{core}")  # dir at any depth
            normalized_excludes.append(f"**/{core}/**")  # everything under it

    # Ensure destination exists even if src is empty
    if not dry_run:
        dest.mkdir(parents=True, exist_ok=True)

    for item in src.iterdir():
        # Skip excluded directories and their contents early
        if is_excluded_raw(item, normalized_excludes, src_root):
            logger.debug("🚫  Skipped: %s", item.relative_to(src_root))
            continue

        target = dest / item.relative_to(src)
        if item.is_dir():
            logger.trace(f"📁 {item.relative_to(src_root)}")
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)
            copy_directory(
                item,
                target,
                normalized_excludes,
                src_root=src_root,
                dry_run=dry_run,
            )
        else:
            logger.debug("📄 %s", item.relative_to(src_root))
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)


def copy_item(
    src_entry: PathResolved,
    dest_entry: PathResolved,
    exclude_patterns: list[PathResolved],
    *,
    dry_run: bool,
) -> None:
    """Copy one file or directory entry, using built-in root info."""
    logger = get_logger()
    src = Path(src_entry["path"])
    src_root = Path(src_entry["root"]).resolve()
    src = (src_root / src).resolve() if not src.is_absolute() else src.resolve()
    dest = Path(dest_entry["path"])
    dest_root = (dest_entry["root"]).resolve()
    dest = (dest_root / dest).resolve() if not dest.is_absolute() else dest.resolve()
    origin = src_entry.get("origin", "?")

    # Combine output directory with the precomputed dest (if relative)
    dest = dest if dest.is_absolute() else (dest_root / dest)

    exclude_patterns_raw = [str(e["path"]) for e in exclude_patterns]
    pattern_str = str(src_entry.get("pattern", src_entry["path"]))

    logger.trace(
        f"[COPY_ITEM] {origin}: {src} → {dest} "
        f"(pattern={pattern_str!r}, excludes={len(exclude_patterns_raw)})",
    )

    # Exclusion check relative to its root
    if is_excluded_raw(src, exclude_patterns_raw, src_root):
        logger.debug("🚫  Skipped (excluded): %s", src.relative_to(src_root))
        return

    # Detect shallow single-star pattern
    is_shallow_star = (
        bool(re.search(r"(?<!\*)\*(?!\*)", pattern_str)) and "**" not in pattern_str
    )

    # Shallow match: pattern like "src/*"
    #  — copy only the directory itself, not its contents
    if src.is_dir() and is_shallow_star:
        logger.trace(
            f"📁 (shallow from pattern={pattern_str!r}) {src.relative_to(src_root)}",
        )
        if not dry_run:
            dest.mkdir(parents=True, exist_ok=True)
        return

    # Normal behavior
    if src.is_dir():
        copy_directory(
            src,
            dest,
            exclude_patterns_raw,
            src_root=src_root,
            dry_run=dry_run,
        )
    else:
        copy_file(
            src,
            dest,
            src_root=src_root,
            dry_run=dry_run,
        )


def _build_prepare_output_dir(out_dir: Path, *, dry_run: bool) -> None:
    """Create or clean the output directory as needed."""
    logger = get_logger()
    if out_dir.exists():
        if dry_run:
            logger.info("🧪 (dry-run) Would remove existing directory: %s", out_dir)
        else:
            shutil.rmtree(out_dir)
    if dry_run:
        logger.info("🧪 (dry-run) Would create: %s", out_dir)
    else:
        out_dir.mkdir(parents=True, exist_ok=True)


def _build_process_includes(
    includes: list[IncludeResolved],
    excludes: list[PathResolved],
    out_entry: PathResolved,
    *,
    out_dir: Path,
    dry_run: bool,
) -> None:
    logger = get_logger()
    for inc in includes:
        src_pattern = str(inc["path"])
        root = Path(inc["root"]).resolve()

        logger.trace(
            f"[INCLUDE] start pattern={src_pattern!r},"
            f" root={root}, origin={inc['origin']}",
        )

        if not src_pattern.strip():
            logger.debug("⚠️ Skipping empty include pattern")
            continue

        matches = _build_expand_include_pattern(src_pattern, root)
        if not matches:
            logger.debug("⚠️ No matches for %s", src_pattern)
            continue

        _build_copy_matches(
            matches,
            inc,
            excludes,
            out_entry,
            out_dir=out_dir,
            dry_run=dry_run,
        )


def _build_expand_include_pattern(src_pattern: str, root: Path) -> list[Path]:
    """Return all matching files for a given include pattern."""
    logger = get_logger()
    matches: list[Path] = []

    if src_pattern.endswith("/") and not has_glob_chars(src_pattern):
        logger.trace(
            f"[MATCH] Treating as trailing-slash directory include → {src_pattern!r}",
        )
        root_dir = root / src_pattern.rstrip("/")
        if root_dir.exists():
            matches = [p for p in root_dir.rglob("*") if p.is_file()]
        else:
            logger.trace(f"[MATCH] root_dir does not exist: {root_dir}")

    elif src_pattern.endswith("/**"):
        logger.trace(f"[MATCH] Treating as recursive include → {src_pattern!r}")
        root_dir = root / src_pattern.removesuffix("/**")
        if root_dir.exists():
            matches = [p for p in root_dir.rglob("*") if p.is_file()]
        else:
            logger.trace(f"[MATCH] root_dir does not exist: {root_dir}")

    elif has_glob_chars(src_pattern):
        logger.trace(f"[MATCH] Using glob() for pattern {src_pattern!r}")
        matches = list(root.glob(src_pattern))
        logger.trace(f"[MATCH] glob found {len(matches)} match(es)")

    else:
        logger.trace(f"[MATCH] Treating as literal include {root / src_pattern}")
        matches = [root / src_pattern]

    for i, m in enumerate(matches):
        logger.trace(f"[MATCH]   {i + 1:02d}. {m}")

    return matches


def _build_copy_matches(
    matches: list[Path],
    inc: IncludeResolved,
    excludes: list[PathResolved],
    out_entry: PathResolved,
    *,
    out_dir: Path,
    dry_run: bool,
) -> None:
    logger = get_logger()
    for src in matches:
        if not src.exists():
            logger.debug("⚠️ Missing: %s", src)
            continue

        logger.trace(f"[COPY] Preparing to copy {src}")

        dest_rel = _compute_dest(
            src,
            Path(inc["root"]).resolve(),
            out_dir=out_dir,
            src_pattern=str(inc["path"]),
            dest_name=inc.get("dest"),
        )
        logger.trace(f"[COPY] dest_rel={dest_rel}")

        src_resolved = make_pathresolved(
            src,
            inc["root"],
            inc["origin"],
            pattern=str(inc["path"]),
        )
        dest_resolved = make_pathresolved(dest_rel, out_dir, out_entry["origin"])

        copy_item(src_resolved, dest_resolved, excludes, dry_run=dry_run)


def run_build(
    build_cfg: BuildConfigResolved,
) -> None:
    """Execute a single build task using a fully resolved config."""
    logger = get_logger()
    dry_run = build_cfg.get("dry_run", DEFAULT_DRY_RUN)
    includes: list[IncludeResolved] = build_cfg["include"]
    excludes: list[PathResolved] = build_cfg["exclude"]
    out_entry: PathResolved = build_cfg["out"]
    out_dir = (out_entry["root"] / out_entry["path"]).resolve()

    logger.trace(f"[RUN_BUILD] out_dir={out_dir}, includes={len(includes)} patterns")

    # --- Clean and recreate output directory ---
    _build_prepare_output_dir(out_dir, dry_run=dry_run)

    # --- Process includes ---
    _build_process_includes(
        includes,
        excludes,
        out_entry,
        out_dir=out_dir,
        dry_run=dry_run,
    )
    logger.info("✅ Build completed → %s\n", out_dir)


def run_all_builds(
    resolved_builds: list[BuildConfigResolved],
    *,
    dry_run: bool,
) -> None:
    logger = get_logger()
    root_level = logger.level_name
    logger.trace(f"[run_all_builds] Resolved build: {resolved_builds}")

    for i, build_cfg in enumerate(resolved_builds, 1):
        build_log_level = build_cfg.get("log_level")

        build_cfg["dry_run"] = dry_run

        # apply build-specific log level temporarily
        needs_override = build_log_level and build_log_level != root_level
        context = (
            logger.use_level(cast_hint(str, build_log_level))
            if needs_override
            else contextlib.nullcontext()
        )

        with context:
            if needs_override:
                logger.debug("Overriding log level → %s", build_log_level)

            logger.info("▶️  Build %d/%d", i, len(resolved_builds))
            run_build(build_cfg)

    logger.info("🎉 All builds complete.")
