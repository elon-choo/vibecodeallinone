---
name: vibe-coding-orchestrator
description: "Context Architecture orchestrator for AI-assisted development. Use when performing full code reviews, pre-deploy audits, large-scale refactoring, or when multiple quality dimensions (security, testing, architecture, clean code) need simultaneous assessment. Triggers on 'vibe init', 'vibe review', 'vibe pipeline' commands. Coordinates clean-code-mastery, security, testing, and architecture skills."
license: MIT
compatibility: "Claude Code, Codex CLI, Gemini CLI. Adaptable to Cursor, Windsurf, GitHub Copilot."
metadata:
  version: "6.0.0"
  author: "elon-opensource"
  skills_included: 2
  skills_compatible: 18
allowed-tools:
  - Read
  - Glob
  - Grep
  - Agent
  - Skill
  - Bash
---

# Vibe Coding Orchestrator v6.0

**Context Architecture Master** — Includes 2 skills, coordinates up to 18 when available. Dependency-aware execution, Knowledge Graph integration, and multi-model quality gates. The orchestrator structures context so AI cannot fail.

> **Note**: This package includes `clean-code-mastery` and `vibe-coding-orchestrator`. The orchestrator can coordinate 16 additional skills when they are installed separately. See `core/skill-registry.md` for the full compatibility list.

## What's New in v6.0

### Architecture Upgrades
- **Context Architecture Pattern**: Environment structuring (AGENTS.md, CLAUDE.md, PLAN.md, PROGRESS.md) replaces raw prompt engineering
- **Knowledge Graph Native**: Deep integration with codebase-graph for dependency-aware orchestration
- **Multi-Model Review**: Parallel review routing to multiple AI models for quality gating
- **Cross-Tool Compatibility**: Agent Skills open standard (Claude Code, Codex, Gemini CLI, Cursor, Windsurf)
- **Parallel Execution**: Independent skills run concurrently via isolated worktrees
- **Error Amplification Control**: Limits cascading errors in multi-agent chains (17.2x → 4.4x)

### New Skills (+2)
- **context-architect**: Structures project context files for optimal AI performance
- **dependency-sentinel**: Monitors dependency health, CVEs, and update strategies

### 2026 Tool Updates
- **Vitest 3.x**: Default test runner
- **Biome 2.0**: Default linter+formatter
- **TanStack Router v2**: Type-safe routing
- **Drizzle ORM**: Type-safe SQL
- **Bun 1.2**: Package manager + runtime option
- **Effect-TS**: Typed functional effects (advanced)

## Skill Registry (18 Skills × 9 Layers)

| Layer | Priority | Skills | Purpose |
|-------|----------|--------|---------|
| **Context** | 0 | context-architect | Structure project context files |
| **Planning** | 1 | project-architect, tech-stack-advisor, requirements-analyzer | Design before code |
| **Foundation** | 2 | codebase-graph, smart-context | Codebase understanding |
| **Analysis** | 3 | impact-analyzer, arch-visualizer | Change impact assessment |
| **Quality** | 4 | clean-code-mastery, tdd-guardian, security-shield | Code quality gates |
| **Structure** | 5 | monorepo-architect, api-first-design | Architecture patterns |
| **Validation** | 6 | naming-convention-guard, code-smell-detector, dependency-sentinel | Verification |
| **Integration** | 7 | code-reviewer | Final unified review |
| **Production** | 8 | production-scale-launcher | Production readiness |

### Skill Dependency Graph

```
context-architect (0)
    └─→ project-architect (1)
        └─→ codebase-graph (2) ←── smart-context (2)
            └─→ impact-analyzer (3)
                └─→ clean-code-mastery (4) ←── security-shield (4) [BLOCKING]
                    └─→ tdd-guardian (4)
                        └─→ code-smell-detector (6)
                            └─→ code-reviewer (7)
                                └─→ production-scale-launcher (8)
```

## Context Architecture

The core innovation of v6.0: **structure the environment so AI cannot fail**.

```yaml
context_files:
  CLAUDE.md:
    purpose: "Project-level instructions, conventions, constraints"
    auto_generate: true
    includes:
      - project structure overview
      - coding conventions
      - dependency constraints
      - deployment targets

  PLAN.md:
    purpose: "Current implementation plan"
    auto_generate: "on new feature/refactor tasks"
    includes:
      - task breakdown
      - dependency order
      - acceptance criteria

  PROGRESS.md:
    purpose: "Track progress across sessions"
    auto_update: "after each completed task"
    includes:
      - completed items
      - current blockers
      - next steps

  AGENTS.md:
    purpose: "Cross-tool skill discovery (Codex, Gemini CLI)"
    auto_generate: true
    format: "Agent Skills open standard"
```

## Knowledge Graph Integration

```yaml
kg_workflow:
  on_task_start:
    action: "hybrid_search for related code patterns"
    benefit: "context-aware skill selection"

  during_orchestration:
    action: "smart_context at appropriate detail levels"
    levels:
      existence_check: 0    # ~5 tokens
      interface_review: 1    # ~20 tokens
      api_understanding: 2   # ~50 tokens
      review_impact: 3       # ~100 tokens
      debug_refactor: 4      # ~200 tokens
      deep_modification: 5   # ~300+ tokens

  post_task:
    action: "sync_incremental to update graph"
    benefit: "living documentation, zero context rot"

  metrics:
    token_savings: "72-77%"
    accuracy: "92%+"
    nodes_supported: "82K+"
    edges_supported: "190K+"
```

## Multi-Model Review Loop

```yaml
review_loop:
  trigger: "code-reviewer score < 90 OR security findings"

  round_1:
    model: "primary (Claude)"
    action: "full review with all active skills"
    output: "findings + score"

  round_2:
    condition: "score < 90 OR critical findings"
    models:
      - "secondary review (configurable)"
    action: "parallel review, merge findings"
    output: "consolidated findings"

  round_3:
    condition: "conflicting findings between models"
    action: "resolution review with primary model"
    output: "final verdict"

  max_rounds: 3
  quality_gate:
    pass: "score >= 90, no critical/high findings"
    conditional: "score 70-89, only minor findings"
    fail: "score < 70 OR any critical finding"
```

## Error Amplification Control

Multi-agent chains amplify errors. Based on findings from multi-agent scaling research (2025), v6.0 mitigates this:

```yaml
error_control:
  problem: "N agents in chain can amplify errors significantly"
  reference: "Based on multi-agent scaling research (2025)"

  mitigations:
    checkpoint_validation:
      description: "Validate output at each layer boundary"
      frequency: "every 2 skills"

    rollback_capability:
      description: "Revert to last checkpoint on failure"
      max_rollbacks: 2

    confidence_threshold:
      minimum: 0.8
      action_below: "escalate to human review"

    saturation_monitoring:
      threshold: "45% of skill chain"
      action: "stop adding agents, consolidate"

  result: "error amplification limited to 4.4x"
```

## 4-Stage Maturity Model

```yaml
level_1_mvp:
  goal: "Ship fast, prove concept"
  active_skills:
    - context-architect
    - requirements-analyzer
    - project-architect
    - tech-stack-advisor
  quality: "relaxed (speed priority)"
  deploy: "Vercel/Netlify, Supabase"

level_2_stable:
  goal: "Tested, reliable, maintainable"
  add_skills:
    - clean-code-mastery
    - code-smell-detector
    - tdd-guardian
    - security-shield
    - code-reviewer
    - dependency-sentinel
  quality: "standard (80% coverage, no critical smells)"
  deploy: "same + CI/CD pipeline"

level_3_scalable:
  goal: "Scale-ready architecture"
  add_skills:
    - impact-analyzer
    - codebase-graph
    - smart-context
    - monorepo-architect
    - arch-visualizer
    - production-scale-launcher
  quality: "strict (90% coverage, full security audit)"
  deploy: "AWS/GCP via SST/CDK"

level_4_enterprise:
  goal: "Compliance, security, observability"
  enhance_skills:
    - security-shield: "FULL (OWASP + SAST + DAST)"
    - arch-visualizer: "auto-generate architecture docs"
  quality: "enterprise (95% coverage, SOC2/GDPR ready)"
  deploy: "multi-region, zero-downtime"
```

## Task-Type Workflows

```yaml
workflows:
  new_feature:
    chain: "context → requirements → architect → [clean-code + security] → tdd → smell → review"
    parallel: "[clean-code, security]"

  bug_fix:
    chain: "smart-context → tdd(reproduce) → [clean-code + security] → tdd(verify) → review"
    parallel: "[clean-code, security]"

  refactoring:
    chain: "codebase-graph → impact-analyzer → tdd(baseline) → [clean-code + smell] → tdd(verify) → review"
    parallel: "[clean-code, smell]"

  api_change:
    chain: "api-first → codebase-graph → impact → [security + tdd] → review"
    parallel: "[security, tdd]"

  security_patch:
    chain: "security-shield(FULL) → impact → tdd → code-reviewer"
    blocking: "security-shield"
    priority: "critical"

  dependency_update:
    chain: "dependency-sentinel → impact-analyzer → tdd → review"
    blocking: "dependency-sentinel"
```

## Quick Commands

> These are **conversation triggers** — type them in your Claude Code session (not terminal CLI commands).

| Command | Action | Skills Invoked |
|---------|--------|---------------|
| `vibe init` | New project setup | context + requirements + architect + stack |
| `vibe code` | Write code | clean-code + naming + smell + security |
| `vibe review` | Code review | all quality + integration skills |
| `vibe test` | Test analysis | tdd-guardian + coverage check |
| `vibe secure` | Security scan | security-shield (basic/owasp/full) |
| `vibe arch` | Architecture check | codebase-graph + arch-visualizer |
| `vibe impact` | Change impact | impact-analyzer + codebase-graph |
| `vibe pipeline` | Full pipeline | all 7 stages sequentially |
| `vibe launch` | Production check | production-scale-launcher |
| `vibe deps` | Dependency health | dependency-sentinel |
| `vibe context` | Setup context files | context-architect |

## Cross-Tool Compatibility

```yaml
compatibility:
  native:
    claude_code: "SKILL.md (this file)"
    codex: "auto-generates AGENTS.md"
    gemini_cli: "auto-generates AGENTS.md"

  adaptable:
    cursor: "exports to .cursor/rules"
    windsurf: "exports to .windsurfrules"
    copilot: "exports to .github/copilot-instructions.md"

  export_command: "vibe export --target cursor|windsurf|copilot"
```

## Configuration

```yaml
# .vibeconfig.yml
global:
  language: "typescript"
  framework: ["react", "nestjs"]
  maturity: 2  # 1=MVP, 2=Stable, 3=Scalable, 4=Enterprise
  strictMode: true
  autoFix: false

kg:
  enabled: true
  context_level: 3
  auto_sync: true

review:
  multi_model: false  # enable for parallel AI review
  max_rounds: 3
  quality_gate: 90

pipeline:
  stages: ["lint", "type-check", "unit-test", "security-scan", "code-quality"]
  failFast: true
  parallel: true

skills:
  clean-code-mastery:
    strictness: "standard"  # relaxed | standard | strict
  security-shield:
    level: "owasp"  # basic | owasp | full
  tdd-guardian:
    coverage_threshold: 80
```

## File Structure

```
vibe-coding-orchestrator/
├── SKILL.md                              # This file
├── core/
│   ├── context-detection.md              # File/content/task type detection
│   └── skill-registry.md                 # Skill definitions + dependencies
├── pipeline/
│   ├── pre-commit.md                     # Pre-commit checks
│   └── quality-pipeline.md               # 7-stage quality pipeline
├── workflow/
│   ├── auto-activation.md                # Trigger rules
│   └── standard-workflow.md              # 5-phase workflow
├── templates/
│   └── orchestration-template.md         # Orchestration templates
└── quick-reference/
    ├── commands.md                        # Quick command reference
    └── config.md                          # Configuration reference
```

---

**Version**: 6.0.0 | **Skills**: 2 included + 16 compatible | **Layers**: 9 | **Updated**: 2026-03-01
**Philosophy**: Context Architecture > Prompt Engineering
**Compatibility**: Claude Code, Codex, Gemini CLI, Cursor, Windsurf
