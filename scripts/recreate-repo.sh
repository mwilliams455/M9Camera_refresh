#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="${1:-M9Cam-Recovered}"
mkdir -p "$REPO_DIR"
cp -a "$(cd "$(dirname "$0")/.." && pwd)/." "$REPO_DIR/"
rm -rf "$REPO_DIR/.git"
cd "$REPO_DIR"
git init
git add .
git commit -m "Recover M9Cam through v0.7ZQ PERF3I"
echo "Created local Git repository at: $(pwd)"
echo "Add your GitHub remote, then: git push -u origin HEAD:main"
