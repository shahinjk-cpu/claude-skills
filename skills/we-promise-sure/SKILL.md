---
name: we-promise-sure
description: >
  Self-hosted personal finance and net-worth tracking platform (community fork of Maybe Finance). Track assets, liabilities, transactions, investments, and budgets via Sure API.
metadata:
  version: "1.0.0"
  category: backend_api
  triggers: sure, we-promise sure, maybe finance, personal finance, budget tracker, net worth
---

# Sure (we-promise/sure) — Personal Finance Engine

Orchestrates personal finance analysis, balance reconciliation, transaction categorization, and net worth modeling using the open-source Sure platform.

## Key Capabilities
- **Account Aggregation**: Track bank balances, credit accounts, investments, and crypto wallets.
- **Transaction Classification**: Auto-tag and categorize expenses using rules or LLM classifications.
- **Net Worth Timeline**: Historical balance sheets and trend analytics.
- **LLM/MCP Connectivity**: Expose financial data securely to AI agents for budgeting advice and spending analysis.

## Setup & API Integration
```bash
docker run -d -p 3000:3000 --name sure ghcr.io/we-promise/sure:latest
```
