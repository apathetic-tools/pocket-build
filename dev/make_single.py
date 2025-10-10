# dev/make_single.py
"""
Concatenate all source modules into one readable pocket-build.py file.
"""

import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
src_dir = root / "src"
out_file = root / "bin" / "pocket-build.py"

ORDER = [
    "types.py",
    "utils.py",
    "jsonc_loader.py",
    "copier.py",
    "main.py",
]


def strip_imports(text: str) -> str:
    """Remove internal imports between modules."""
    lines = text.splitlines()
    result = []
    for line in lines:
        if re.match(r"from\s+src(\.|$)", line) or re.match(r"import\s+src", line):
            continue
        result.append(line)
    return "\n".join(result)


parts = []
for filename in ORDER:
    path = src_dir / filename
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^#!.*\n", "", text)  # remove shebangs
    text = strip_imports(text)
    header = f"# === {filename} ==="
    parts.append(f"\n{header}\n{text.strip()}\n")

# Combine
result = "#!/usr/bin/env python3\n" + "\n".join(parts)
out_file.parent.mkdir(parents=True, exist_ok=True)
out_file.write_text(result, encoding="utf-8")

print(f"✅ Built {out_file.relative_to(root)} ({len(parts)} modules).")
