---
name: clean-code-mastery
description: "Proactive Code Guardian that enforces SOLID/DRY/KISS principles and OWASP security patterns. Use when writing code, reviewing pull requests, refactoring, or performing security audits on TypeScript, Python, Go, Rust, Java, C++, C#, or Kotlin files. Activates on code quality, clean code, or security review requests."
license: MIT
compatibility: "Claude Code, Codex CLI, Gemini CLI. Adaptable to Cursor, Windsurf, GitHub Copilot."
metadata:
  version: "4.0.0"
  author: "elon-opensource"
  languages: 8
allowed-tools: Read Glob Grep Agent Skill
---

# Clean Code Mastery v4.0

**Proactive Code Guardian** — Auto-activates on code files. Enforces Clean Code + Secure Coding with Knowledge Graph-powered context and multi-model review.

## What's New in v4.0

- **Knowledge Graph Integration**: Leverages codebase-graph for dependency-aware reviews (72% token savings, 92% accuracy)
- **Cross-Tool Compatibility**: Works with Claude Code, Codex, Gemini CLI, Cursor, Windsurf via Agent Skills open standard
- **Multi-Model Review Loop**: Routes critical findings through parallel AI review (configurable)
- **Result Type Pattern**: Language-agnostic error handling via discriminated unions
- **2026 Tooling**: Biome 2.0, Oxlint 1.x, ESLint 9 flat config, Vitest 3.x
- **Scoring v2**: 100-point scale with weighted security emphasis

## Auto-Activation

```yaml
triggers:
  file_extensions:
    - ".ts, .tsx, .js, .jsx"   # TypeScript/JavaScript
    - ".py"                     # Python
    - ".go"                     # Go
    - ".rs"                     # Rust
    - ".java"                   # Java
    - ".cpp, .cc, .h, .hpp"    # C++
    - ".cs"                     # C#
    - ".kt, .kts"              # Kotlin

  keywords:
    - "code review", "코드 리뷰"
    - "refactor", "리팩토링"
    - "clean code", "클린 코드"
    - "code quality", "코드 품질"
    - "security review", "보안 검토"

  actions:
    - Write/Edit tool on code files
    - Code analysis requests
    - PR review requests

  content_patterns:
    critical_security:
      - "eval(", "innerHTML", "dangerouslySetInnerHTML"
      - "exec(", "spawn(", "child_process"
      - "password", "secret", "token", "api_key"
    injection_risk:
      - "string concatenation in SQL"
      - "template literal in query"
      - "f-string in SQL"
```

## Selective Document Loading

**Loads only what's needed** — not the entire corpus:

```yaml
loading_strategy:
  step_1_detect_language:
    method: "file extension + syntax detection"
    fallback: "ask user"

  step_2_load_required:
    always_load:
      - "core/principles.md"         # SOLID, DRY, KISS, YAGNI
      - "core/security.md"           # OWASP Top 10

    language_specific:
      TypeScript:  "languages/typescript.md"
      Python:      "languages/python.md"
      Go:          "languages/go.md"
      Rust:        "languages/rust.md"
      Java:        "languages/java.md"
      CPP:         "languages/cpp.md"
      CSharp:      "languages/csharp.md"
      Kotlin:      "languages/kotlin.md"
    context_specific:
      code_review:    "contexts/review-checklist.md"
      refactoring:    "contexts/refactoring-patterns.md"
      # security-audit context is provided by security-shield skill

  step_3_knowledge_graph:
    condition: "when codebase-graph skill is available"
    action: "query dependency graph for affected modules"
    benefit: "dependency-aware reviews catch cross-module impacts"
```

## Knowledge Graph Integration

When codebase-graph is available, clean-code-mastery uses it for:

```yaml
kg_integration:
  pre_review:
    - "Query call graph for function under review"
    - "Identify callers and callees (impact radius)"
    - "Check for circular dependencies"
    - "Get complexity metrics from graph"

  during_review:
    - "Cross-reference naming with project conventions"
    - "Validate import patterns against architecture"
    - "Check for duplicate implementations via similarity search"

  post_review:
    - "Update graph with new patterns found"
    - "Log quality metrics to graph nodes"
    - "Track technical debt accumulation"

  token_savings:
    without_kg: "~4200 tokens per review context"
    with_kg: "~980 tokens (smart context level 3)"
    reduction: "77%"

  fallback_without_kg:
    action: "proceed with standard file-based context"
    token_usage: "standard (~4200 tokens per review)"
    note: "KG is optional - skill works fully without it"
```

## Scoring System v2 (100 points)

| Category | Item | Points |
|----------|------|--------|
| **Readability** (15) | Naming conventions | 8 |
| | Function size (≤20 lines) + complexity (≤10) | 7 |
| **Structure** (25) | SOLID compliance | 10 |
| | DRY (no duplication) | 8 |
| | Error handling patterns | 7 |
| **Quality** (20) | Code smell free | 8 |
| | Language idioms | 7 |
| | Test coverage (≥80%) | 5 |
| **Security** (40) | Input validation | 10 |
| | Output encoding | 5 |
| | Injection prevention | 10 |
| | Secret management | 5 |
| | Auth/session security | 10 |

### Grade Scale

| Score | Grade | Verdict |
|-------|-------|---------|
| 90-100 | A | Production-ready |
| 80-89 | B | Acceptable with minor fixes |
| 70-79 | C | Needs improvement |
| <70 | D | Significant rework required |

## 2026 Tooling Guide

```yaml
linting:
  biome_2:
    description: "All-in-one linter + formatter"
    speed: "15-20x faster than ESLint"
    typescript_coverage: "95%+ of typescript-eslint rules"
    recommended_for: "new projects, fast feedback"
    config: "biome.json"

  eslint_9:
    description: "Flat config, mature ecosystem"
    recommended_for: "enterprise, team projects, max type safety"
    config: "eslint.config.mjs"

  oxlint_1:
    description: "Rust-based ultra-fast linter"
    speed: "50-100x faster than ESLint"
    rules: "700+"
    recommended_for: "large codebases, CI speed"

  selection_guide:
    solo_new: "Biome 2"
    team_new: "ESLint 9 flat config"
    existing: "keep current, tighten gradually"
    ci_optimization: "Oxlint parallel"

testing:
  vitest_3: "Default for new projects (30-70% faster than Jest)"
  jest_30: "Stable choice for existing projects"
  playwright_2: "E2E testing standard"

formatting:
  biome: "Integrated with linting"
  prettier_4: "Standalone formatter, wide support"
  dprint: "Rust-based, Biome-compatible"
```

## Cross-Tool Compatibility

This skill follows the **Agent Skills Open Standard** and works with:

| Tool | Config File | Status |
|------|------------|--------|
| Claude Code | `SKILL.md` | Native |
| Codex | `AGENTS.md` | Compatible |
| Gemini CLI | `AGENTS.md` | Compatible |
| Cursor | `.cursor/rules` | Adaptable |
| Windsurf | `.windsurfrules` | Adaptable |
| GitHub Copilot | `.github/copilot-instructions.md` | Adaptable |

## File Structure

```
clean-code-mastery/
├── SKILL.md                         # This file (router + overview)
├── core/
│   ├── principles.md                # SOLID, DRY, KISS, YAGNI
│   └── security.md                  # OWASP Top 10 security patterns
├── languages/
│   ├── typescript.md                # TS/JS patterns + security
│   ├── python.md                    # Python patterns + security
│   ├── go.md                        # Go patterns + security
│   ├── rust.md                      # Rust patterns + security
│   ├── java.md                      # Java patterns + security
│   ├── cpp.md                       # C++ patterns + security
│   ├── csharp.md                    # C# patterns + security
│   └── kotlin.md                    # Kotlin patterns + security
├── contexts/
│   ├── review-checklist.md          # Code review checklist
│   └── refactoring-patterns.md      # Martin Fowler refactoring catalog
└── quick-reference/
    └── anti-patterns.md             # Anti-pattern catalog
```

## Integration with Other Skills

```yaml
skill_chain:
  planning:
    - project-architect → "structure first"
    - requirements-analyzer → "analyze requirements"
    - tech-stack-advisor → "select technology"

  development:
    - clean-code-mastery → "write clean code"
    - naming-convention-guard → "verify naming"
    - security-shield → "verify security"

  validation:
    - code-smell-detector → "detect smells"
    - tdd-guardian → "verify tests"
    - code-reviewer → "final review"

  knowledge:
    - codebase-graph → "dependency context"
    - smart-context → "token-efficient context"
    - impact-analyzer → "change impact"
```

## Quick Reference

### Clean Code Essentials
- **SRP**: One class/function = one responsibility
- **DRY**: No code duplication
- **KISS**: Keep it simple
- **Functions**: ≤20 lines, ≤3 parameters
- **Nesting**: ≤3 levels deep

### Security Essentials
- **Input Validation**: Validate all inputs (whitelist preferred)
- **Output Encoding**: Encode all outputs per context
- **Parameterized Queries**: Never concatenate SQL
- **No Secrets in Code**: Use environment variables
- **Least Privilege**: Minimal permissions always

---

**Version**: 4.0.0 | **Languages**: 8 | **Updated**: 2026-03-01
**Compatibility**: Claude Code, Codex, Gemini CLI, Cursor, Windsurf
