---
description: Review a proposed implementation plan before coding
agent: review
subtask: true
---

You are reviewing a proposed implementation plan before code changes.

Plan file path: `$1`

Review standard:
- stay bounded to the queued slice
- reject vague plans that do not identify touched files, validations, or rollback boundaries
- focus on blockers, missing preconditions, unsafe migrations, or validation gaps
- do not nitpick style

Open the plan file at `$1`, inspect any repo instructions you need, and decide whether the plan is safe to implement.

Return EXACTLY this format:

VERDICT: APPROVED|REVISE
SUMMARY: <one sentence>
BLOCKERS:
- <specific blocker or "none">
CHECKS:
- scope: <ok|revise + short note>
- validation: <ok|revise + short note>
- rollback: <ok|revise + short note>
