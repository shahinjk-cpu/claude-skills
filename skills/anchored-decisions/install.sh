#!/usr/bin/env bash
# Anchored Decisions installer. Idempotent, no sudo, no dependencies.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="anchored-decisions"
MODE="user"
PROJECT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --user)       MODE="user" ;;
    --cli-only)   MODE="cli" ;;
    --project)    MODE="project"; PROJECT="${2:-}"; shift ;;
    -h|--help)
      sed -n '1,8p' "$0"
      echo "Usage: ./install.sh [--user | --project <repo> | --cli-only]"
      exit 0 ;;
    *) echo "install.sh: unknown option '$1'" >&2; exit 2 ;;
  esac
  shift
done

command -v python3 >/dev/null 2>&1 || { echo "install.sh: python3 is required" >&2; exit 1; }
PYV=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')
echo "python3 $PYV found"

install_files() {   # $1 = destination skill directory
  mkdir -p "$1/templates" "$1/examples" "$1/hooks"
  cp "$SRC/SKILL.md" "$SRC/GUIDE.md" "$SRC/anchor-check.py" "$1/"
  cp "$SRC/templates/"* "$1/templates/"
  cp "$SRC/examples/"* "$1/examples/"
  cp "$SRC/hooks/pre-commit" "$1/hooks/"
  chmod +x "$1/anchor-check.py" "$1/hooks/pre-commit"
  echo "installed skill -> $1"
}

link_cli() {        # $1 = path to anchor-check.py
  mkdir -p "$HOME/.local/bin"
  ln -sf "$1" "$HOME/.local/bin/anchor-check"
  echo "linked CLI   -> ~/.local/bin/anchor-check"
  case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) echo "note: ~/.local/bin is not on PATH - add it, or call the script by path" ;;
  esac
}

case "$MODE" in
  user)
    DEST="$HOME/.claude/skills/$NAME"
    install_files "$DEST"
    link_cli "$DEST/anchor-check.py"
    echo
    echo "Claude Code will load the skill in every project on this machine."
    ;;
  project)
    [ -n "$PROJECT" ] || { echo "install.sh: --project needs a path" >&2; exit 2; }
    [ -d "$PROJECT" ] || { echo "install.sh: no such directory: $PROJECT" >&2; exit 2; }
    DEST="$PROJECT/.claude/skills/$NAME"
    install_files "$DEST"
    echo
    echo "Commit .claude/skills/$NAME so teammates get it on checkout."
    echo "Run it with: python3 .claude/skills/$NAME/anchor-check.py"
    ;;
  cli)
    DEST="$HOME/.local/share/$NAME"
    mkdir -p "$DEST"
    cp "$SRC/anchor-check.py" "$DEST/"
    chmod +x "$DEST/anchor-check.py"
    echo "installed CLI -> $DEST/anchor-check.py"
    link_cli "$DEST/anchor-check.py"
    ;;
esac

echo
echo "Next: cd into a repo and run"
echo "  anchor-check --init"
echo "  anchor-check --new \"<the decision you just made>\""
echo "  anchor-check"
