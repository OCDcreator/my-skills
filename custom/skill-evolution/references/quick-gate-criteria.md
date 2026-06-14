# Quick Gate Criteria

The Quick Gate is the product. Its job: keep overfit / duplicate / preference-only feedback out of the skill while letting real engineering principles in. It is model-judged and has a self-serving bias toward `discard`, so it is supplemented by a grep pre-check (Gate 2), borderline surfacing (Gate 3), transparency, and human approval.

**Every verdict requires pasted evidence (Hard Contract).** Gate 2 verdicts paste the matched existing rule text + `file:line` (or state "grep: no hits" for `new`); Gate 3 verdicts quote the user message + the principle-vs-preference reasoning; Gate 1 fails cite the single-document scope. A verdict without pasted evidence is tagged `unverified` in the report — never silently trusted. (This is auditable evidence, not automated verification — see SKILL.md "Known Limitation: Verification Ceiling".)

## Gate 1 — Generality

Does the rule generalize to a **class of inputs**, not just the triggering document? If you never see this exact document again, is the rule still meaningful?

- PASS: "distinct solution methods must be separate paragraphs" (any multi-method doc).
- FAIL: "page 274's table should use 3 columns" (single-doc instance).

## Gate 2 — Duplication (grep pre-check, then semantic)

Step A — **grep pre-check**: extract keywords from `candidate_rule` (method names, distinctive nouns like "formula", "callout", "array"). `rg` them against the target skill's `SKILL.md` + `references/*.md`. Collect hits.

Step B — **semantic judgment** (only on hits, or on "no hits → likely new"): compare the candidate to each hit:
- no relevant hit → `new`
- hit exists but weak/vague → `strengthen`
- hit fully covers it → `duplicate`
- hit contradicts it → `conflict`

Judging duplication against a 400+ line SKILL.md plus several reference files by semantics alone is unreliable — the grep pre-check keeps this honest.

## Gate 3 — Preference vs Principle

Is it a transferable engineering principle (another skilled practitioner agrees it's correct), or personal taste?

- principle: structural integrity, content fidelity, correctness, verifiability.
- preference: "I prefer shorter paragraphs", "this phrasing is ugly".

Already-documented rules stay in scope (e.g. a stated 300-char paragraph limit is config, not taste). One-off taste does not become a rule.

**Borderline verdicts are surfaced for explicit user confirmation** — never silently discarded. Silent `preference → discard` is the path that loses recurring real feedback.

**Every `preference-clear → discard` must show its reasoning** (not just borderline): the user quote, why it is preference (not principle), whether existing skill rules already encode it, why it is safe to discard, and the recurrence count. The `preference-clear → discard` path is where the model's self-serving bias is strongest and the user's visibility is weakest — so it gets full sunlight. A discard with no shown reasoning is `unverified`.

## Decision matrix — precedence (top wins)

Evaluate top-down; the first matching row decides. This resolves overlap between wildcards.

1. Gate 2 == `conflict` → **`human_review`** (never auto-resolved)
2. Gate 1 == fail → **`discard`** (overfit / single-doc)
3. Gate 2 == `duplicate` → **`discard`** (already covered)
4. Gate 3 == `preference-borderline` → **`surface`** (ask user)
5. Gate 3 == `preference-clear` → **`discard`** (taste) — must show full reasoning (user quote + why preference + existing-rule check + recurrence), see Gate 3 above
6. Gate 2 == `new` & Gate 3 == `principle` → **`add_new`**
7. Gate 2 == `strengthen` & Gate 3 == `principle` → **`strengthen`**

## Worked examples (validated against rewrite-doc2x-markdown)

| user correction | G1 | G2 | G3 | decision (precedence row) |
|---|---|---|---|---|
| "法一法二别合并" | pass | strengthen | principle | strengthen (row 7) |
| "公式 `\$` 显示错了" | pass | duplicate (F2 covers `\$`) | * | discard (row 3) |
| "这段解析太啰嗦,精简下" | pass | duplicate | preference-clear | discard (row 3 beats row 5; also violates Preserve-ALL-detail) |
| "callout 的 `>` 丢了" | pass | strengthen | principle | strengthen (row 7) |
| "第 274 页图标位置不对" | fail | * | * | discard (row 2) |
| "我喜欢段落再短一点" | pass | * | preference-borderline | surface (row 4) |
| (new) "callout 嵌套时要双 `>`" | pass | new | principle | add_new (row 6) |
