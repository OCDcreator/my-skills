# Hooks, Self-Repair, and Self-Evolution

This reference covers optional hooks configuration and the self-repair protocol for `opencode-loop`. Load this file when you need to configure hooks or debug a stalled run.

## Optional Hooks

Normal hooks run shell commands at pre/post iteration boundaries. They are useful for external review or side checks and never stop the loop when exhausted. Do not confuse these with execute mode's `gate-review` blocking gate hook: that hook is consumed by the review gate, and a missing or failing `gate-review` makes the gate unavailable/fail instead of merely warning.

For execute review gates, do not write reviewer scripts that only inspect raw `git diff` from the worktree. A task may already be committed and clean when the review gate runs. Use the gate-provided review context first:

- `OPENCODE_LOOP_REVIEW_DIFF_FILE`
- `OPENCODE_LOOP_REVIEW_STAT_FILE`
- `OPENCODE_LOOP_REVIEW_CHANGED_FILES_FILE`
- `OPENCODE_LOOP_REVIEW_CONTEXT_FILE`
- `OPENCODE_LOOP_REVIEW_DIFF_RANGE`

These files represent the task branch/worktree diff that should be reviewed, including committed clean states.

**Detect reviewer commands before adding hooks.** Commands vary across machines:

```bash
# Detect Kimi CLI (may be `kimi` or `kimi-code`)
KIMI_CMD=$(command -v kimi-code 2>/dev/null || command -v kimi 2>/dev/null || echo "")
CLAUDE_CMD=$(command -v claude 2>/dev/null || echo "")
CODEX_CMD=$(command -v codex 2>/dev/null || echo "")
```

```bash
opencode-loop hooks add --dir /path/to/target --event pre_iteration \
  --name kimi-ui --command "$KIMI_CMD --dir \"\$OPENCODE_LOOP_TARGET_DIR\" \"Review UI\"" --attempts 3
opencode-loop hooks add --dir /path/to/target --event post_iteration \
  --name codex-review --command 'codex exec --cd "$OPENCODE_LOOP_TARGET_DIR" "Review"' --attempts 3
opencode-loop hooks add --dir /path/to/target --event post_iteration \
  --name claude-review --command 'claude -p --cwd "$OPENCODE_LOOP_TARGET_DIR" "Review code changes."' --attempts 3
opencode-loop hooks install-review --dir /path/to/target --codex-bin codex --timeout 1800
opencode-loop hooks install-recovery --dir /path/to/target --codex-bin codex --timeout 900
opencode-loop hooks list --dir /path/to/target --json
```

**Validate hooks in two layers.** `hooks test` may hang on slow reviewers — validate the reviewer command directly first:

```bash
# Layer 1: Validate reviewer produces valid output independently
$KIMI_CMD --print --final-message-only --cwd /path/to/target "Output ONLY JSON: {\"result\":\"pass\"}"
# Expected: {"result":"pass"}

# Layer 2 (supplementary): hooks test confirms wiring
# Use a timeout — it can hang if the reviewer takes >30s
timeout 120 opencode-loop hooks test --dir /path/to/target --event post_iteration --iteration 0
timeout 120 opencode-loop hooks test --dir /path/to/target --event post_iteration --recovery
```

Do not treat `hooks test` as the sole gatekeeper for hook readiness. If Layer 1 passes but Layer 2 hangs, the hook is still functional.

For Full Auto execute queues, install the recovery hook before starting the supervisor. The helper only writes `.opencode-loop/gate-recovery-review-codex.sh` and `hooks.json`; it does not call Codex during setup. During execution, Codex is called only after a failed gate to decide whether a narrow queue contract can be repaired safely, for example by adding precise supporting tests to `scope_paths`.

For Full Auto queues that require review, prefer `hooks install-review` over hand-written review scripts. The installed `gate-review` reads opencode-loop's review diff/context files, so committed clean task worktrees remain reviewable instead of being misclassified as "no diff".

## Self-Repair / Self-Evolution Protocol

Use this low-freedom sequence when a stalled run reveals an `opencode-loop` controller, heartbeat, queue-contract, or skill gap. Do not skip to relaunching the target loop.

1. Freeze blind retries:
   ```bash
   opencode-loop status --dir /path/to/target --json
   opencode-loop observe --dir /path/to/target --json
   opencode-loop heartbeat status --dir /path/to/target --json
   ```
2. Preserve evidence and task work before touching controller or target state:
   ```bash
   mkdir -p /path/to/target/.opencode-loop/recovery/$(date -u +%Y%m%dT%H%M%SZ)
   git -C /path/to/target status --short --branch
   git -C /path/to/target diff --stat
   ```
3. Extract the first concrete blocker from the latest progress/output/stderr/supervisor/gate logs and queue `last_error`. The next model prompt must name that blocker, not say "continue".
4. If the blocker is controller-side, fix the `opencode-loop` source first. Run the narrow relevant test, then `bash bin/test.sh` when feasible. Prepend the lesson to `docs/pitfalls-and-lessons.md`, commit, and deploy:
   ```bash
   bash bin/install-cli.sh
   opencode-loop heartbeat refresh --dir /path/to/target --interval-minutes 10
   ```
5. If the blocker is skill-side, update this skill only after consulting the `skill-creator` skill:
   - Load the `skill-creator` skill using your platform's native skill tool (e.g., `skill` in OpenCode, `Skill` in Claude Code)
   - Run `quick_validate.py` from that skill's `scripts/` directory against `/path/to/my-skills/custom/opencode-loop`
   - Keep fragile recovery steps low-freedom with exact commands. After validation, commit the skill repo change.
6. Deploy the refreshed skill to any dedicated target worktree that carries a repo-local copy:
   ```bash
   mkdir -p /path/to/target/.codex/skills/opencode-loop
   cp /path/to/my-skills/custom/opencode-loop/SKILL.md /path/to/target/.codex/skills/opencode-loop/SKILL.md
   ```
7. Resume only the original queue:
   ```bash
   opencode-loop next-command --dir /path/to/target --kind supervisor --profile execute --wrap tmux --resume-existing-queue
   opencode-loop status --dir /path/to/target --json
   ```

The intended evolution loop is: detect trap → repair controller/skill → validate → commit → install wrapper → refresh scheduler snapshot → deploy target-local skill → resume the same queue. Treat a stale heartbeat snapshot as an undeployed fix.

For `environment_blocked` after `Isolation integration conflict`, do not reset the target root. Preserve the root diff, verify dirty files match the blocked task's `scope_paths`, and use the controller's blocked-integration dirty-scope recovery path. The safe target-side shape is a blocked task with `last_error/status_reason` containing `integration conflict` plus dirty files owned by that same task. Anything else needs manual diagnosis before resuming.
