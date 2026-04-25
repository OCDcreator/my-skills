# Codex Autopilot Intent Confirmation Layer Design

## Goal

Add a startup-only intent confirmation layer to `custom/codex-autopilot-scaffold` so the operator's real objective is locked before unattended execution begins.

The primary goal is to stop the scaffold flow from silently degrading a "keep running" request into a preview-only or single-round-only outcome.

This design should make one rule explicit:

- **smoke is an intermediate step, not a completion state, whenever the operator asked for continuous unattended execution.**

## Current State

- `custom/codex-autopilot-scaffold/SKILL.md` already describes a keep-running contract and says a continuous run is not complete after scaffolding alone.
- The same skill also recommends an initial smoke step, usually `start --dry-run --single-round`, before durable launch.
- `custom/codex-autopilot-scaffold/scripts/scaffold_repo.py` prints both dry-run and daemonizing next steps side by side.
- `custom/codex-autopilot-scaffold/templates/common/automation/README.md` documents the same startup sequence and correctly says only `health` can prove the runner is truly alive.

The problem is not that the scaffold lacks runtime guardrails. The problem is that startup intent is still partly inferred from natural language and procedural suggestions. That leaves room for an agent to stop after the smoke step even when the operator intended "keep running".

## Requirements

### 1. Add a startup-only intent layer

The scaffold flow should gain a distinct pre-execution layer that resolves operator intent before any launch commands are chosen.

This layer belongs **before**:

- dry-run preview,
- single real round,
- daemonization,
- remote Mac handoff,
- review-gated waiting behavior.

This layer must run once per launch/setup interaction, not inside the unattended runtime loop.

### 2. Introduce explicit intent fields

The startup layer should normalize operator intent into a small structured contract:

- `execution_goal`
- `execution_target`
- `work_mode`
- `queue_authority`
- `smoke_policy`

These fields should drive launch decisions more strongly than loose natural-language interpretation.

### 3. Add a hard ask-before-proceed rule

The system must not silently proceed when required intent fields are still ambiguous.

At minimum, it must explicitly confirm when any of these are unclear:

- whether the operator wants preview-only, one real round, or continuous unattended execution,
- whether the real execution target is local Windows, local macOS, or remote `ssh mac`,
- which preset/work mode is intended,
- whether an approved seed plan/spec is the queue authority or whether the preset backlog should drive the queue.

This is a **hard constraint**, not a soft recommendation.

If these fields are missing or conflict with each other, the startup layer must ask instead of guessing.

### 4. Make "keep running" non-degradable

If the resolved `execution_goal` is continuous unattended execution, the flow must not be allowed to end at:

- scaffold installation only,
- `doctor` only,
- `start --dry-run --single-round`,
- one foreground round without durable relaunch,
- printed instructions without launch proof.

For `keep_running`, the minimum successful completion path is:

1. scaffold or refresh,
2. commit scaffold files,
3. dedicated branch/worktree,
4. `doctor`,
5. smoke step if requested or required,
6. durable background launch,
7. `health` verification against the exact intended state file.

### 5. Define smoke as subordinate to the final goal

The startup layer must treat smoke as a sub-step whose meaning depends on `execution_goal`:

- `preview_only`: smoke may be the final endpoint
- `single_real_round`: a real foreground round may be the final endpoint
- `keep_running`: smoke is only a checkpoint before durable launch

This distinction should be enforced in docs and in startup guidance.

### 6. Keep the unattended runtime non-interactive

The intent confirmation layer must not introduce blocking prompts inside the repo-local unattended controller itself.

Specifically:

- no per-round human confirmations,
- no runtime `ask question` inside `autopilot.py` loops,
- no "pause and wait for operator input" behavior inside unattended rounds.

The interactive layer is only for launch-time intent capture.

### 7. Limit the scope of mandatory confirmation

Not every configurable detail belongs in the confirmation layer.

The design should classify startup choices into three buckets:

1. **Must confirm** when ambiguous
2. **Confirm only when risky or low-confidence**
3. **Never elevate into the intent layer**

This prevents the startup layer from becoming a bloated configuration wizard.

## Proposed Intent Model

### Required fields

#### `execution_goal`

Allowed values:

- `scaffold_only`
- `preview_only`
- `single_real_round`
- `keep_running`

This is the most important field and must gate completion semantics.

#### `execution_target`

Allowed values:

- `local_windows`
- `local_mac`
- `remote_mac`

This field decides where runtime proof must come from.

#### `work_mode`

Allowed values:

- `maintainability`
- `review_gated`
- `quality_gate`
- `bugfix_backlog`

This field maps directly to the preset and should not be inferred loosely when user wording is ambiguous.

#### `queue_authority`

Allowed values:

- `seed_plan`
- `seed_spec`
- `preset_backlog`

This field prevents the system from silently choosing generic backlog behavior when the operator expects execution to follow an approved plan/spec.

#### `smoke_policy`

Allowed values:

- `none`
- `dry_run_preview`
- `foreground_real_round`

This field must be interpreted relative to `execution_goal`, not as the final outcome by itself.

## Which wobble points belong in the confirmation layer

### Must confirm when ambiguous

- final execution goal
- actual execution target
- preset/work mode
- queue authority
- smoke style

These are worth asking because a wrong guess can completely invert the operator's expectation.

### Confirm only when risky or low-confidence

- install mode (`fresh install`, `refresh`, `regeneration`)
- inferred validation commands when repo evidence is weak
- deploy policy when deploy side effects are meaningful

These matter, but they do not belong in the mandatory intent layer for every run.

### Keep out of the intent layer

- `runner_model`
- `vulture_command`
- `force-lock`
- `allow-dirty-worktree`
- `no-branch-guard`
- `restart-after-next-commit`
- `watch` formatting or tail count
- machine-local `profile-path` details

These are implementation/operator controls, not first-class intent fields.

## Hard Constraints

### 1. Ambiguity must trigger a question

If the startup layer cannot confidently resolve required intent fields, it must ask once before launch.

The system must not silently:

- assume `preview_only`,
- assume `single_real_round`,
- assume local execution when the operator actually means remote Mac,
- assume preset backlog when a seed plan/spec appears to be the intended authority.

### 2. `keep_running` must override smoke as the terminal state

If `execution_goal=keep_running`, then:

- `dry_run_preview` cannot count as success,
- `foreground_real_round` cannot count as success by itself,
- the run is incomplete until durable background launch happens,
- the run is still incomplete until `health` proves the target state line is actually live.

### 3. Runtime proof must match execution target

If `execution_target=remote_mac`, then Windows-local runtime artifacts cannot be used as proof that the unattended runner is alive.

The final proof must come from Mac-side `health` and Mac-side bound runtime artifacts.

### 4. Reporting must reflect unresolved state honestly

If the launch has reached only a smoke checkpoint, the final report must say so explicitly.

It must not use wording like:

- "it is running"
- "autopilot is active"
- "the unattended runner is up"

unless the resolved completion contract for that goal has actually been met.

## Recommended Behavior

### Startup interaction

The launch-time interaction should resolve intent in this order:

1. execution goal
2. execution target
3. work mode
4. queue authority
5. smoke policy

If operator wording already makes a field unambiguous, no extra question is needed for that field.

If one or more required fields are ambiguous, ask once with a compact confirmation prompt rather than multiple scattered follow-up questions.

### Suggested operator mapping

- "跑起来 / 一直跑 / 别停 / keep running" → `execution_goal=keep_running`
- "先预览一下 / 先看看 prompt" → `execution_goal=preview_only`
- "先来一轮真实的" → `execution_goal=single_real_round`
- "先审方案再审代码" → `work_mode=review_gated`
- "按 plan/spec 跑" → `queue_authority=seed_plan` or `seed_spec`

### Completion semantics

The startup layer should define completion based on `execution_goal`:

- `scaffold_only`: scaffold produced and reported
- `preview_only`: preview rendered and reported
- `single_real_round`: one foreground round completed and reported
- `keep_running`: background execution launched and verified with `health`

This must be documented in `SKILL.md`, generated operator docs, and startup next-step output.

## Impacted Surfaces

The eventual implementation should update these areas:

- `custom/codex-autopilot-scaffold/SKILL.md`
  - to define the intent confirmation layer and its hard constraints
- `custom/codex-autopilot-scaffold/scripts/scaffold_repo.py`
  - to stop printing ambiguous equal-weight startup paths when `keep_running` is clearly intended
- `custom/codex-autopilot-scaffold/templates/common/automation/README.md`
  - to express completion semantics in terms of resolved intent, not generic command lists

Optional future implementation may also add a machine-readable startup contract artifact, but that is not required for the first pass.

## Risks and Mitigations

- **Too many startup questions**: keep the mandatory layer limited to a few high-impact intent fields.
- **Wizard creep**: do not elevate low-level operational flags into the confirmation layer.
- **False confidence from NLP**: require a real question when the core fields remain ambiguous.
- **Agents still stop at smoke**: make `keep_running` a hard completion contract in both docs and startup output wording.

## Success Criteria

- A "keep running" request can no longer be truthfully completed at dry-run or single-round-only checkpoints.
- Startup flow asks when the core intent fields are ambiguous instead of silently guessing.
- Remote Mac launches require remote proof rather than local artifact hand-waving.
- The distinction between preview, one real round, and continuous unattended execution is explicit in docs and future implementation guidance.
