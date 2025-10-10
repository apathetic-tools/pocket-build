#!/usr/bin/env bash
# dev/list-project.sh
# -------------------------------------------------------
# 📂 Project Structure Lister (stable + indented)
# -------------------------------------------------------

set -euo pipefail
shopt -s globstar nullglob dotglob extglob

IGNORE_DIRS=(
  ".git" ".mypy_cache" ".ruff_cache" ".pytest_cache"
  ".venv" "__pycache__" "node_modules" "dist" "build"
)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# --- Header ---
echo "📦 Project structure under: $ROOT_DIR"
echo "🧹 Ignoring: ${IGNORE_DIRS[*]}" | sed 's/ /, /g'
echo "-------------------------------------------------------"

# --- Build -prune expression for find ---
PRUNE_EXPR=()
for d in "${IGNORE_DIRS[@]}"; do
  PRUNE_EXPR+=(-name "$d" -prune -o)
done

# --- Collect paths ---
mapfile -t all_paths < <(
  find . "${PRUNE_EXPR[@]}" -print0 2>/dev/null | sort -z | tr '\0' '\n'
)

echo "Formatted tree:"
set +e  # disable exit-on-error inside loop

count=0
for p in "${all_paths[@]}"; do
  p="${p#./}"
  [[ "$p" == "." ]] && continue

  slashes="${p//[^\/]/}"
  depth=${#slashes}
  indent=$(printf "%*s" $((depth * 2)) "")

  if [[ -d "$p" ]]; then
    printf "%s📁 %s\n" "$indent" "$p"
    ((count++))
  elif [[ -f "$p" ]]; then
    printf "%s📄 %s\n" "$indent" "$p"
    ((count++))
  fi
done

set -e
echo "-------------------------------------------------------"
echo "✅ Done. Printed $count visible entries."
