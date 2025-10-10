#!/usr/bin/env bash
# ./dev/check-license.sh
# Run GitHub's license detector (Licensee) inside a temporary Ruby container.
# No Ruby or gems are installed on the host.

set -euo pipefail

# Allow running from any directory
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

# Choose runtime: prefer podman, fallback to docker
RUNTIME=$(command -v podman || command -v docker || true)
if [[ -z "$RUNTIME" ]]; then
  echo "❌ Neither podman nor docker found. Please install one." >&2
  exit 1
fi

# Image tag — full name avoids registry confusion
IMAGE="docker.io/library/ruby:3.3-bookworm"

# Simple status messages
echo "🧾 Running Licensee in container via: $RUNTIME"
echo "   Image: $IMAGE"
echo

# Pull if needed (quietly)
$RUNTIME pull -q "$IMAGE" >/dev/null 2>&1 || true

# Run Licensee
$RUNTIME run --rm \
  -v "$PWD":/repo -w /repo \
  "$IMAGE" bash -c '
    set -e
    apt-get update -qq
    apt-get install -y --no-install-recommends cmake git > /dev/null
    gem install --no-document licensee > /dev/null
    echo "📄 Licensee output:"
    echo "-------------------"
    licensee detect .
  '

echo
echo "✅ Done. (Container removed automatically)"
