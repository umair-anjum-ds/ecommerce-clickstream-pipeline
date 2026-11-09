#!/usr/bin/env bash
# One-time git setup for this project.
#
# Usage:
#   bash scripts/git_setup.sh                                  # only create the local repository and first commit
#   bash scripts/git_setup.sh https://github.com/YOU/REPO.git  # also connect GitHub and push
set -e

REMOTE_URL="$1"

if [ ! -d .git ]; then
  git init -b main
  echo "Created a new git repository."
fi

git add .
if git diff --cached --quiet; then
  echo "Nothing new to commit."
else
  git commit -m "feat: initial commit of the clickstream analytics pipeline"
fi

if [ -n "$REMOTE_URL" ]; then
  git remote remove origin 2>/dev/null || true
  git remote add origin "$REMOTE_URL"
  git push -u origin main
  echo "Pushed to $REMOTE_URL. Open the Actions tab on GitHub to watch the pipeline run."
else
  echo "Next: create an empty repository on GitHub, then run:"
  echo "  bash scripts/git_setup.sh https://github.com/YOU/REPO.git"
fi
