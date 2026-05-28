#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="/home/rmer/.agents"
BACKUP_DIR="/home/rmer/project/git/skills"

cd "$BACKUP_DIR"

rsync -a --delete "$SOURCE_DIR/skills/" "$BACKUP_DIR/skills/"
rsync -a "$SOURCE_DIR/.skill-lock.json" "$BACKUP_DIR/.skill-lock.json"

git add -A skills .skill-lock.json

if git diff --cached --quiet; then
  echo "No skill changes to back up."
  exit 0
fi

git commit -m "Backup agents skills $(date '+%Y-%m-%d %H:%M:%S')"
