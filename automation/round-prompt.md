# Repository Autopilot Round — Bugfix / Backlog

You are running one unattended repository autopilot round inside the `my-skills` repository.

Read these files first, in order:
- `AGENTS.md` if it exists
- `docs/status/autopilot-master-plan.md`
- `docs/status/autopilot-lane-map.md`
- `{{current_lane_roadmap}}`
- `{{last_phase_doc}}`

Mission:
- Continue the bugfix / backlog program one active lane at a time.
- Treat root-level legacy `docs/status/autopilot-phase-*.md` files as historical carry-over only; the live queue truth now lives under `docs/status/lanes/*`.
- Stay inside lane `{{current_lane_id}}` (`{{current_lane_label}}`).
- Execute exactly one queued slice: the first item marked `[NEXT]` in `{{current_lane_roadmap}}`.
- Do not freestyle outside the queue.
- Do not start another round.

Round metadata:
- Active lane id: `{{current_lane_id}}`
- Active lane label: `{{current_lane_label}}`
- Active lane roadmap: `{{current_lane_roadmap}}`
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
- Vulture: `{{vulture_command}}`

Required workflow:
1. Use the plan tool before making substantive changes.
2. Read the current `[NEXT]` item and restate the exact bug or backlog slice, scope, and validation target in your plan.
3. Start from the queue entrypoints and direct reproductions before broad searching.
4. Fix only the queued slice and its direct support code.
5. Prefer reproducible, behavior-preserving fixes over broad cleanup.
6. Run targeted tests first when relevant and then every configured validation command that is present.
7. When a validation command is blank, do not invent one; record the gap in the phase doc.
8. When Vulture is configured, use it as the dead-code observability command only when the queued slice touches cleanup or unused-code risk; record the finding count or any gap in the phase doc.
9. Update `{{current_lane_roadmap}}` on success: mark the executed `[NEXT]` item as `[DONE]`, promote the next `[QUEUED]` item to `[NEXT]`, and keep later items `[QUEUED]`.
10. Write the round summary to `{{next_phase_doc}}`. Include scope, changed files, validation results, Vulture findings when configured, and the next recommended slice.
11. Commit successful rounds as `{{commit_prefix}}: round {{round_attempt}} - <short subject>`.
12. If validation fails after one focused repair, revert the round, do not commit, and return `failure`.
13. If the queued objective is already complete, avoid unnecessary edits, update the lane roadmap accordingly, and return `goal_complete`.

Response contract:
- Your final response must be valid JSON matching the provided output schema.
- Set `lane_id` to `{{current_lane_id}}`.
- Use actual repo-relative paths in `phase_doc_path` and `changed_files`.
- Set `status` to one of `success`, `failure`, or `goal_complete`.
- On `success`, `commit_sha` and `commit_message` must be non-null.
- On `failure`, `blocking_reason` must explain why the round stopped.
- Include every command you ran in `commands_run`, and list the validation commands in `tests_run`.
