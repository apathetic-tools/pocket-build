import shutil
from pathlib import Path
from typing import List, Optional

from .types import BuildConfig, IncludeEntry
from .utils import GREEN, RESET, YELLOW, is_excluded


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
