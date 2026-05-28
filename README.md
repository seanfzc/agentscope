# AgentScope

**AI Agent Permissions, Without the Pain.**

Stop approving every command. AgentScope gives your AI agents task-based authorization — approve the mission, not every mouse click.

## Problem

Current AI coding agents (Claude Code, Codex, Cursor, OpenCode) have broken permission models:
- **YOLO mode**: Approve everything. One rogue command can nuke your database.
- **Permission fatigue**: Approve each action. You stop reading after the 20th prompt.
- **No middle ground**: Binary approve/deny with no concept of scope or risk.

## Solution

AgentScope introduces **task-based authorization**:

1. **Define the task** — tell AgentScope what you're building
2. **Auto-approve safe actions** — reads, searches, local edits, tests run without prompts
3. **Flag risky actions** — git push, deploy, env access get flagged for review
4. **Deny dangerous actions** — database drops, credential access blocked by default

## Quick Start

```bash
# Install
pip install agentscope
# or
npm install -g agentscope

# Initialize
agentscope init "Add payment flow to checkout"

# Run with auto-approval
agentscope run "Add payment flow to checkout"

# Check status
agentscope status
```

## How Risk Classification Works

| Risk Level | Actions | Default |
|-----------|---------|---------|
| 🟢 Low | Read, search, list, status | Auto-approve |
| 🟡 Medium | Edit, write, create, test | Auto-approve (configurable) |
| 🟠 High | Push, deploy, publish, env vars | Flag for review |
| 🔴 Critical | Database, auth, credentials, root | Deny |

## Configuration

AgentScope stores config in `~/.agentscope/config.json`:

```json
{
  "auto_approve_medium": true,
  "auto_approve_high": false,
  "blocked_patterns": [],
  "sessions": 12
}
```

## Pricing

- **Solo** (Free): Local CLI, unlimited tasks, basic risk detection
- **Team** ($19/mo): Shared policies, team audit log, custom rules, MCP integration
- **Enterprise** (Custom): SSO, compliance rules, on-prem, SLA

## Status

- [x] CLI prototype v0.1.0
- [x] Risk classification engine
- [x] Session logging
- [ ] MCP server integration
- [ ] Web dashboard
- [ ] Team features
- [ ] IDE plugins (VS Code, JetBrains)

## License

MIT

---

Built by [Kepler](https://github.com/seanfzc) — the revenue-hunting AI agent.
