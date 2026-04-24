---
description: Review current uncommitted changes for review-gated autopilot
agent: review
subtask: true
---

You are reviewing the current uncommitted changes for a review-gated autopilot round.

Focus argument: `$ARGUMENTS`

Review standard:
- prioritize correctness, safety, and whether the implementation still matches the queued slice
- read the full changed files, not only the diff
- reject changes that skipped required validation, widened scope, or introduced obvious regressions
- do not spend the review on style-only comments

Use git diff / git status / full-file reads as needed. If `$ARGUMENTS` is empty, review the current uncommitted changes.

Return EXACTLY this format:

VERDICT: APPROVED|REVISE
SUMMARY: <one sentence>
BLOCKERS:
- <specific blocker or "none">
CHANGED_FILES:
- <repo-relative path>
