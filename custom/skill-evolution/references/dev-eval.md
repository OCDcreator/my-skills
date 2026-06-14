# Dev Eval — Regression Gate for Validator-Equipped Skills

Dev Eval is the **one place** skill-evolution invokes a real automated check. It is narrow on purpose: it only catches **non-regression** on skills that ship an **output-file validator**, and only for lessons whose candidate behavior a validator can actually exercise. It is NOT a behavior tester and gives ~no signal for semantic lessons (e.g. "preserve ALL detail", "do byte-level verification"). Honest framing matters — do not oversell Dev Eval as "the verification step". See SKILL.md "Known Limitation: Verification Ceiling".

## Step 1 — Discover the validator (inline glob, no bundled script)

Probe the target skill directory in priority order:

1. `scripts/validate_*.py` / `scripts/*_check.py` (e.g. `rewrite-doc2x-markdown` → `scripts/validate_canonical_markdown.py`)
2. `tests/` directory (e.g. `rewrite-doc2x-markdown/tests/test_validate_canonical_markdown.py`)
3. The Step-6 self-check command block in the target's `SKILL.md` (run those `rg` / `py` commands directly)

Use inline `glob`/`grep` — there is deliberately **no `scripts/find_validator.py`** (discovery is simple enough not to warrant a bundled script; bundle only when this proves non-trivial in practice).

## Step 2 — Run on the CORRECTED output

If a validator is found and runnable, run it on the **corrected** output — the post-redo state the user accepted, **never** the original bad output. Paste the actual command + output as evidence (Hard Contract).

## Step 3 — States

| State | Meaning | Action |
|---|---|---|
| **pass** | Validator still PASS on corrected output after the candidate behavior | No regression → proceed; paste output as evidence |
| **fail** | Validator newly FAILS after the candidate behavior | **Regression** — do NOT write; surface the validator output (safety valve #2) |
| **no validator** | No discoverable validator in the target skill | Skip; flag diff "Dev Eval N/A — no validator" (the common case, ~26 of ~31 custom skills) |
| **exists but cannot run** | Validator present but needs API keys / images / build env not available | Flag "validator present but not runnable"; degrade to unverified |
| **inconclusive** | Sample already failing before the candidate behavior (bad sample) | Degrade to unverified |

## Honest framing

- Dev Eval certifies that an edit did not trip an **output linter**. It does NOT certify the skill's *judgment* improved, that a semantic rule is now followed, or that the edit helps on inputs the validator doesn't cover.
- For the CSS + builder-script case (added a file + changed a script): Dev Eval only helps if the validator actually **exercises the builder**. A syntax-only validator won't catch a broken builder.
- Coverage: ~4–5 of ~31 custom skills ship a validator. For the rest, Dev Eval is N/A and the skill relies on auditable evidence + human review (the rest of the Verification Ceiling stack).

## What Dev Eval does NOT replace

- The evidence-pasting discipline (Gate verdicts, trace fields) — Dev Eval cannot check judgment.
- The human approval packet — Dev Eval pass is one signal, not a substitute for diff review.
- The evolution-log append — happens regardless of Dev Eval outcome.
