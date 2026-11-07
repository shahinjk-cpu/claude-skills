#!/usr/bin/env bash
# Restore Claude Code skills from this repo to ~/.claude/skills/
# Usage: bash install.sh

set -e

SKILLS_DIR="$HOME/.claude/skills"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing skills to $SKILLS_DIR..."
mkdir -p "$SKILLS_DIR"

# Copy all skills (skip if already exists gstack — install that separately)
for skill_dir in "$REPO_DIR/skills"/*/; do
  skill_name="$(basename "$skill_dir")"
  if [ "$skill_name" = "gstack" ] || [ "$skill_name" = "gstack.bak" ]; then
    echo "  skip $skill_name (install gstack separately: https://github.com/garrytan/gstack)"
    continue
  fi
  dest="$SKILLS_DIR/$skill_name"
  if [ -e "$dest" ]; then
    echo "  skip $skill_name (already exists)"
  else
    cp -r "$skill_dir" "$dest"
    echo "  + $skill_name"
  fi
done

echo ""
echo "Done. To install gstack:"
echo "  git clone https://github.com/garrytan/gstack.git ~/.claude/skills/gstack"
echo "  cd ~/.claude/skills/gstack && ./setup"
