---
name: opencode-mcp-delegate
description: |
  Use when an AI coding agent (Codex, Claude Code, etc.) needs to delegate
  coding or review tasks to OpenCode via the opencode-mcp MCP server.
  Trigger on requests to use opencode MCP tools, run long background jobs,
  continue OpenCode sessions, or avoid direct bash `opencode run`.
  Prefer workflow tools (`opencode_ask/run/fire/check/wait`) and enforce
  provider/model plus enabled-tools constraints from local MCP config.
---

# OpenCode MCP Delegation

Delegate work through `opencode-mcp` so OpenCode executes independently and
returns compact structured results.

## Mandatory Rules

1. Start with `opencode_setup` once per thread/session.
2. Always pass `providerID` and `modelID` on `opencode_ask`, `opencode_reply`, `opencode_run`, and `opencode_fire`.
3. Prefer workflow tools over low-level session/message tools.
4. Respect enabled tools from local MCP config before planning tool calls.
5. Pass `directory` whenever the target project is not the current working directory.

Without rule #2, OpenCode may pick a default model and return empty or unstable responses.

## Tool Profile First

Before choosing tools, read enabled tools from project config:

`<project>/.codex/config.toml` → `[mcp_servers.opencode].enabled_tools`

If a documented tool is unavailable, use fallback routes in this skill and do not call unsupported tools.

## Decision Tree (Use In Order)

1. Quick analysis or one-round Q&A: `opencode_ask`.
2. Code changes likely under 10 minutes: `opencode_run`.
3. Long or uncertain runtime: `opencode_fire` → `opencode_check` → optional `opencode_wait` → `opencode_review_changes`.
4. Continue an existing session:
   - If `opencode_reply` is enabled: use `opencode_reply`.
   - If `opencode_reply` is not enabled: use `opencode_run` or `opencode_fire` with `sessionId`.
5. Low-cost progress checks: `opencode_check`.
6. Final acceptance on file changes: `opencode_review_changes`.
7. Full transcript only when needed: `opencode_conversation` after completion (expensive).

## Canonical Workflows

### Quick Question

```json
opencode_ask({
  "prompt": "Analyze auth architecture and list risks",
  "providerID": "zhipuai-coding-plan",
  "modelID": "glm-5.1"
})
```

### Execute And Wait (<10 min)

```json
opencode_run({
  "prompt": "Add unit tests for calculatePrice() and fix failing cases",
  "providerID": "zhipuai-coding-plan",
  "modelID": "glm-5.1",
  "maxDurationSeconds": 1800
})
```

### Long Task Async (Recommended)

```json
opencode_fire({
  "prompt": "Refactor duplicated utils and keep behavior unchanged",
  "providerID": "zhipuai-coding-plan",
  "modelID": "glm-5.1"
})

opencode_check({ "sessionId": "ses_xxx" })
opencode_wait({ "sessionId": "ses_xxx", "timeoutSeconds": 1800 })
opencode_review_changes({ "sessionId": "ses_xxx" })
```

Recommended baseline for this project:
- Use `opencode_run` with `maxDurationSeconds: 1800`.
- Use `opencode_wait` with `timeoutSeconds: 1800`.
- Keep MCP `tool_timeout_sec` at least `3600` to avoid parent timeout preempting child task completion.

## Prompting Standard

1. State stack and relevant modules.
2. List requirements as bullets.
3. State constraints (no API breaks, no behavior regressions, etc.).
4. Require verification (build/lint/test) and fix failures.
5. Request concise final report and changed files summary.

## Error Recovery

1. Connection issue: `opencode_setup`, then `opencode_status`.
2. Provider uncertainty: `opencode_provider_test` (or re-check setup output if provider tools are disabled).
3. Timeout or `fetch failed`: use async mode (`opencode_fire` + `opencode_check`).
4. Stuck session: `opencode_session_abort` if enabled, then retry with a tighter prompt.

## Pitfalls To Avoid

1. Do not call `opencode_conversation` repeatedly on active sessions.
2. Do not open a new session for every follow-up when continuation is available.
3. Do not omit `directory` in multi-project work.
4. Do not run bash `opencode run` for tasks that MCP tools can handle.
5. Do not omit `providerID` and `modelID`.
