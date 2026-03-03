#!/bin/bash
# Claude Code Power Pack - Validation Script
# Run before submitting a Pull Request

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
FAILED=0

echo "Claude Code Power Pack - Validation"
echo "===================================="
echo ""

# 1. Ruff lint check
echo -n "[1/4] Ruff lint check... "
if command -v ruff &> /dev/null; then
  if ruff check "$ROOT_DIR" --quiet 2>/dev/null; then
    echo -e "${GREEN}PASS${NC}"
  else
    echo -e "${RED}FAIL${NC}"
    ruff check "$ROOT_DIR" 2>/dev/null || true
    FAILED=$((FAILED + 1))
  fi
else
  echo -e "${YELLOW}SKIP (ruff not installed)${NC}"
fi

# 2. Pytest
echo -n "[2/4] Pytest... "
if command -v pytest &> /dev/null; then
  if pytest "$ROOT_DIR/tests" --quiet --no-header 2>/dev/null; then
    echo -e "${GREEN}PASS${NC}"
  else
    echo -e "${RED}FAIL${NC}"
    FAILED=$((FAILED + 1))
  fi
else
  echo -e "${YELLOW}SKIP (pytest not installed)${NC}"
fi

# 3. SKILL.md frontmatter check
echo -n "[3/4] SKILL.md frontmatter check... "
SKILL_FAIL=0
for skill_file in "$ROOT_DIR/skills"/*/SKILL.md; do
  if [ -f "$skill_file" ]; then
    # Check that file starts with ---
    if ! head -1 "$skill_file" | grep -q "^---"; then
      echo ""
      echo -e "  ${RED}Missing frontmatter: $skill_file${NC}"
      SKILL_FAIL=1
    fi
  fi
done
if [ "$SKILL_FAIL" -eq 0 ]; then
  echo -e "${GREEN}PASS${NC}"
else
  FAILED=$((FAILED + 1))
fi

# 4. No hardcoded secrets
echo -n "[4/4] Secret scan... "
SECRET_FAIL=0
# Check for common secret patterns (excluding .env.example and tests)
if grep -rn "password123\|sk-[a-zA-Z0-9]\{20,\}\|AKIA[A-Z0-9]\{16\}" \
    --include="*.py" --include="*.sh" --include="*.md" --include="*.yml" \
    --exclude-dir=".git" --exclude-dir=".venv" --exclude-dir="node_modules" \
    "$ROOT_DIR" 2>/dev/null | grep -v ".env.example" | grep -v "test_config.py"; then
  SECRET_FAIL=1
fi
if [ "$SECRET_FAIL" -eq 0 ]; then
  echo -e "${GREEN}PASS${NC}"
else
  echo -e "${RED}FAIL - potential secrets found${NC}"
  FAILED=$((FAILED + 1))
fi

echo ""
echo "===================================="
if [ "$FAILED" -eq 0 ]; then
  echo -e "${GREEN}All checks passed!${NC}"
  exit 0
else
  echo -e "${RED}$FAILED check(s) failed.${NC}"
  exit 1
fi
