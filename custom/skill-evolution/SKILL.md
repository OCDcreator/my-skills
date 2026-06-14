---
name: skill-evolution
description: Use after finishing a task with ANY custom skill where you gave corrections, rework, or "do this differently" feedback, and want to fold those corrections back into the skill so the same mistake is not repeated. Invoke manually at the end of a session — it reads the session's user messages, extracts rework-type feedback with its failure context, runs an anti-overfit gate, and proposes a concrete edit to the target skill's SKILL.md. Use it whenever a custom-skill task ended with you redoing or correcting the model's work, even if you only gave one piece of feedback.
---

# Skill Evolution

Manually-invoked meta-skill. After a `custom/` skill task where the user gave corrections/rework, capture the trace-backed lessons, filter them through an anti-overfit Quick Gate, and propose a concrete, human-approved edit to the target skill's `SKILL.md`. The Quick Gate is the product; it exists to stop overfit/personal-preference noise from bloating the skill.

## Hard Contract

- **Manual invocation only.** Never auto-trigger. The user calls this after a task ends.
- **`custom/` targets only.** Refuse any target path outside `custom/` (especially `external/`). See `references/target-skill-scope.md`.
- **Two safety valves never auto-resolve:**
  1. `conflict` (candidate rule contradicts an existing hard rule) → always `human_review`.
  2. Dev Eval regression (target skill's validator fails after the candidate behavior) → never write; surface the failure. (Dev Eval itself is deferred to v0.5; the principle stands.)
- **Pre-edit snapshot.** Before any write, create `SKILL.md.bak-YYYY-MM-DD` beside the target file. Local undo if the edit is bad.
- **Human approval required.** Never write without an explicit approve. Show the diff + the gate reasoning + an adversarial "strongest reason NOT to add this" note.
- **No auto-commit.** Write the file; the user commits. If the diff touched frontmatter, remind the user to run `python3 scripts/generate_skills_catalog.py` and `python3 scripts/verify_structure.py`.
- **Active-context staleness.** Editing the repo file does NOT change this session's loaded skill text. State this in the final report; recommend a fresh session to exercise the improved skill.

## Preconditions & Path Resolution

Resolve the target skill's repo path in this order (see `references/target-skill-scope.md`):

1. **Known repo root** — `C:\Users\lt\Desktop\Write\custom-project\my-skills` (same hardcoded root `custom/skill-router` uses), then `custom/<skill>/`.
2. **realpath fallback** — `os.path.realpath` on the loaded skill path, accepted only if it resolves into `<root>/custom/`.
3. **Ask the user** — if both fail, ask for the path. This is a **normal path, not an error**.

Validate the resolved path is under `custom/` before any read/write.

## Pipeline

### Step 0 — Resolve target & validate scope
Resolve path (above). If not under `custom/`, refuse with the fork-first guidance (`references/target-skill-scope.md`).

### Step 1 — CAPTURE (trace-backed)
Extract **all** user messages verbatim first (lossless; user messages are sparse). Classify each: `rework | missing | wrong | style-pref | off-topic`. For each `rework/missing/wrong`, enrich into a trace-backed entry (see `references/lesson-schema.md`): verbatim message, the preceding assistant action, affected file paths + their state at that moment, the final accepted state, relevant validator/self-check outputs, whether it resolved, uncertainty notes. `style-pref` → Gate 3 scrutiny. `off-topic` → drop from lesson pipeline, keep in retro.

### Step 2 — Pre-read evolution-log (recurrence)
Before gating, read the target skill's `references/evolution-log.md` (create if absent). Mark any candidate whose substance **recurred ≥2 times** as a prior `discard` — these are recurrence candidates eligible for third-strike promotion (`references/evolution-log-format.md`).

### Step 3 — Batch pairwise conflict check
Check candidate lessons against **each other** (not just existing rules). Any pairwise contradiction → `human_review`. (A young skill can produce 7–8 new rules per session; this catches cross-candidate clashes.)

### Step 4 — QUICK GATE (per candidate)
Run Gates 1–3. Gate 2 does a grep keyword pre-check before semantic judgment; Gate 3 borderline verdicts are **surfaced for confirmation**, never silently discarded. Assign the decision per the matrix below. Full rubric: `references/quick-gate-criteria.md`.

**Decision matrix (row precedence: `conflict` > Gate1-fail > `duplicate` > `preference`(clear) > `add_new`/`strengthen`):**

| Gate 1 | Gate 2 | Gate 3 | decision |
|---|---|---|---|
| pass | new | principle | `add_new` |
| pass | strengthen | principle | `strengthen` |
| pass | duplicate | * | `discard` |
| fail | * | * | `discard` |
| * | conflict | * | `human_review` |
| pass | * | preference (clear) | `discard` |
| pass | * | preference (borderline) | `surface` — ask user |

### Step 5 — (v0.5, deferred) Dev Eval
Not in v0. When implemented: run the target skill's validator on the **corrected** output; regression blocks the write. v0 marks all diffs "unverified — Dev Eval lands in v0.5".

### Step 6 — (v1, deferred) Strict Eval option B
Not in v0. For structural changes in v0: route to `human_review` (present + defer). The option-B structured-proposal machinery lands in v1.

### Step 7 — Landing zone
Choose where each surviving rule lands via the 4-tier cascade in `references/landing-zone-rules.md`. Add a date stamp to every new rule.

### Step 8 — Snapshot + diff
Create `<target>/SKILL.md.bak-YYYY-MM-DD`. Generate the concrete diff (SKILL.md and/or references/), annotated with each change's gate reasoning + the adversarial "strongest reason NOT to add this".

### Step 9 — Approve → write → log
Present diff + reasoning. On approve: write to the repo path (symlink propagates to load points). **Regardless of verdict**, append an entry to `<target>/references/evolution-log.md`. Do not commit. If frontmatter changed, remind the user to run the catalog generators.

### Step 10 — Report
Summarize: retro, candidate list + verdicts, written diff path, snapshot path, log entry, **active-context-staleness caveat** (recommend a fresh session to exercise the improved skill).

## Quick Gate — why each criterion exists

- **Gate 1 (Generality):** a rule that only fits the triggering document is overfit noise.
- **Gate 2 (Duplication):** the skill likely already covers it; `strengthen` beats `add_new`. The same model that made the mistake has a self-serving bias toward `discard` (admitting the lesson = admitting it was wrong), so the grep pre-check keeps Gate 2 honest against a large SKILL.md.
- **Gate 3 (Preference vs Principle):** personal taste must not become a universal rule — but already-documented config stays in scope.

Borderline Gate-3 verdicts are surfaced, not silently discarded: silent `preference → discard` is exactly the path that loses recurring real feedback.

## References

- `references/lesson-schema.md` — lesson fields + trace enrichment + worked example
- `references/quick-gate-criteria.md` — full gate rubric + grep pre-check + borderline surface + worked table
- `references/landing-zone-rules.md` — 4-tier landing cascade + failure diagnosis + reference-file guidance
- `references/evolution-log-format.md` — append-only log + third-strike promotion + pre-read step
- `references/target-skill-scope.md` — `custom/`-only rule + `external/` rejection + fork-first
