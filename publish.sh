#!/usr/bin/env bash
#
# One command to update the course site:
#   1. rebuild index.html and copy the latest slide/pset/syllabus PDFs
#   2. commit everything
#   3. push to GitHub (which refreshes GitHub Pages automatically)
#
# Usage:  ./publish.sh ["optional commit message"]
#
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Building site..."
python3 build.py

echo "==> Committing..."
git add -A

if git diff --cached --quiet; then
  echo "Nothing changed. Site is already up to date."
  exit 0
fi

MSG="${1:-Update site $(date '+%Y-%m-%d %H:%M')}"
git commit -m "$MSG"

echo "==> Pushing..."
git push

echo "Done. GitHub Pages will refresh in ~1 minute."
