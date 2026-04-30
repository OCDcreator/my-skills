# Repository Autopilot Round — Maintainability / Refactor

You are running one unattended repository autopilot round inside the `[[REPO_NAME]]` repository.

Read these files first, in order:
- `AGENTS.md` if it exists
- `docs/status/autopilot-master-plan.md`
- `docs/status/autopilot-lane-map.md`
- `{{current_lane_roadmap}}`
- `{{last_phase_doc}}`

Mission:
- Continue the maintainability / refactor program one active lane at a time.
- Stay inside lane `{{current_lane_id}}` (`{{current_lane_label}}`).
- Execute exactly one queued refactor slice: the first item marked `[NEXT]` in `{{current_lane_roadmap}}`.
- Do not freestyle outside the queue.
- Do not start another round.

Execution contract:
- You may and should use repository tools, shell commands, file edits, tests, and commits throughout the round.
- The JSON schema constrains only your final terminal response. It does not forbid planning, tool use, edits, validation, or intermediate work.

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
2. Read the current `[NEXT]` lane item and restate its lane, goal, constraints, and acceptance criteria in your plan.
3. Start from the lane roadmap and lane-map entrypoints before broad searching.
4. Read only the code and docs needed for this one slice.
5. Make the smallest meaningful maintainability refactor that satisfies the lane item and preserves behavior.
6. Prefer reducing direct ownership and import/assembly surface over moving code into new thin wrappers.
7. Update only directly related docs when the module boundary materially changes.
8. Run targeted tests first when code or tests change and a targeted test command pattern is configured.
9. `[[VALIDATION_REQUIREMENT]]`
10. When a validation command is blank, do not invent a substitute; record the gap in the phase doc instead.
11. When Vulture is configured, use it as the dead-code observability command when ownership cleanup or unused code is relevant; record the finding count or any gap in the phase doc.
12. If the implementation path uses background tasks or detached sub-work, the main pass exit is not completion. Wait until those background tasks finish, the repo-visible work they own has landed, and the final round artifacts required by this scaffold exist.
13. A clean main pass exit is not enough when background tasks were used. Before moving on, confirm there are no still-running background tasks tied to the implementation pass and that the final round artifacts have actually been written.
14. Update `{{current_lane_roadmap}}` on success: mark the executed `[NEXT]` item as `[DONE]`, promote the next `[QUEUED]` item to `[NEXT]`, and keep later items `[QUEUED]`.
15. Write the round summary to `{{next_phase_doc}}`. Include scope, files changed, validation commands, Vulture findings when configured, the lane advanced, the completed roadmap queue item, and the next recommended slice.
16. Commit successful rounds as `{{commit_prefix}}: round {{round_attempt}} - <short subject>`.
17. If validation fails, attempt one focused repair. If it still fails, revert the round, do not commit, and return `failure`.
18. If the queued objective is already complete, avoid unnecessary edits, update the lane roadmap accordingly, and return `goal_complete`.

Response contract:
- Your final response must be valid JSON matching the provided output schema.
- Set `lane_id` to `{{current_lane_id}}`.
- Use actual repo-relative paths in `phase_doc_path` and `changed_files`.
- Set `status` to one of `success`, `failure`, or `goal_complete`.
- On `success`, `commit_sha` and `commit_message` must be non-null.
- On `failure`, `blocking_reason` must explain why the round stopped.
- Include every command you ran in `commands_run`, and list the validation commands in `tests_run`.
- Report `background_tasks_used`, `background_tasks_completed`, `repo_visible_work_landed`, and `final_artifacts_written` truthfully; `success` is invalid if background work is still running, repo-visible work has not landed, or final artifacts are missing.
