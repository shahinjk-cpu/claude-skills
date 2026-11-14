---
name: swarmchat
description: >
  Multi-agent swarm collaboration protocol. Orchestrates decentralized agent swarms with shared message boards, role delegation, voting consensus, and structured handoffs.
metadata:
  version: "1.0.0"
  category: ai_ml
  triggers: swarmchat, multi agent swarm, agent collaboration, swarm protocol, consensus
---

# SwarmChat — Multi-Agent Swarm Orchestration

Coordinates multi-agent swarms using asynchronous shared message boards, peer-to-peer delegation, role arbitration, and consensus protocols.

## Swarm Lifecycle
1. **Roster Initialization**: Coordinator spawns specialized agents (Architect, Author, Reviewer, QA).
2. **Public Message Board**: All agents read and post to a shared transparent ledger.
3. **Turn Arbitration**: Agents take turns based on @mentions, work state, or priority interrupts.
4. **Consensus & Landing**: Work is verified by peer consensus before merging into the main branch.

## Tool Commands
```bash
# Antigravity native swarm orchestration
swarm action="status"
swarm action="add" name="coder" brief="Implement the auth module"
swarm action="add" name="reviewer" brief="Review coder's implementation against security guidelines"
```
