# Codex Autopilot Success-Evidence-First Validation Design

## Goal

Harden `custom/codex-autopilot-scaffold` so genuinely successful unattended rounds are not misclassified as failures merely because the reported test commands do not match a narrow string-prefix rule.

The target behavior is:

- keep strict failure semantics for missing commits, missing phase docs, bad build/deploy evidence, and broken result contracts,
- but stop treating a round as failed when the round clearly succeeded and the only mismatch is that targeted test recognition was too narrow.

## Current State

- The scaffold currently validates successful rounds in `templates/common/automation/_autopilot/validation.py`.
- For changed code/test files, targeted tests are enforced via `targeted_test_required=true`, `targeted_test_required_paths`, and `targeted_test_prefixes`.
- Node/TypeScript repos currently default to a very narrow targeted-test prefix set from `scripts/scaffold_repo.py`:
  - `npm test --`
  - `npm run test --`
- In real unattended runs, some repos report targeted tests with commands such as `npx jest ...`, which are valid targeted test evidence but do not match the narrow prefix list.
- This causes a successful round with:
  - a real commit,
  - a real phase doc,
  - `HEAD == commit_sha`,
  - passing `npm run verify`,
  - and verified deploy/build evidence
  
  to still be classified as `failure` because the targeted-test matcher says the tests were "not reported".

This is a controller/scaffold defect, not a target-repo product defect.

## Requirements

### 1. Keep strict hard-failure rules

The design must preserve hard failures for genuinely broken success results, including:

- missing `commit_sha`,
- missing or wrong `phase_doc_path`,
- `HEAD` not matching the reported `commit_sha`,
- missing required `plan_review_verdict` / `code_review_verdict`,
- missing required build evidence,
- missing required deploy evidence,
- dirty worktree after reported success,
- missing final output artifacts or explicit unfinished background-task state.

The fix must not weaken these.

### 2. Introduce success-evidence-first validation

Validation of `status=success` should evaluate the strongest success evidence first:

- `commit_sha` exists,
- the commit really exists and matches `HEAD`,
- `phase_doc_path` exists and matches the expected lane phase doc,
- commit message/prefix rules pass,
- required build/deploy evidence passes,
- final runtime/output ownership rules pass.

If these strong success signals all pass, then weaker reporting mismatches should not automatically collapse the whole round into `failure`.

### 3. Reclassify narrow targeted-test mismatches

If a round has strong success evidence and the only remaining issue is that targeted test reporting did not match the configured prefixes, this should be treated as a softer validation mismatch rather than a full round failure.

For the first implementation pass, this may be represented as:

- a warning emitted through the existing validation support logger, or
- a non-fatal validation finding handled separately from hard failure conditions.

But it must not return a blocking failure reason by itself when the round otherwise clearly succeeded.

### 4. Expand targeted-test command recognition

The scaffold must widen default targeted-test recognition for Node/TypeScript repos.

At minimum, the generated default prefixes should cover common successful targeted-test forms such as:

- `npm test --`
- `npm run test --`
- `npx jest `
- `npx vitest `
- `pnpm test --`
- `pnpm exec jest `
- `pnpm exec vitest `
- `yarn test `
- `yarn jest `
- `yarn vitest `

This is not the whole solution, but it reduces the number of false mismatches immediately.

### 5. Preserve true targeted-test failures

If a round changed code/test files and:

- no strong targeted-test evidence exists,
- and no acceptable targeted-test command was reported,

then validation must still fail.

The goal is not to remove the targeted-test requirement. The goal is to stop false negatives caused by incomplete command recognition.

### 6. Add regression coverage

Regression tests must prove all of the following:

1. a successful Node/TypeScript round using `npx jest ...` no longer fails solely because targeted-test prefixes were too narrow,
2. a successful round using other newly-supported targeted-test prefixes is also accepted,
3. a round with strong success evidence but only the targeted-test recognition mismatch is downgraded from hard failure,
4. a round that truly omitted targeted tests still fails.

## Proposed Validation Model

### Hard success evidence

For `status=success`, treat these as hard success evidence:

- valid `commit_sha`,
- valid `phase_doc_path`,
- `HEAD == commit_sha`,
- actual commit message matches reported message,
- commit prefix is valid,
- required review verdict fields are present,
- required build/deploy evidence is present,
- no dirty worktree remains.

If any of these fail, the result should still be a hard failure.

### Soft reporting mismatches

Treat these as softer reporting mismatches when hard success evidence already holds:

- targeted tests were likely run, but the command string did not match the configured prefixes,
- other non-structural reporting mismatches of the same class where real round success is already strongly proven.

For the first pass, only the targeted-test mismatch needs to be explicitly handled.

### Failure precedence

Validation should effectively follow this order:

1. schema / required-field validation
2. lane and phase-path validation
3. commit / head / phase-doc / build / deploy / dirty-worktree hard checks
4. targeted/full-test reporting checks
5. command-budget handling

The key change is that step 4 must no longer be able to override step 3 when the only problem is narrow command recognition.

## Proposed Implementation Surfaces

### `scripts/scaffold_repo.py`

Update Node/TypeScript command detection so `DetectionResult.targeted_test_prefixes` includes more common targeted-test command families, especially `npx`, `pnpm`, and `yarn` patterns.

### `templates/common/automation/_autopilot/validation.py`

Add a clearer separation between:

- hard validation errors that should fail the round,
- softer reporting mismatches that should warn when hard success evidence already exists.

One reasonable design is:

- gather hard validation errors,
- gather soft validation mismatches,
- if hard errors exist, fail,
- if only soft mismatches exist and hard success evidence is intact, log warnings and continue.

### `evals/test_scaffold_versioning.py`

Add focused regression tests at the scaffold level for:

- expanded Node/TS targeted-test prefix generation,
- success-result validation with `npx jest ...`,
- preservation of hard failure when targeted tests were truly absent.

## Non-Goals

This design does **not** aim to:

- make all reporting mismatches non-fatal,
- remove targeted-test requirements,
- redesign full-test cadence semantics,
- change deploy policy rules,
- change the meaning of `status=success` vs `status=failure`,
- solve OpenCode implementation-pass stalls or missing `assistant-output.json` failures.

Those are separate issues.

## Risks and Mitigations

- **Risk: validation becomes too permissive**
  - Mitigation: only downgrade targeted-test mismatches when hard success evidence is already intact.

- **Risk: future command styles still slip through**
  - Mitigation: expand default prefixes now and keep the logic structured so more patterns can be added later.

- **Risk: hidden true test omissions become warnings**
  - Mitigation: preserve hard failure when there is no convincing targeted-test evidence at all.

## Success Criteria

- A round with a real success commit, valid phase doc, aligned `HEAD`, and valid build/deploy evidence is not marked as failure solely because it reported `npx jest ...` instead of `npm test -- ...`.
- The scaffold generates broader targeted-test prefixes for Node/TypeScript repos.
- A round that truly omitted targeted tests still fails.
- Regression coverage proves both the fixed false-negative case and the preserved true-failure case.
