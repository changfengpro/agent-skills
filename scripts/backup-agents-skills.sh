#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="/home/rmer/.agents"
BACKUP_DIR="/home/rmer/project/git/skills"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Before backing up, ensure every skill has a symlink in ~/.claude/skills.
source "$SCRIPT_DIR/link-skills.sh"
link_missing_skills

cd "$BACKUP_DIR"

rsync -a --delete --delete-excluded \
  --exclude-from="$SCRIPT_DIR/backup-exclude.txt" \
  "$SOURCE_DIR/skills/" "$BACKUP_DIR/skills/"
rsync -a "$SOURCE_DIR/.skill-lock.json" "$BACKUP_DIR/.skill-lock.json"

git add -A skills .skill-lock.json

if git diff --cached --quiet; then
  echo "No skill changes to back up."
  exit 0
fi

git commit -m "Backup agents skills $(date '+%Y-%m-%d %H:%M:%S')"
