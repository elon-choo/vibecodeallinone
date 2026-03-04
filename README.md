# Claude Code Power Pack

[![CI](https://github.com/elon-choo/vibecodeallinone/actions/workflows/ci.yml/badge.svg)](https://github.com/elon-choo/vibecodeallinone/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

12 AI skills + Knowledge Graph MCP server for [Claude Code](https://claude.com/claude-code).

Clean code enforcement, vibe coding orchestration, codebase-aware reviews, and intelligent context management — all in one package.

![Demo](docs/assets/demo.gif)

## 30-Second Install

```bash
git clone https://github.com/elon-choo/vibecodeallinone.git
cd vibecodeallinone
bash scripts/install.sh
```

## Installation Tiers

| Tier | What You Get | Requirements | Cost |
|------|-------------|-------------|------|
| **1: Skills** | 12 AI skills | None | $0 |
| **2: + KG MCP** | + Knowledge Graph server | Python 3.11+, Neo4j | $0 |
| **3: Full** | + Auto-trigger hooks | Same as Tier 2 | $0 |

### Tier 1: Skills Only (Recommended Start)

Zero dependencies. Just copy 12 skill directories:

```bash
bash scripts/install.sh 1
```

### Tier 2: Add Knowledge Graph

Adds a Neo4j-powered MCP server for dependency-aware code reviews:

```bash
brew install neo4j && neo4j start   # one-time setup
bash scripts/install.sh 2
# Edit ~/.claude/power-pack.env with your Gemini API key (free)
```

### Tier 3: Full Automation

Adds hooks that auto-trigger KG context on every code operation:

```bash
bash scripts/install.sh 3
```

## Skills (12)

| Skill | Layer | What It Does |
|-------|-------|-------------|
| **clean-code-mastery** | Quality | SOLID/DRY/KISS + OWASP for 8 languages |
| **vibe-coding-orchestrator** | Integration | Coordinates all skills across 9 layers |
| **codebase-graph** | Foundation | In-memory code knowledge graph |
| **smart-context** | Foundation | Token-efficient context (72-77% savings) |
| **impact-analyzer** | Analysis | Change propagation + risk scoring |
| **arch-visualizer** | Analysis | Mermaid/PlantUML architecture diagrams |
| **code-reviewer** | Integration | Quality gate scoring |
| **security-shield** | Quality | OWASP Top 10, 40+ secret detection patterns |
| **code-smell-detector** | Validation | 22 code smell patterns |
| **naming-convention-guard** | Validation | Per-language naming rules |
| **tdd-guardian** | Quality | TDD workflow, fake-test detection |
| **graph-loader** | Foundation | JSON-to-Neo4j graph loader |

## Knowledge Graph MCP Server

When installed (Tier 2+), provides 20+ MCP tools:

| Tool | Purpose |
|------|---------|
| `hybrid_search` | BM25 + vector search fusion |
| `smart_context` | Intent-aware context at 6 detail levels |
| `sync_incremental` | Real-time graph updates on code changes |
| `get_call_graph` | Function call relationship graph |
| `simulate_impact` | Change impact prediction |
| `evaluate_code` | LLM-powered quality scoring |
| `suggest_tests` | Automatic test generation |
| `get_bug_hotspots` | Bug-prone area detection |

**Tech Stack**: Neo4j (local), Gemini 3 Flash, Voyage AI voyage-code-3, Tree-sitter (7 languages)

**Benchmark** (10-query suite, `scripts/ralphloop/e2e/t3_benchmark.py`):

| Method | Avg Precision | Avg Recall | Time |
|--------|--------------|------------|------|
| Vanilla grep | 0.155 | 0.933 | 295ms |
| KG hybrid search | 0.243 | 0.783 | 315ms |
| **Delta** | **+0.088** | -0.150 | +20ms |

> KG hybrid search achieves **57% higher precision** by leveraging import graph analysis and node relevance ranking, reducing noise from irrelevant file matches.

## Quick Start

In your Claude Code session:

```
vibe review src/app.ts        # Full code review with all skills
vibe init                      # Set up a new project
vibe secure                    # Security scan
vibe pipeline                  # Run all quality stages
vibe impact src/auth.ts        # Change impact analysis
```

> These are conversation triggers (type in Claude Code chat, not terminal).

## Configuration

```yaml
# .vibeconfig.yml (in your project root)
global:
  language: "typescript"
  maturity: 2  # 1=MVP, 2=Stable, 3=Scalable, 4=Enterprise

skills:
  clean-code-mastery:
    strictness: "standard"  # relaxed | standard | strict

kg:
  enabled: true
  context_level: 3
```

## Graceful Degradation

Everything works without Neo4j or API keys:

| Component | Without Neo4j | Without API Keys |
|-----------|-------------|-----------------|
| 12 Skills | Full functionality | Full functionality |
| KG MCP Tools | Disabled (skills still work) | Keyword search only (no vectors) |
| Hooks | Skip silently | Skip silently |

## Cross-Tool Compatibility

| Tool | Method |
|------|--------|
| **Claude Code** | Native (`SKILL.md`) |
| **Codex CLI** | Via `AGENTS.md` |
| **Gemini CLI** | Via `AGENTS.md` |
| **Cursor** | Adaptable (`.cursor/rules`) |
| **Windsurf** | Adaptable (`.windsurfrules`) |

## Cost

| Component | Provider | Cost |
|-----------|----------|------|
| Neo4j | Local (Homebrew) | $0 |
| Gemini 3 Flash | Google AI Studio free tier | $0 |
| Voyage Embeddings | Initial indexing | ~$1-2 one-time |
| Voyage Embeddings | Monthly maintenance | $0.01-0.10 |

**Total: $0-2/month.** Skills work completely free without any API keys.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
