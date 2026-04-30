# Repository Autopilot Round — Review-Gated Delivery

You are running one unattended repository autopilot round inside the `[[REPO_NAME]]` repository.

Read these files first, in order:
- `AGENTS.md` if it exists
- `docs/status/autopilot-master-plan.md`
- `docs/status/autopilot-lane-map.md`
- `{{current_lane_roadmap}}`
- `{{last_phase_doc}}`

Mission:
- Continue the review-gated delivery program one active lane at a time.
- Stay inside lane `{{current_lane_id}}` (`{{current_lane_label}}`).
- Execute exactly one queued slice: the first item marked `[NEXT]` in `{{current_lane_roadmap}}`.
- For this preset, each round must pass a plan review before coding and a code review before final validation/commit.
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
- Current round directory: `{{current_round_directory}}`
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
2. Restate the active `[NEXT]` queue item, its acceptance criteria, the files you expect to touch, and the validations you must preserve.
3. Before editing code, write a short execution plan to `{{current_round_directory}}/implementation-plan.md`. Keep it concrete and bounded to this one queued slice.
4. Run a plan review and wait patiently for it to finish. Reviewer latency is expected to be minute-scale; do not treat quiet polling as a hang.
   - Windows: `pwsh -File .\automation\Invoke-OpencodeReview.ps1 -Mode plan -PlanPath "{{current_round_directory}}\implementation-plan.md" -OutputPath "{{current_round_directory}}\plan-review.txt"`
   - macOS/Linux: `bash ./automation/opencode-review.sh plan "{{current_round_directory}}/implementation-plan.md" "{{current_round_directory}}/plan-review.txt"`
5. Record the plan review verdict in the phase doc and final JSON field `plan_review_verdict`.
6. If the plan review verdict is `REVISE`, either repair the plan and re-run the review once, or stop the round with `failure`.
7. Only after plan approval, implement the smallest change set that satisfies the queued slice.
8. Once the implementation pass starts, do not kill it early just because the repo diff is still empty or the pass is still reading files. Discovery, reference-reading, and long planning can be the real work for the first several minutes.
9. Treat a still-growing implementation log or a still-live child PID as proof that the pass is still working, even if no repo edits have landed yet.
10. If the implementation path uses background tasks, do not treat the main pass as complete until those background tasks finish, the repo-visible work they own has landed, and the final round artifacts required by this scaffold exist.
11. A clean main-process exit is not enough when background tasks were used. Before moving on, confirm there are no still-running background tasks tied to the implementation pass and that the round's final output contract has actually been written.
12. Only interrupt or retry an implementation pass early when there is a hard failure signal: the wrapper exits non-zero, the log proves a concrete blocker, or the human explicitly asks to stop. Lack of edits alone is not a blocker.
13. After implementation and before final validation/commit, run a code review and wait for the verdict:
   - Windows: `pwsh -File .\automation\Invoke-OpencodeReview.ps1 -Mode code -OutputPath "{{current_round_directory}}\code-review.txt"`
   - macOS/Linux: `bash ./automation/opencode-review.sh code "{{current_round_directory}}/code-review.txt"`
14. Record the code review verdict in the phase doc and final JSON field `code_review_verdict`.
15. If the code review verdict is `REVISE`, attempt one focused repair, then re-run the code review once. If it still fails, revert the round, do not commit, and return `failure`.
16. Run targeted tests first when code or tests change and a targeted test command pattern is configured.
17. `[[VALIDATION_REQUIREMENT]]`
18. When a validation command is blank, do not invent a substitute; record the gap in the phase doc instead.
19. When Vulture is configured, use it as the dead-code observability command when cleanup or unused-code risk is relevant; record the finding count or any gap in the phase doc.
20. Update `{{current_lane_roadmap}}` on success: mark the executed `[NEXT]` item as `[DONE]`, promote the next `[QUEUED]` item to `[NEXT]`, and keep later items `[QUEUED]`.
21. Write the round summary to `{{next_phase_doc}}`. Include the queued slice, the implementation plan path, plan/code review verdicts, changed files, validation commands, Vulture findings when configured, and the next recommended slice.
22. Commit successful rounds as `{{commit_prefix}}: round {{round_attempt}} - <short subject>`.
23. If the queued objective is already complete, avoid unnecessary edits, update the lane roadmap accordingly, and return `goal_complete`.

Response contract:
- Your final response must be valid JSON matching the provided output schema.
- Set `lane_id` to `{{current_lane_id}}`.
- Use actual repo-relative paths in `phase_doc_path` and `changed_files`.
- Set `status` to one of `success`, `failure`, or `goal_complete`.
- On `success`, `commit_sha` and `commit_message` must be non-null.
- On `failure`, `blocking_reason` must explain why the round stopped.
- Include every command you ran in `commands_run`, and list the validation commands in `tests_run`.
- Set `plan_review_verdict` and `code_review_verdict` to the actual reviewer verdicts when you invoked those review wrappers.
- Report `background_tasks_used`, `background_tasks_completed`, `repo_visible_work_landed`, and `final_artifacts_written` truthfully; `success` is invalid if background work is still running, repo-visible work has not landed, or final artifacts are missing.
