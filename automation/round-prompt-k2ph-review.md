# Repository Autopilot Round — Knowledge Handout Page Review

You are running one unattended repository autopilot round inside the `my-skills` repository.

Read these files first, in order:
- `AGENTS.md` if it exists
- `custom/knowledge-to-print-html/SKILL.md`
- `custom/knowledge-to-print-html/references/review-loop.md`
- `custom/knowledge-to-print-html/references/layout-guardrails.md`
- `custom/knowledge-to-print-html/references/diagram-guardrails.md`
- `docs/status/autopilot-k2ph-review-master-plan.md`
- `docs/status/autopilot-k2ph-review-round-roadmap.md`
- `{{last_phase_doc}}`

Target artifact:
- `custom/knowledge-to-print-html/artifacts/knowledge-handout/igcse-0620-preparation-of-salts/handout.html`

Mission:
- Continue the sequential page-review program one queued page at a time.
- Execute exactly one queued slice: the first item marked `[NEXT]` in `docs/status/autopilot-k2ph-review-round-roadmap.md`.
- Do not freestyle outside pages 4-6.
- Do not start another round manually.

Round metadata:
- Attempt number: `{{round_attempt}}`
- Next phase number: `{{next_phase_number}}`
- New phase doc path: `{{next_phase_doc}}`
- Current branch: `{{current_branch}}`
- Last successful phase doc: `{{last_phase_doc}}`
- Last commit: `{{last_commit_sha}}`
- Previous summary: `{{last_summary}}`
- Focus hint: `{{focus_hint}}`
- Objective: `{{objective}}`
- Platform note: `{{platform_note}}`
- Runner kind: `{{runner_kind}}`
- Runner model: `{{runner_model}}`

Required workflow:
1. Use the plan tool before making substantive changes.
2. Restate the current `[NEXT]` page slice, page number, and pass target in the plan.
3. Regenerate the review packet before editing:
   - `python3 custom/knowledge-to-print-html/review_print_pages.py --html custom/knowledge-to-print-html/artifacts/knowledge-handout/igcse-0620-preparation-of-salts/handout.html`
4. Read the current page packet from `custom/knowledge-to-print-html/artifacts/knowledge-handout/igcse-0620-preparation-of-salts/screens/py-latest/page-review/page-XX-review.json`.
5. If `page-XX-subagent-prompt.md` exists and delegation tools are available, use a fresh subagent for page review. If delegation is unavailable, emulate the same structured review contract yourself and explicitly record that limitation in the phase doc.
6. Fix only the current page and the minimum adjacent layout needed to keep pagination stable.
7. Rerun `review_print_pages.py` after edits and judge only the current queued page for completion.
8. If the current page still needs work but you made bounded progress, leave the same queue item as `[NEXT]`, write the phase doc, and return `success` with a commit.
9. If the current page now passes, mark it `[DONE]`, promote the next `[QUEUED]` item to `[NEXT]` if one exists, write the phase doc, and return `goal_complete`.
10. If you are blocked after one focused repair attempt, revert the round, do not commit, and return `failure`.
11. The handout and review artifacts live under an ignored path. Edit them in place anyway, but commit only tracked queue/docs/config changes. Record every edited ignored artifact path in the phase doc.
12. Do not add new queue items beyond pages 4-6.

Validation commands:
- Primary validation: rerun `python3 custom/knowledge-to-print-html/review_print_pages.py --html custom/knowledge-to-print-html/artifacts/knowledge-handout/igcse-0620-preparation-of-salts/handout.html`
- Optional spot checks: inspect the current page screenshot and packet JSON for the queued page only.
- Do not invent lint/typecheck/test/build commands; there are none configured for this lane.

Phase doc requirements:
- Current queued page and whether it passed this round
- Exact edited files, including ignored artifact paths
- Whether delegation/subagent review was available
- Current page heuristic outcome before and after the edit
- Any remaining issue types on the current page
- The next page or next retry target

Response contract:
- Your final response must be valid JSON matching the provided output schema.
- Use actual repo-relative paths in `phase_doc_path` and `changed_files`.
- Set `status` to one of `success`, `failure`, or `goal_complete`.
- On `success`, `commit_sha` and `commit_message` must be non-null.
- On `goal_complete`, include `commit_sha` and `commit_message` if you created a bookkeeping commit; otherwise set them null.
- On `failure`, `blocking_reason` must explain why the round stopped.
- Include every command you ran in `commands_run`, and list the review command in `tests_run`.
