---
name: skill-evolution
description: Use after finishing a task with ANY custom skill where you gave corrections, rework, or "do this differently" feedback, and want to fold those corrections back into the skill so the same mistake is not repeated. Invoke manually at the end of a session — it reads the session's user messages, extracts rework-type feedback with its failure context, runs an anti-overfit gate, and proposes a concrete edit to the target skill's SKILL.md. Use it whenever a custom-skill task ended with you redoing or correcting the model's work, even if you only gave one piece of feedback.
---

# Skill Evolution

Manually-invoked meta-skill. After a `custom/` skill task where the user gave corrections/rework, capture the trace-backed lessons, filter them through an anti-overfit Quick Gate, and propose a concrete, human-approved edit to the target skill's `SKILL.md`. The Quick Gate is the product; it exists to stop overfit/personal-preference noise from bloating the skill.

## Hard Contract

- **Manual invocation only.** Never auto-trigger. The user calls this after a task ends.
- **`custom/` targets only.** Refuse any target path outside `custom/` (especially `external/`). See `references/target-skill-scope.md`.
- **CAPTURE runs in the main orchestrating context.** Do NOT dispatch a subagent for transcript extraction or trace enrichment — the subagent lacks the session. If the executing context cannot access the full transcript (long session, context pressure, invoked fresh), tell the user immediately and accept a user-pasted transcript; every trace-enrichment field is then tagged with provenance (`(extracted)` / `(user-pasted)`) and the retro states it explicitly. **Memory-only reconstruction is not evidence** — put it in `uncertainty` and tag the field `unverified`, never present it as a real trace field. Extracting user messages is cheap and lossless — do it before context pressure forces eviction.
- **Evidence-backed claims (no trust without proof).** Every Gate verdict, pairwise conflict check, and CAPTURE trace field must paste its evidence: existing rule text + location for Gate 2; user quote + reasoning for Gate 3; the generalized class (Gate 1 pass) or single-document scope + triggering quote (Gate 1 fail); actual command output for validator/grep claims; the real assistant turn for `preceding_action` (not paraphrase). Claims without pasted evidence are tagged `unverified` in the report — never silently trusted. This is *auditable evidence*, not automated verification (see Known Limitation).
- **Two safety valves never auto-resolve:**
  1. `conflict` (candidate rule contradicts an existing hard rule) → always `human_review`.
  2. Dev Eval regression (target skill's validator fails after the candidate behavior) → never write; surface the failure.
- **Pre-edit snapshot (behavior-changing writes only).** Before any **behavior-changing write** to the target skill's `SKILL.md` or behavioral reference files, create `SKILL.md.bak-YYYY-MM-DD` beside the target file (suffix `-2`, `-3` if a same-day snapshot exists). Log-only appends to `references/evolution-log.md` do NOT require a snapshot. Local undo if the edit is bad.
- **Human approval on the full packet, not a summary.** Never modify the target skill's `SKILL.md` or behavioral reference files based on a compressed summary — present the unified diff + evidence + gate reasoning (Step 8). Audit artifacts are separate: the evolution log is appended on every invocation regardless of verdict, and the pre-edit snapshot is created immediately before an approved behavior-changing write.
- **No auto-commit.** Write the file; the user commits. If the diff touched frontmatter, remind the user to run `python3 scripts/generate_skills_catalog.py` and `python3 scripts/verify_structure.py`.
- **Active-context staleness.** Editing the repo file does NOT change this session's loaded skill text. State this in the final report; recommend a fresh session to exercise the improved skill.
- **If dispatched as a subagent, do not CAPTURE from memory.** Read skill-evolution's own reference files first (`quick-gate-criteria.md`, `lesson-schema.md`, `evolution-log-format.md`, `dev-eval.md`) plus the target skill's `SKILL.md`. Then either (a) ask the orchestrator/user for a pasted transcript (tag trace fields `(user-pasted)`, mark provenance explicitly) or (b) return "cannot perform CAPTURE from subagent context". Never reconstruct trace fields from memory. State which references were consulted in the report.
- **Session-end responsibility.** If a session used a `custom/` skill and produced ≥3 `rework`-type user corrections, suggest running skill-evolution before the session closes. This is a manual nudge, not an auto-trigger.

## Known Limitation: Verification Ceiling

A content skill is markdown instructions — it has no runtime to verify its own execution. The achievable defense is layered, not a single automated gate: **verifiable artifacts** (the diff, `.bak-*` snapshot, `evolution-log.md`, pasted validator output) + **auditable evidence** (the evidence-pasting discipline above) + **human review** (the approval step) + **narrow external checks** (Dev Eval, only for validator-equipped skills). "Complete reliance on model self-discipline" is a property of the medium, not a fixable-in-skill defect. This skill *reduces* the trust surface (every claim must show evidence; every edit is human-approved) but cannot *eliminate* it. **This section is the canonical Verification Ceiling statement for users of the skill.**

## Preconditions & Path Resolution

Resolve the target skill's repo path in this order (see `references/target-skill-scope.md`):

1. **Known repo root** — `C:\Users\lt\Desktop\Write\custom-project\my-skills` (same hardcoded root `custom/skill-router` uses), then `custom/<skill>/`. `<skill>` may be a direct child or a nested relative path (e.g. `x-reader/analyzer`); accept only if the resolved directory contains `SKILL.md` and stays under `<root>/custom/`.
2. **realpath fallback** — `os.path.realpath` on the loaded skill path, accepted only if it resolves into `<root>/custom/`.
3. **Ask the user** — if both fail, ask for the path. This is a **normal path, not an error**.

Validate the resolved path is under `custom/` before any read/write.

## Pipeline

### Step 0 — Resolve target & validate scope
Resolve path (above). If not under `custom/`, refuse with the fork-first guidance (`references/target-skill-scope.md`).

### Step 1 — CAPTURE (trace-backed, in main context)
Extract **all** user messages verbatim first (lossless; user messages are sparse) — in the main orchestrating context, not a subagent (Hard Contract). Classify each: `rework | missing | wrong | style-pref | off-topic`. For each `rework/missing/wrong`, enrich into a trace-backed entry (see `references/lesson-schema.md`): verbatim message, the preceding assistant action (**paste the real turn — do not paraphrase**), affected file paths + their state at that moment, the final accepted state, relevant validator/self-check outputs, whether it resolved, uncertainty notes. **Provenance**: tag each enrichment field `(extracted)` if exact content from the in-context transcript/files, `(user-pasted)` if exact content supplied by the user; memory-only reconstruction is NOT evidence — it goes in `uncertainty` as `unverified`. The retro states the overall provenance. `style-pref` → Gate 3 scrutiny. `off-topic` → drop from lesson pipeline, keep in retro.

### Step 2 — Pre-read evolution-log (recurrence)
Before gating, read the target skill's `references/evolution-log.md`; if absent, treat as empty (it is created on first run during Step 9 — never infer unrecorded history). For each candidate, scan prior `discard` or `surface` entries for the same substance. Count recurrence by prior matches: 0 = first, 1 = second, ≥2 = third+. Third+ recurrence routes to `surface` with the recurrence history shown, even if Gate 3 would otherwise discard as preference-clear. See `references/evolution-log-format.md`.

### Step 3 — Batch pairwise conflict check (or fast path)
**Fast path**: if ≤3 candidates, skip the pairwise check — contradictions among ≤3 items are human-visible in the full approval packet (candidate table + evidence + unified diff, Step 9) — and note "Fast path — ≤3 corrections" in the report. (The fast path is invalid if the approval packet omits any candidate.) **Otherwise** check each candidate against every other candidate (not just existing rules) and **show each pair compared + the comparison reasoning**; never just assert "no contradictions". Any pairwise contradiction → `human_review`. (A young skill can produce 7–8 new rules per session; this catches cross-candidate clashes.)

### Step 4 — QUICK GATE (per candidate)
Run Gates 1–3 (full rubric in `references/quick-gate-criteria.md`). Gate 2 runs a grep keyword pre-check before semantic judgment; Gate 3 borderline verdicts are **surfaced for confirmation**, never silently discarded. Every verdict must **paste its evidence** (Hard Contract):
- Gate 1 pass → cite the generalized class of inputs it applies to; Gate 1 fail → cite why it is single-document / one-off scope, with the triggering quote.
- Gate 2 `new`/`strengthen`/`duplicate`/`conflict` → paste the matched existing rule text + `file:line` (or state "grep: no hits" for `new`).
- Gate 3 verdict → quote the user message + explain principle-vs-preference + compare to existing rules.

**Decision precedence (evaluate top-down; first match wins):**

1. Gate 2 == `conflict` → **`human_review`** (never auto-resolved)
2. Gate 1 == fail → **`discard`**
3. Gate 2 == `duplicate` → **`discard`**
4. Gate 3 == `preference-borderline` → **`surface`** (ask user)
5. Gate 3 == `preference-clear` → **`discard`** — but **only with full reasoning shown**: user quote, why it is preference (not principle), whether existing rules already encode it, why it is safe to discard, recurrence count. **A `preference-clear → discard` WITHOUT the required reasoning is invalid — it routes to `surface` (or `human_review`), never a final `discard`.** (The self-serving-bias path gets sunlight.)
6. Gate 2 == `new` & Gate 3 == `principle` → **`add_new`**
7. Gate 2 == `strengthen` & Gate 3 == `principle` → **`strengthen`**

All gate verdicts are transparent and human-overridable. If the user overrides `discard` or `surface`, rerun landing-zone selection and proceed through snapshot + explicit approval before any write.

Idempotency: rerunning on the same session should turn already-applied lessons into Gate 2 `duplicate` → `discard`, not add the same rule twice.

### Step 5 — Dev Eval (regression gate, validator-equipped skills only)
Discover the target skill's validator inline via glob: `scripts/validate_*.py` / `scripts/*_check.py` / `tests/` / the Step-6 self-check command block. If found and runnable, run it on the **corrected** output (never the original bad output) and paste the command output. States:
- **pass** → no regression → proceed (paste output as evidence).
- **fail** → regression → do NOT write; surface the validator output (safety valve #2).
- **no validator** → skip; diff flagged "Dev Eval N/A — no validator" (the common case, ~26 of ~31 skills).
- **exists but cannot run** (needs API keys / images / build env) → flag "validator present but not runnable"; degrade to unverified.
- **inconclusive** (sample already failing) → degrade to unverified.

Dev Eval is an output-file lint checking non-regression — it is NOT a behavior tester and gives ~no signal for semantic lessons (e.g. "preserve ALL detail"). Honest framing; do not oversell. Full details: `references/dev-eval.md`.

### Step 6 — (v1, deferred) Strict Eval option B
Not in v0.5. For structural changes — a new rule touching Hard Contract / Step templates / subagent contracts / workflow skeleton, or a candidate that replaces/overturns an existing rule — route to `human_review`: present the candidate + trace + gate reasoning + adversarial note, then defer. Do not auto-apply structural changes. The option-B structured-proposal + on-request `evals.json` machinery lands in v1 (see the future Strict Eval option B spec).

### Step 7 — Landing zone (or fast path)
Choose where each surviving rule lands via the 4-tier cascade in `references/landing-zone-rules.md`. **Fast path**: if ≤3 candidates AND the target `SKILL.md` is NOT near the size cap AND no candidate is a long rubric / exception table / existing-reference-domain rule, collapse to "prefer existing Lessons section, else append to the most relevant step". Otherwise use the full 4-tier cascade (size cap → `references/lessons-learned.md`; reference-domain → that reference file). Add a date stamp to every new rule.

### Step 8 — Prepare snapshot path + unified diff
Prepare the snapshot path `<target>/SKILL.md.bak-YYYY-MM-DD` (suffix `-2`, `-3` if a same-day snapshot exists). Generate the **unified diff** (SKILL.md and/or references/), annotated inline with each change's gate reasoning + the adversarial "strongest reason NOT to add this". Do not write yet.

### Step 9 — Approve → write → log (unconditional)
Present the **full approval packet** — never a compressed summary (Hard Contract): candidate table, evidence table (each verdict's pasted proof), Gate verdicts + reasoning, strongest-reason-not-to-add, landing-zone choice, unified diff, files touched, snapshot path, evolution-log entry preview. On approve: create the snapshot immediately before writing, then write to the repo path (symlink propagates to load points). **Regardless of verdict** (approve / revise / reject / discard), append an entry to `<target>/references/evolution-log.md`, creating the file on first run if absent — bulletproof: append even on error or abort. Do not commit. If frontmatter changed, remind the user to run the catalog generators.

### Step 10 — Report
Summarize: retro (with provenance), candidate list + verdicts + evidence, written diff path, snapshot path, log entry, **active-context-staleness caveat** (recommend a fresh session to exercise the improved skill), and a **verification summary**: which verdicts were machine-verified (Dev Eval pass) vs auditable-evidence-only vs `unverified`.

## Quick Gate — why each criterion exists

- **Gate 1 (Generality):** a rule that only fits the triggering document is overfit noise.
- **Gate 2 (Duplication):** the skill likely already covers it; `strengthen` beats `add_new`. The same model that made the mistake has a self-serving bias toward `discard` (admitting the lesson = admitting it was wrong), so the grep pre-check keeps Gate 2 honest against a large SKILL.md.
- **Gate 3 (Preference vs Principle):** personal taste must not become a universal rule — but already-documented config stays in scope.

Borderline Gate-3 verdicts are surfaced, not silently discarded: silent `preference → discard` is exactly the path that loses recurring real feedback. And per Step 4 row 5, even clear-preference discards must show reasoning or route to `surface`.

## References

- `references/lesson-schema.md` — lesson fields + trace enrichment + provenance tags + worked example
- `references/quick-gate-criteria.md` — full gate rubric + grep pre-check + borderline surface + Gate-3 discard reasoning + worked table
- `references/landing-zone-rules.md` — 4-tier landing cascade + failure diagnosis + reference-file guidance
- `references/evolution-log-format.md` — append-only log + bulletproof append + third-strike promotion
- `references/dev-eval.md` — validator discovery + run states + honest framing (non-regression lint)
- `references/target-skill-scope.md` — `custom/`-only rule + `external/` rejection + fork-first
