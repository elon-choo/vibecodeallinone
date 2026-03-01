# Vibe Coding Orchestrator - Beginner's Guide

> **Version**: 6.0.0 | **Date**: 2026-03-01

## What Is This?

Think of an **orchestra conductor**. The conductor doesn't play any instrument -- they coordinate 18 musicians so they play in harmony. The Vibe Coding Orchestrator does the same thing for AI coding skills.

Without orchestration, multiple skills might:
- Give conflicting advice
- Run in the wrong order
- Miss important checks
- Waste tokens on redundant analysis

The orchestrator solves this by **detecting what you're doing** and **activating the right skills in the right order**.

## What's Included?

This package includes **2 skills**:

| Skill | What It Does |
|-------|-------------|
| **clean-code-mastery** | Enforces SOLID, DRY, KISS principles + OWASP security patterns |
| **vibe-coding-orchestrator** | Coordinates all available skills with dependency-aware execution |

The orchestrator can also coordinate **16 additional skills** when you install them separately. See `core/skill-registry.md` for the full list.

## How It Works

### 1. You Write Code

Just write code normally in Claude Code. The orchestrator watches for relevant file types and keywords.

### 2. Automatic Skill Selection

Based on what you're doing, the orchestrator picks the right skills:

| Your Activity | Skills Activated |
|--------------|------------------|
| Writing new code | clean-code-mastery, naming-convention-guard (if installed) |
| Fixing a bug | smart-context (if installed), clean-code-mastery |
| Security-related work | security-shield (if installed), clean-code-mastery |
| Code review | All quality skills available |

### 3. Ordered Execution

Skills run in dependency order -- foundation skills first, then quality checks, then final review.

### 4. Unified Report

You get a single report with findings prioritized by severity:

| Priority | Meaning |
|----------|---------|
| **Critical** | Must fix -- security vulnerability or data loss risk |
| **High** | Should fix -- bug potential or significant code smell |
| **Medium** | Nice to fix -- code quality improvement |
| **Low** | Optional -- style or convention suggestion |

## Quick Start

### Installation

```bash
# Copy skills to your Claude Code skills directory
cp -r skills/clean-code-mastery ~/.claude/skills/
cp -r skills/vibe-coding-orchestrator ~/.claude/skills/
```

### First Use

In your Claude Code session, try:

```
"vibe review src/app.ts"
```

This triggers a full review using all available skills.

### Conversation Triggers

> **Important**: These are phrases you type in Claude Code chat, NOT terminal commands.

| Trigger | What It Does |
|---------|-------------|
| `vibe init` | Set up a new project with structure + stack selection |
| `vibe code` | Write code with quality checks |
| `vibe review` | Full code review |
| `vibe test` | Test analysis and coverage check |
| `vibe secure` | Security scan |
| `vibe pipeline` | Run all quality stages |
| `vibe launch` | Production readiness check |

## The 4-Stage Maturity Model

The orchestrator adjusts its behavior based on your project's maturity:

### Level 1: MVP
- **Goal**: Ship fast, prove the concept
- **Active Skills**: Planning only (project-architect, tech-stack-advisor)
- **Quality**: Relaxed -- speed is priority

### Level 2: Stable
- **Goal**: Tested, reliable, maintainable
- **Active Skills**: + Quality skills (clean-code, tests, security, review)
- **Quality**: Standard -- 80% test coverage, no critical smells

### Level 3: Scalable
- **Goal**: Scale-ready architecture
- **Active Skills**: + Analysis and structure skills
- **Quality**: Strict -- 90% coverage, full security audit

### Level 4: Enterprise
- **Goal**: Compliance, security, observability
- **Active Skills**: All skills enhanced
- **Quality**: Enterprise -- 95% coverage, SOC2/GDPR ready

## Configuration

Create a `.vibeconfig.yml` in your project root:

```yaml
global:
  language: "typescript"
  maturity: 2  # 1=MVP, 2=Stable, 3=Scalable, 4=Enterprise

skills:
  clean-code-mastery:
    strictness: "standard"  # relaxed | standard | strict
```

## FAQ

**Q: Do I need all 18 skills?**
A: No. The package includes 2 skills and works great with just those. Additional skills enhance the experience when installed.

**Q: Does this work with other AI tools besides Claude Code?**
A: The skills follow the Agent Skills open standard and are compatible with Codex CLI, Gemini CLI, and adaptable to Cursor, Windsurf, and GitHub Copilot.

**Q: What languages are supported?**
A: clean-code-mastery supports TypeScript, Python, Go, Rust, Java, C++, C#, and Kotlin with language-specific patterns and security guidance.

---

*Also available in Korean: [GUIDE_FOR_BEGINNERS_KO.md](./GUIDE_FOR_BEGINNERS_KO.md)*
