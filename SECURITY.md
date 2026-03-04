# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.0.x   | Yes       |
| < 2.0   | No        |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT** open a public GitHub issue
2. Use [GitHub Security Advisories](https://github.com/elon-choo/vibecodeallinone/security/advisories/new) to report privately
3. We aim to acknowledge reports within 48 hours

## Security Measures

- All API keys and secrets belong in `~/.claude/power-pack.env` (gitignored)
- `.gitleaks.toml` configured for pre-commit secret scanning
- No stdout output in MCP server pipeline (protects JSON-RPC stream integrity)
- Embedding provider locked to single dimension (no cross-dimension fallback)
- Dependencies audited for known CVEs via `pip-audit`
