# Contributing to Claude Code Quality Kit

Thank you for your interest in contributing! This guide will help you get started.

## Ways to Contribute

### 1. Add a New Language
Create a new file in `skills/clean-code-mastery/languages/`:
- Follow the pattern of existing language files (e.g., `typescript.md`)
- Include: naming conventions, idioms, security patterns, error handling, testing, code smells
- Add the language to `SKILL.md` triggers and loading strategy

### 2. Create a Compatible Skill
The orchestrator can coordinate any skill that follows the [Agent Skills specification](https://code.claude.com/docs/en/skills):
- Create a `SKILL.md` with proper frontmatter (`name`, `description`, `allowed-tools`)
- Add your skill to the orchestrator's `core/skill-registry.md`
- Test that the orchestrator detects and coordinates your skill

### 3. Improve Documentation
- Fix typos or unclear explanations
- Add examples for under-documented features
- Translate guides to new languages

### 4. Report Issues
- Use GitHub Issues to report bugs or suggest improvements
- Include your environment (Claude Code version, OS, tools used)

## Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/add-ruby-support`
3. Make your changes
4. Run validation: `bash scripts/validate.sh`
5. Submit a Pull Request

## Skill File Standards

Every SKILL.md must include:
```yaml
---
name: skill-name
description: "What it does and when to use it. Include trigger keywords."
license: MIT
allowed-tools: Read Glob Grep
---
```

## Code of Conduct

Be respectful, constructive, and helpful. We welcome contributors of all experience levels.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
