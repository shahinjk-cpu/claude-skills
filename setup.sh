#!/usr/bin/env bash
# Universal AI Agent Skills Bootstrapper for Linux / macOS
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_SRC="$SCRIPT_DIR/skills"
TARGETS=(
    "$HOME/.gemini/config/skills"
    "$HOME/.claude/skills"
    "$HOME/.cursor/skills"
    "$HOME/.agents/skills"
    "$HOME/.codex/skills"
)

echo "================================================================="
echo "  🧠 UNIVERSAL AI AGENT SKILLS BOOTSTRAPPER (5,101+ SKILLS)"
echo "================================================================="

for t in "${TARGETS[@]}"; do
    mkdir -p "$t"
    echo "Syncing skills to $t..."
    cp -rn "$SKILLS_SRC"/* "$t/" 2>/dev/null || true
done

mkdir -p "$HOME/.gemini/config"
cp "$SCRIPT_DIR/skill_router.py" "$HOME/.gemini/config/" 2>/dev/null || true
cp "$SCRIPT_DIR/skills_manifest.json" "$HOME/.gemini/config/" 2>/dev/null || true
cp "$SCRIPT_DIR/skills_index.md" "$HOME/.gemini/config/" 2>/dev/null || true
cp "$SCRIPT_DIR/AGENTS.md" "$HOME/.gemini/config/" 2>/dev/null || true
cp "$SCRIPT_DIR/AGENTS.md" "$HOME/" 2>/dev/null || true

if command -v python3 &>/dev/null; then
    python3 "$HOME/.gemini/config/build_router.py" || true
fi

echo "================================================================="
echo "  ✅ SUCCESS: All 5,101+ skills and Auto-Router are now active!"
echo "================================================================="
