#!/usr/bin/env bash
set -euo pipefail

# Ensure every skill in ~/.agents/skills has a symlink in ~/.claude/skills.
# Existing links (even pointing elsewhere) are left untouched.
# Can be run standalone or sourced by the backup script.

AGENTS_SKILLS_DIR="${AGENTS_SKILLS_DIR:-/home/rmer/.agents/skills}"
CLAUDE_SKILLS_DIR="${CLAUDE_SKILLS_DIR:-/home/rmer/.claude/skills}"

link_missing_skills() {
  if [[ ! -d "$AGENTS_SKILLS_DIR" ]]; then
    echo "Source skills dir not found: $AGENTS_SKILLS_DIR" >&2
    return 1
  fi

  mkdir -p "$CLAUDE_SKILLS_DIR"

  local created=0
  local name target link
  for src in "$AGENTS_SKILLS_DIR"/*/; do
    [[ -d "$src" ]] || continue
    name="$(basename "$src")"
    link="$CLAUDE_SKILLS_DIR/$name"

    # Skip if a link/file/dir already exists for this skill.
    if [[ -e "$link" || -L "$link" ]]; then
      continue
    fi

    # Relative target: ~/.claude/skills/<name> -> ../../.agents/skills/<name>
    target="../../.agents/skills/$name"
    ln -s "$target" "$link"
    echo "Linked skill: $name -> $target"
    created=$((created + 1))
  done

  if [[ "$created" -eq 0 ]]; then
    echo "All skills already linked into $CLAUDE_SKILLS_DIR."
  else
    echo "Created $created new skill link(s)."
  fi
}

# Run automatically only when executed directly (not when sourced).
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  link_missing_skills
fi
