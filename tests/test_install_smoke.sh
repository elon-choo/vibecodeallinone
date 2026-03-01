#!/bin/bash
# Smoke test for install.sh Tier 1
# Usage: bash tests/test_install_smoke.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Use temp home to avoid clobbering real ~/.claude/skills
export HOME=$(mktemp -d)
echo "Test HOME: $HOME"

# Run Tier 1 install
bash "$ROOT_DIR/scripts/install.sh" 1

# Verify skills directory exists
if [ ! -d "$HOME/.claude/skills" ]; then
  echo "FAIL: ~/.claude/skills not created"
  rm -rf "$HOME"
  exit 1
fi

# Count installed skills
INSTALLED=$(ls -d "$HOME/.claude/skills"/*/ 2>/dev/null | wc -l | tr -d ' ')
echo "Installed skills: $INSTALLED"

if [ "$INSTALLED" -lt 12 ]; then
  echo "FAIL: Expected 12 skills, got $INSTALLED"
  ls "$HOME/.claude/skills/"
  rm -rf "$HOME"
  exit 1
fi

# Verify each skill has SKILL.md
MISSING=0
for skill_dir in "$HOME/.claude/skills"/*/; do
  if [ ! -f "$skill_dir/SKILL.md" ]; then
    echo "FAIL: Missing SKILL.md in $(basename "$skill_dir")"
    MISSING=$((MISSING + 1))
  fi
done

if [ "$MISSING" -gt 0 ]; then
  rm -rf "$HOME"
  exit 1
fi

echo "PASS: All 12 skills installed with SKILL.md"

# Cleanup
rm -rf "$HOME"
exit 0
