# Repository Autopilot Round — Quality-Gate Recovery

You are running one unattended repository autopilot round inside the `[[REPO_NAME]]` repository.

Read these files first, in order:
- `AGENTS.md` if it exists
- `docs/status/autopilot-master-plan.md`
- `docs/status/autopilot-round-roadmap.md`
- `docs/status/autopilot-lane-map.md`
- `{{last_phase_doc}}`

Mission:
- Continue the quality-gate recovery program until the queued validation hotspot is under control.
- Execute exactly one queued slice: the first item marked `[NEXT]` in `docs/status/autopilot-round-roadmap.md`.
- Do not freestyle outside the queue.
- Do not start another round.

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

Configured validation commands:
- Lint: `{{lint_command}}`
- Typecheck: `{{typecheck_command}}`
- Full test: `{{full_test_command}}`
- Build: `{{build_command}}`

Required workflow:
1. Use the plan tool before making substantive changes.
2. Read the current `[NEXT]` queue item and restate the failing or noisy gate, the target scope, and the stop condition in your plan.
3. Start from the queue entrypoints and validation baseline before broad searching.
4. Fix only the queued hotspot or its direct support files.
5. Prefer restoring green gates with the smallest behavior-preserving change.
6. Do not delete assertions, lower coverage, or silence warnings without justification.
7. Run targeted tests first when relevant and then every configured validation command that is present.
8. When a validation command is blank, do not invent one; record the gap in the phase doc.
9. Update `docs/status/autopilot-round-roadmap.md` on success: mark the executed `[NEXT]` item as `[DONE]`, promote the next `[QUEUED]` item to `[NEXT]`, and keep later items `[QUEUED]`.
10. Write the round summary to `{{next_phase_doc}}`. Include the recovered gate, changed files, validation results, and the next recommended slice.
11. Commit successful rounds as `{{commit_prefix}}: round {{round_attempt}} - <short subject>`.
12. If validation still fails after one focused repair, revert the round, do not commit, and return `failure`.
13. If the queued objective is already complete, avoid unnecessary edits, update the roadmap accordingly, and return `goal_complete`.

Response contract:
- Your final response must be valid JSON matching the provided output schema.
- Use actual repo-relative paths in `phase_doc_path` and `changed_files`.
- Set `status` to one of `success`, `failure`, or `goal_complete`.
- On `success`, `commit_sha` and `commit_message` must be non-null.
- On `failure`, `blocking_reason` must explain why the round stopped.
- Include every command you ran in `commands_run`, and list the validation commands in `tests_run`.
