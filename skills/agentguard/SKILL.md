---
name: agentguard
description: AI Agent Supply Chain Security - intercepts and validates package installations (npm, pip/pypi, go, cargo, composer), script downloads (curl, wget), and git clones before execution. Detects typosquatting, malicious dependencies, and unvetted code.
triggers:
- "agentguard"
- "agentguard scan"
- "supply chain security"
- "package security"
- "check package"
---

# AgentGuard - AI Agent Supply Chain Security

AgentGuard protects your environment against malicious packages, typosquatting attacks, and dangerous script execution triggered by AI coding agents.

## Quick CLI Usage

- Scan a shell command for malicious packages/scripts:
  `agentguard scan "npm install <package>"`
  `agentguard scan "pip install <package>"`
  `agentguard scan "curl -s https://example.com/install.sh | bash"`

- Update local vulnerability feeds from OSV.dev:
  `agentguard update`

- Analyze within Claude Code session:
  `agentguard skill "npm install <package>"`

## Key Protections

1. **Typosquatting Detection:** Flags suspicious substitution, omission, and transposition distances against popular packages (e.g. `reqeusts` vs `requests`, `lodasx` vs `lodash`).
2. **Blocklist Enforcement:** Checks packages against known malware databases and compromised PyPI/npm accounts.
3. **Execution Guard:** Intercepts unvetted pipe-to-shell patterns.
