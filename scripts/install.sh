#!/bin/bash
# Power Pack developer toolkit installer
# Supports 3 installation tiers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
SKILLS_DIR="${HOME}/.claude/skills"
HOOKS_DIR="${HOME}/.claude/hooks"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

usage() {
  cat <<'EOF'
Power Pack Developer Toolkit Installer

Usage:
  bash scripts/install.sh [1|2|3]

Tiers:
  1  Install 12 Claude Code skills only
  2  Install skills + KG MCP server
  3  Install skills + KG MCP server + hooks

For the assistant runtime self-host reference stack, use:
  bash scripts/assistant/bootstrap_runtime.sh --target <dir>
EOF
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  usage
  exit 0
fi

echo -e "${BLUE}Claude Code Power Pack - Developer Toolkit Installer${NC}"
echo "===================================="
echo ""
echo "Installation Tiers:"
echo "  1) Skills Only     - 12 AI skills, zero dependencies (\$0/month)"
echo "  2) Skills + KG MCP - Adds Knowledge Graph MCP server (Python required)"
echo "  3) Full            - Adds auto-trigger hooks for seamless KG integration"
echo "  Runtime stack      - Use scripts/assistant/bootstrap_runtime.sh"
echo ""

# Default to tier 1 if argument provided, otherwise ask
TIER=${1:-0}
if [ "$TIER" = "0" ]; then
  read -p "Select tier (1/2/3) [1]: " TIER
  TIER=${TIER:-1}
fi

case "$TIER" in
  1|2|3) ;;
  *)
    echo -e "${YELLOW}Invalid tier: $TIER${NC}"
    usage
    exit 1
    ;;
esac

echo ""

# === TIER 1: Skills ===
echo -e "${GREEN}[Tier 1] Installing 12 skills...${NC}"
mkdir -p "$SKILLS_DIR"

INSTALLED=0
for skill_dir in "$ROOT_DIR/skills"/*/; do
  skill_name=$(basename "$skill_dir")

  if [ -d "$SKILLS_DIR/$skill_name" ]; then
    echo "  Updating: $skill_name"
    # Safe backup: verify target is under SKILLS_DIR before removing
    if [ -d "$SKILLS_DIR/${skill_name}.bak" ] && [[ "$SKILLS_DIR/${skill_name}.bak" == "${HOME}/.claude/skills/"* ]]; then
      rm -rf "$SKILLS_DIR/${skill_name}.bak"
    fi
    mv "$SKILLS_DIR/$skill_name" "$SKILLS_DIR/${skill_name}.bak"
  else
    echo "  Installing: $skill_name"
  fi

  cp -r "$skill_dir" "$SKILLS_DIR/$skill_name"
  INSTALLED=$((INSTALLED + 1))
done

echo -e "${GREEN}  $INSTALLED skills installed${NC}"
echo ""

if [ "$TIER" -lt 2 ]; then
  echo "Done! Skills are ready in your Claude Code sessions."
  echo "Try: 'vibe review' or 'vibe init'"
  echo "Assistant runtime reference stack: bash scripts/assistant/bootstrap_runtime.sh --target <dir>"
  exit 0
fi

# === TIER 2: KG MCP Server ===
echo -e "${GREEN}[Tier 2] Setting up Knowledge Graph MCP Server...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
  echo -e "${YELLOW}  Python 3 not found. Please install Python 3.11+ first.${NC}"
  exit 1
fi

KG_DEST="${HOME}/.claude/kg-mcp-server"
mkdir -p "$KG_DEST"
cp -r "$ROOT_DIR/kg-mcp-server/"* "$KG_DEST/"

# Create venv
echo "  Creating Python virtual environment..."
python3 -m venv "$KG_DEST/venv"
source "$KG_DEST/venv/bin/activate"
pip install -r "$KG_DEST/requirements.txt"
deactivate

# Copy .env.example if no .env exists
if [ ! -f "${HOME}/.claude/power-pack.env" ]; then
  cp "$ROOT_DIR/.env.example" "${HOME}/.claude/power-pack.env"
  echo -e "${YELLOW}  Created ~/.claude/power-pack.env - edit with your API keys${NC}"
fi

# Create launcher script that forces venv python
cat > "$KG_DEST/run.sh" << 'LAUNCHER'
#!/bin/bash
# KG MCP Server Launcher - ensures venv python is used
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
  echo "Error: venv not found at $SCRIPT_DIR/venv" >&2
  echo "Run the installer again: bash scripts/install.sh 2" >&2
  exit 1
fi

exec "$VENV_PYTHON" -m mcp_server.server "$@"
LAUNCHER
chmod +x "$KG_DEST/run.sh"

echo -e "${GREEN}  KG MCP Server installed at $KG_DEST${NC}"
echo -e "${GREEN}  Launcher: $KG_DEST/run.sh${NC}"
echo ""

# Auto-register MCP server in settings.json
SETTINGS_FILE="${HOME}/.claude/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
  # Check if already registered
  if ! grep -q "neo4j-knowledge-graph" "$SETTINGS_FILE" 2>/dev/null; then
    echo "  Registering MCP server in settings.json..."
    python3 -c "
import json, sys
try:
    with open('$SETTINGS_FILE', 'r') as f:
        settings = json.load(f)
    if 'mcpServers' not in settings:
        settings['mcpServers'] = {}
    settings['mcpServers']['neo4j-knowledge-graph'] = {
        'command': '$KG_DEST/run.sh',
        'args': [],
        'env': {}
    }
    with open('$SETTINGS_FILE', 'w') as f:
        json.dump(settings, f, indent=2)
    print('  MCP server registered successfully')
except Exception as e:
    print(f'  Warning: could not auto-register MCP server: {e}', file=sys.stderr)
"
  else
    echo "  MCP server already registered in settings.json"
  fi
else
  # Create settings.json with MCP server entry
  echo "  Creating settings.json with MCP server registration..."
  mkdir -p "$(dirname "$SETTINGS_FILE")"
  cat > "$SETTINGS_FILE" << SETTINGS
{
  "mcpServers": {
    "neo4j-knowledge-graph": {
      "command": "$KG_DEST/run.sh",
      "args": [],
      "env": {}
    }
  }
}
SETTINGS
  echo -e "${GREEN}  MCP server registered in settings.json${NC}"
fi

if [ "$TIER" -lt 3 ]; then
  echo "Done! MCP server registered. Edit ~/.claude/power-pack.env with your API keys."
  exit 0
fi

# === TIER 3: Hooks ===
echo -e "${GREEN}[Tier 3] Installing KG automation hooks...${NC}"
mkdir -p "$HOOKS_DIR"

for hook_file in "$ROOT_DIR/hooks/"*.py; do
  hook_name=$(basename "$hook_file")
  if [ -f "$HOOKS_DIR/$hook_name" ]; then
    echo "  Backing up existing: $hook_name"
    cp "$HOOKS_DIR/$hook_name" "$HOOKS_DIR/${hook_name}.bak"
  fi
  cp "$hook_file" "$HOOKS_DIR/$hook_name"
  echo "  Installed: $hook_name"
done

echo -e "${GREEN}  8 hooks installed${NC}"
echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit ~/.claude/power-pack.env with your credentials"
echo "  2. Install Neo4j: brew install neo4j && neo4j start"
echo "  3. Start a Claude Code session and try 'vibe review'"
echo "  4. For the assistant runtime reference stack, use scripts/assistant/bootstrap_runtime.sh"
