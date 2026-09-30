#!/usr/bin/env bash
# Build, commit the website files, and publish to origin/main.
set -euo pipefail
cd -P "$(dirname "$0")"

usage() {
  cat <<'HELP'
Usage (from the ECON139 folder):
  ./website/publish.sh ["commit message"]  Build, commit, and push to GitHub
  ./website/publish.sh --check             Validate/report changes; no writes
  ./website/publish.sh --sources           Show exact source files to edit
  ./website/publish.sh --local             Build locally; no commit or push
  ./website/publish.sh --preview           Build and serve at localhost:8000
  ./website/publish.sh --help              Show this help

Export edited slides to PDF in the original course folders first.
Edit teaching code/data in materials/<topic>/code/ and data/.
Individual downloads and topic ZIPs update together.
Edit website/course.json to change source files and releases.
Edit website/schedule.json to move materials between weeks.
Use PORT=8001 ./website/publish.sh --preview to select another preview port.
HELP
}

if (( $# > 1 )); then
  usage >&2
  exit 2
fi

case "${1:-}" in
  --help|-h) usage; exit 0 ;;
  --sources) exec python3 build.py --sources ;;
  --check) exec python3 build.py --check ;;
  --local) exec python3 build.py ;;
  --preview)
    python3 build.py
    echo "Preview: http://localhost:${PORT:-8000} (Ctrl-C to stop)"
    exec python3 -m http.server "${PORT:-8000}" --bind 127.0.0.1
    ;;
  --*) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
esac

if [[ "$(git rev-parse --show-toplevel)" != "$PWD" ]]; then
  echo "Publishing requires website/ to be its own Git repository." >&2
  exit 1
fi
if [[ "$(git symbolic-ref --quiet --short HEAD)" != main ]]; then
  echo "Switch to the main branch before publishing." >&2
  exit 1
fi
if ! git remote get-url origin >/dev/null; then
  echo "Configure the origin remote before publishing (see README.md)." >&2
  exit 1
fi

# Do not include unrelated files that were already staged by another task.
while IFS= read -r -d '' path; do
  case "$path" in
    .gitignore|.nojekyll|AGENTS.md|README.md|PROJECT_NOTES.md|SOURCE_FILES.md|build.py|publish.sh|course.json|schedule.json|index.html|assets/*|downloads/*|slides/*|psets/*|syllabus/*|tests/*) ;;
    *) echo "Unrelated file is staged: $path. Unstage it before publishing." >&2; exit 1 ;;
  esac
done < <(git diff --cached --name-only -z)

echo "Validating and building..."
python3 build.py

# Explicit paths: an unrelated file in the repo root is not automatically added.
if [[ -d downloads ]] || [[ -n "$(git ls-files -- downloads)" ]]; then
  git add -A -- downloads
fi
git add -A -- .gitignore .nojekyll AGENTS.md README.md PROJECT_NOTES.md \
  build.py publish.sh course.json schedule.json index.html SOURCE_FILES.md assets slides psets syllabus tests

if git diff --cached --quiet; then
  echo "No new changes to commit."
else
  git commit -m "${1:-Update course site $(date '+%Y-%m-%d %H:%M')}"
fi

# A previous run may have committed successfully and then failed to push.
# Only skip pushing when this branch has an upstream and HEAD is already there.
if [[ "$(git rev-parse --abbrev-ref '@{upstream}' 2>/dev/null || true)" == origin/main ]] && \
   [[ "$(git rev-parse HEAD)" == "$(git rev-parse refs/remotes/origin/main 2>/dev/null)" ]]; then
  echo "No local commits waiting to publish."
  exit 0
fi

echo "Pushing to origin/main..."
if ! git push --set-upstream origin main; then
  echo "Push failed. Your local commit is saved; fix the reported issue and rerun this command." >&2
  exit 1
fi
echo "Push complete. GitHub Pages must be enabled for main / root; deployment may take a few minutes."
