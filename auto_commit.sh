#!/bin/bash
cd /home/omethsk/jarvis || exit 1
git add -A
if ! git diff --cached --quiet; then
  git commit -m "Auto-commit: $(date "+%Y-%m-%d %H:%M:%S")"
  git push origin main
fi
