# src/pocket_build/build.py


import re
import shutil
from pathlib import Path

from .runtime import current_runtime
from .types import BuildConfig, IncludeResolved, PathResolved
from .utils_types import make_pathresolved
from .utils_using_runtime import (
    has_glob_chars,
    is_excluded_raw,
    log,
)

# --------------------------------------------------------------------------- #
# internal helper
# --------------------------------------------------------------------------- #


def _compute_dest(
    src: Path,
    base: Path,
    out_dir: Path,
    src_pattern: str,
    dest_name: Path | str | None,
) -> Path:
    """Compute destination path under out_dir for a matched source file/dir.

    Rules:
      - If dest_name is set → place inside out_dir/dest_name
      - Else if pattern has globs → strip non-glob prefix before computing relative path
      - Else → use src path relative to base
      - If base is not an ancestor of src → fall back to filename only
    """
    log(
        "trace",
        f"[DEST] src={src}, base={base}, out_dir={out_dir},"
        f" pattern={src_pattern!r}, dest_name={dest_name}",
    )

    if dest_name:
        result = out_dir / dest_name
        log("trace", f"[DEST] dest_name override → {result}")
        return result

    # Treat trailing slashes as if they implied recursive includes
    if src_pattern.endswith("/"):
        src_pattern = src_pattern.rstrip("/")
        # pretend it's a glob-like pattern for relative computation
        try:
            rel = src.relative_to(base / src_pattern)
            result = out_dir / rel
            log("trace", f"[DEST] trailing-slash include → rel={rel}, result={result}")
            return result
        except ValueError:
            log("trace", "[DEST] trailing-slash fallback (ValueError)")
            return out_dir / src.name

    try:
        if has_glob_chars(src_pattern):
            # For glob patterns, strip non-glob prefix
            prefix = _non_glob_prefix(src_pattern)
            rel = src.relative_to(base / prefix)
            result = out_dir / rel
            log(
                "trace",
                f"[DEST] glob include → prefix={prefix}, rel={rel}, result={result}",
            )
            return result
        else:
            # For literal includes (like "src" or "file.txt"), preserve full structure
            rel = src.relative_to(base)
            result = out_dir / rel
            log("trace", f"[DEST] literal include → rel={rel}, result={result}")
            return result
    except ValueError:
        # Fallback when src isn't under base
        log("trace", f"[DEST] fallback (src not under base) → using name={src.name}")
        return out_dir / src.name


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
    src_root: Path | str,
    dry_run: bool,
) -> None:
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
    log("debug", f"📄 {rel_src} → {rel_dest}")

    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def copy_directory(
    src: Path | str,
    dest: Path | str,
    exclude_patterns: list[str],
    src_root: Path | str,
    dry_run: bool,
) -> None:
    """Recursively copy directory contents, skipping excluded files/dirs.

    Both src and dest can be Path or str. Exclusion matching is done
    relative to 'src_root', which should normally be the original include base.

    Exclude patterns ending with '/' are treated as directory-wide excludes.
    """
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
            log("debug", f"🚫  Skipped: {item.relative_to(src_root)}")
            continue

        target = dest / item.relative_to(src)
        if item.is_dir():
            log("trace", f"📁 {item.relative_to(src_root)}")
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)
            copy_directory(item, target, normalized_excludes, src_root, dry_run)
        else:
            log("debug", f"📄 {item.relative_to(src_root)}")
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)


def copy_item(
    src_entry: PathResolved,
    dest_entry: PathResolved,
    exclude_patterns: list[PathResolved],
    dry_run: bool,
) -> None:
    """Copy one file or directory entry, using built-in base info."""

    src = Path(src_entry["path"])
    base_src = Path(src_entry["base"]).resolve()
    src = (base_src / src).resolve() if not src.is_absolute() else src.resolve()
    dest = Path(dest_entry["path"])
    base_dest = (dest_entry["base"]).resolve()
    dest = (base_dest / dest).resolve() if not dest.is_absolute() else dest.resolve()
    origin = src_entry.get("origin", "?")

    # Combine output directory with the precomputed dest (if relative)
    dest = dest if dest.is_absolute() else (base_dest / dest)

    exclude_patterns_raw = [str(e["path"]) for e in exclude_patterns]
    pattern_str = str(src_entry.get("pattern", src_entry["path"]))

    log(
        "trace",
        f"[COPY_ITEM] {origin}: {src} → {dest} "
        f"(pattern={pattern_str!r}, excludes={len(exclude_patterns_raw)})",
    )

    # Exclusion check relative to its base
    if is_excluded_raw(src, exclude_patterns_raw, base_src):
        log("debug", f"🚫  Skipped (excluded): {src.relative_to(base_src)}")
        return

    # Detect shallow single-star pattern
    is_shallow_star = (
        bool(re.search(r"(?<!\*)\*(?!\*)", pattern_str)) and "**" not in pattern_str
    )

    # Shallow match: pattern like "src/*"
    #  — copy only the directory itself, not its contents
    if src.is_dir() and is_shallow_star:
        log(
            "trace",
            f"📁 (shallow from pattern={pattern_str!r}) {src.relative_to(base_src)}",
        )
        if not dry_run:
            dest.mkdir(parents=True, exist_ok=True)
        return

    # Normal behavior
    if src.is_dir():
        copy_directory(src, dest, exclude_patterns_raw, base_src, dry_run)
    else:
        copy_file(src, dest, base_src, dry_run)


def run_build(
    build_cfg: BuildConfig,
) -> None:
    """Execute a single build task using a fully resolved config."""
    dry_run = build_cfg.get("dry_run", False)
    includes: list[IncludeResolved] = build_cfg["include"]
    excludes: list[PathResolved] = build_cfg["exclude"]
    out_entry = build_cfg["out"]
    out_dir = (out_entry["base"] / out_entry["path"]).resolve()

    log("trace", f"[RUN_BUILD] out_dir={out_dir}, includes={len(includes)} patterns")

    # --- Clean and recreate output directory ---
    if out_dir.exists():
        if dry_run:
            log("info", f"🧪 (dry-run) Would remove existing directory: {out_dir}")
        else:
            shutil.rmtree(out_dir)
    if dry_run:
        log("info", f"🧪 (dry-run) Would create: {out_dir}")
    else:
        out_dir.mkdir(parents=True, exist_ok=True)

    # --- Process includes ---
    for inc in includes:
        src_pattern = str(inc["path"])
        base = Path(inc["base"]).resolve()

        log(
            "trace",
            f"[INCLUDE] start pattern={src_pattern!r},"
            f" base={base}, origin={inc['origin']}",
        )

        if not src_pattern.strip():
            log("debug", "⚠️  Skipping empty include pattern")
            continue

        # --- Expand include patterns ---
        if src_pattern.endswith("/") and not has_glob_chars(src_pattern):
            # Interpret "src/" as "src/**" and use rglob directly inside
            log(
                "trace",
                f"[MATCH] Treating as trailing-slash directory include"
                f" → {src_pattern!r}",
            )
            root_dir = base / src_pattern.rstrip("/")
            if root_dir.exists():
                matches = [p for p in root_dir.rglob("*") if p.is_file()]
                log(
                    "trace", f"[MATCH] rglob found {len(matches)} file(s) in {root_dir}"
                )
            else:
                matches = []
                log("trace", f"[MATCH] root_dir does not exist: {root_dir}")
        elif src_pattern.endswith("/**"):
            # Direct recursive pattern
            log("trace", f"[MATCH] Treating as recursive include → {src_pattern!r}")
            root_dir = base / src_pattern.rstrip("/**")
            if root_dir.exists():
                matches = [p for p in root_dir.rglob("*") if p.is_file()]
                log(
                    "trace", f"[MATCH] rglob found {len(matches)} file(s) in {root_dir}"
                )
            else:
                matches = []
                log("trace", f"[MATCH] root_dir does not exist: {root_dir}")
        elif has_glob_chars(src_pattern):
            log("trace", f"[MATCH] Using glob() for pattern {src_pattern!r}")
            matches = list(base.glob(src_pattern))
            log("trace", f"[MATCH] glob found {len(matches)} match(es)")
        else:
            log("trace", f"[MATCH] Treating as literal include {base / src_pattern}")
            matches = [base / src_pattern]

        for i, m in enumerate(matches):
            log("trace", f"[MATCH]   {i + 1:02d}. {m}")

        if not matches:
            log("debug", f"⚠️  No matches for {src_pattern}")
            continue

        # --- Copy each matched path ---
        for src in matches:
            if not src.exists():
                log("debug", f"⚠️  Missing: {src}")
                continue

            log("trace", f"[COPY] Preparing to copy {src}")

            # Compute the destination path before handing off
            dest_rel = _compute_dest(src, base, out_dir, src_pattern, inc.get("dest"))
            log("trace", f"[COPY] dest_rel={dest_rel}")

            src_resolved = make_pathresolved(
                src,  # replace pattern with matched path
                inc["base"],
                inc["origin"],
                pattern=src_pattern,
            )
            log("trace", f"[COPY] src_resolved={src_resolved}")

            dest_resolved = make_pathresolved(dest_rel, out_dir, out_entry["origin"])
            log("trace", f"[COPY] dest_resolved={dest_resolved}")

            copy_item(src_resolved, dest_resolved, excludes, dry_run)

    log("info", f"✅ Build completed → {out_dir}\n")


def run_all_builds(resolved_builds: list[BuildConfig], dry_run: bool) -> None:
    log("trace", f"[run_all_builds] Resolved build: {resolved_builds}")

    for i, build_cfg in enumerate(resolved_builds, 1):
        build_log_level = build_cfg.get("log_level")
        prev_level = current_runtime["log_level"]

        build_cfg["dry_run"] = dry_run
        if build_log_level:
            current_runtime["log_level"] = build_log_level
            log("debug", f"Overriding log level → {build_log_level}")

        log("info", f"▶️  Build {i}/{len(resolved_builds)}")
        run_build(build_cfg)

        if build_log_level:
            current_runtime["log_level"] = prev_level

    log("info", "🎉 All builds complete.")
