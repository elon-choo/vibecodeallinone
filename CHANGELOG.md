# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-03-01

### Added

- **12 AI Skills** for Claude Code with YAML frontmatter and cross-tool compatibility
  - `clean-code-mastery` — SOLID/DRY/KISS + OWASP enforcement for 8 languages
  - `vibe-coding-orchestrator` — 9-layer skill coordination
  - `codebase-graph` — In-memory code knowledge graph
  - `smart-context` — Token-efficient context extraction (72-77% savings)
  - `impact-analyzer` — Change propagation and risk scoring
  - `arch-visualizer` — Mermaid/PlantUML architecture diagrams
  - `code-reviewer` — Quality gate scoring
  - `security-shield` — OWASP Top 10, 40+ secret detection patterns
  - `code-smell-detector` — 22 code smell patterns
  - `naming-convention-guard` — Per-language naming rules
  - `tdd-guardian` — TDD workflow with fake-test detection
  - `graph-loader` — JSON-to-Neo4j graph loader
- **Knowledge Graph MCP Server v2.1** with 20+ tools
  - `hybrid_search` — BM25 + vector search fusion
  - `smart_context` — Intent-aware context at 6 detail levels
  - `sync_incremental` — Real-time graph updates on code changes
  - `evaluate_code` — LLM-powered quality scoring
  - `suggest_tests` — Automatic test generation suggestions
  - `get_bug_hotspots` — Bug-prone area detection
  - Tech stack: Neo4j (local), Gemini 3 Flash, Voyage AI voyage-code-3, Tree-sitter (7 languages)
  - Benchmark: keyword P@1 0.720, vector P@1 0.680, hybrid P@1 0.680
- **8 automation hooks** for seamless KG integration
  - `mcp-kg-auto-trigger` — Auto-injects KG context on prompt submit
  - `kg-incremental-indexer` — Indexes changed files after write/edit
  - `kg-precheck` — Warns when writing code without KG context
  - `kg-bulk-indexer` — Full project indexing
  - `kg-auto-judge` — LLM-based quality evaluation
  - `kg-feedback-collector` — User feedback collection
  - `kg-survival-checker` — MCP server health monitoring
  - `post-mcp-kg` — Post-tool KG sync trigger
- **3-tier installation** via `scripts/install.sh`
  - Tier 1: Skills only (zero dependencies, $0)
  - Tier 2: + KG MCP Server (Python 3.11+, Neo4j)
  - Tier 3: + Auto-trigger hooks
- **Cross-tool compatibility** via `AGENTS.md`
  - Native: Claude Code (SKILL.md)
  - Via AGENTS.md: Codex CLI, Gemini CLI
  - Adaptable: Cursor, Windsurf, GitHub Copilot
- **Graceful degradation** — all skills work without Neo4j or API keys
- `.vibeconfig.yml` project-level configuration
- `CONTRIBUTING.md` with skill authoring standards
- `AGENTS.md` for cross-tool agent compatibility

### Security

- Removed all hardcoded credentials; secrets loaded from environment variables
- Added `security-shield` skill with 40+ secret detection patterns

[2.0.0]: https://github.com/elon-opensource/claude-code-power-pack/releases/tag/v2.0.0
