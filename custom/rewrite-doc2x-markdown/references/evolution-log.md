# Evolution Log — rewrite-doc2x-markdown

Append-only history of skill-evolution runs. Every invocation appends an entry
regardless of verdict (approve / revise / reject / discard).

---

## 2026-06-15 — strengthen: one subpart per line

- **Trigger (verbatim user message):** "在产生 md 的时候，如果例题有 (1) (2) 这种多问，要求必须换行，而不是全都堆在一行，变成一坨。"
- **Classification:** `missing` (line-layout rule not enforced)
- **Provenance:** `(user-stated)` — proactive directive; no in-context preceding
  assistant turn. Prior rewrite work referenced only via memory, not this
  session's transcript, so no specific bad output is cited as evidence.
- **Gate verdict:** `strengthen` (Gate 1 PASS general / Gate 2 strengthen /
  Gate 3 principle)
  - Gate 2 evidence — existing rule `references/canonical-markdown-rules.md:18-19`
    addressed whether subparts stay but was silent on line layout.
  - Corroboration — `tests/test_validate_canonical_markdown.py:215-217` already
    expected (1) and (2) on separate lines; intent existed, rule did not mandate it.
- **Pairwise conflict:** fast path (1 candidate).
- **Dev Eval:** N/A — semantic layout rule; validator preserves `(1)(2)` but
  cannot detect cramming; no in-session corrected artifact.
- **Landing zone:** primary = `references/canonical-markdown-rules.md` (strengthen
  existing subpart rule + new Hard rule under Question Callouts); secondary =
  `SKILL.md` Step 6 judgment self-check item.
- **Strongest reason NOT to add:** test file + "regenerate readable structure"
  principle arguably already cover it. **Counter:** user empirically hit the
  failure, proving implicit coverage insufficient.
- **Outcome:** APPROVED (user approved full packet).
- **Files written:**
  - `references/canonical-markdown-rules.md` (Diff 1 strengthen line 19; Diff 2 new Hard rule)
  - `SKILL.md` (Diff 3 — Step 6 self-check "Subpart line breaks")
- **Snapshots:**
  - `SKILL.md.bak-2026-06-15`
  - `references/canonical-markdown-rules.md.bak-2026-06-15`
- **Recurrence count:** 0 (first).
- **Active-context staleness:** editing the repo file does not change the
  currently-loaded skill text; recommend a fresh session to exercise the
  improved rule.

---

## 2026-06-15 — add_new: comma consistency & spacing

- **Trigger (verbatim user message):** "还有一点就是md 中的逗号，我希望统一是, 也就是英式逗号加一个空格这种格式。让技能多出这个约束。"
- **Classification:** `missing` → refined via human-review scope questions to a
  *consistency + spacing* rule (not a global English-comma mandate).
- **Provenance:** `(user-stated)` — proactive directive; no in-context preceding
  assistant turn.
- **Scope resolution (human review):** Original wording read as "all commas →
  English `, `", which Gate 2 flagged as `conflict` with 5 existing rule
  locations mandating Chinese `，` (`auto-fix-rules.md:55`, examples :43/:46/:49;
  `analysis-retypesetting.md:32,76`; `proofreading-checklist.md:50`; test
  fixtures). Surfaced per safety-valve #1 (conflict → always human_review).
  User then chose the **soft scope**: "只要求统一+带空格" — do not mandate
  Chinese vs English, only require (a) every comma followed by exactly one space,
  (b) no `，`/`,` mixing within a paragraph/callout. This re-routes Gate 2 from
  `conflict` to `new` (compatible layer over the existing "prefer Chinese `，`"
  default — no logical contradiction).
- **Gate verdict (final):** `add_new` (Gate 1 PASS general / Gate 2 `new` /
  Gate 3 principle — typographic hygiene).
- **Pairwise conflict:** fast path (1 candidate).
- **Dev Eval:** ran full `pytest` suite after edits — see verification summary
  below. Validator gains NO comma regex (deliberate — a naive comma-spacing
  check would violate Forbidden Pattern F1 and false-positive on `$f(x,y)$`);
  the rule is model-enforced via SKILL.md self-check, consistent with how most
  skill rules work. Hard validator enforcement deferred as follow-up.
- **Landing zone:** primary = `references/canonical-markdown-rules.md` (new
  "## Punctuation Consistency" section); secondary = `SKILL.md` Step 6
  self-check item; regression fixture in `tests/test_validate_canonical_markdown.py`.
- **Strongest reason NOT to add:** "consistency" is arguably already implied by
  existing "always use Chinese `，`" rules. **Counter:** Doc2X output mixes
  `,`/`，`/glued commas in practice (esp. between formulas), so an explicit
  no-mixing + spacing rule with a grep check adds real verifiable hygiene.
- **Outcome:** APPROVED (user approved full packet after scope resolution).
- **Files written:**
  - `references/canonical-markdown-rules.md` (Diff 1 — new "## Punctuation Consistency" section)
  - `SKILL.md` (Diff 2 — Step 6 self-check "Comma consistency & spacing")
  - `tests/test_validate_canonical_markdown.py` (Diff 3 — `test_accepts_consistent_comma_style` acceptance fixture)
- **Snapshots (same-day, 2nd):**
  - `SKILL.md.bak-2026-06-15-2`
  - `references/canonical-markdown-rules.md.bak-2026-06-15-2`
  - `tests/test_validate_canonical_markdown.py.bak-2026-06-15`
- **Recurrence count:** 0 (first; distinct from the subpart-line lesson).
- **Active-context staleness:** editing the repo file does not change the
  currently-loaded skill text; recommend a fresh session to exercise the
  improved rule.

---

## 2026-06-16 — batch: 5 lessons (A-E) from 极米导数策略 session

Session processing PDF pages 6-36 produced ≥8 rework corrections. Five
candidates extracted, all approved by user in a single batch.

### Candidate A — strengthen: fraction nesting definition

- **Trigger (verbatim):** "这里为什么是 tfrac 很明显这里没嵌套啊，他是对数的真数又不是底数，排查所有这个问题"
- **Classification:** `rework` — over-corrected 19 `\ln` arguments from `\dfrac` to `\tfrac`.
- **Provenance:** `(extracted)` — full transcript in-context.
- **Gate verdict:** `strengthen` (Gate 1 PASS / Gate 2 strengthen line 155 / Gate 3 principle).
  - Gate 2 evidence: `canonical-markdown-rules.md:155` said "or log base" —
    ambiguous between `\log_{base}` (subscript) and `\ln(argument)`.
  - Adversarial: "log base arguably clear." Counter: 19 wrong changes prove real confusion.
- **Landing zone:** `references/canonical-markdown-rules.md` — replaced "or log
  base" with explicit nested-context list + "function arguments are NOT nested" rule.

### Candidate B — add_new: F6 no regex for fraction nesting

- **Trigger (verbatim):** "重点是你要将所有分式提取出来看哪些不符合规则懂吗？不要写代码匹配你根本就匹配不明白"
- **Classification:** `missing` — regex cannot parse nested LaTeX braces.
- **Provenance:** `(extracted)` — full transcript in-context; preceding action was
  failed `rg` regex commands that both missed real violations and false-positive'd.
- **Gate verdict:** `add_new` (Gate 1 PASS / Gate 2 `new` — F1 doesn't list
  fraction nesting / Gate 3 principle — verifiable technical limitation).
- **Landing zone:** `SKILL.md` Forbidden Patterns — new F6.

### Candidate C — strengthen: image path specification

- **Trigger (verbatim):** "图的链接你是不是没有按照本地路径改？"
- **Classification:** `rework` — used `images/...` instead of `doc2x/export/images/...`.
- **Provenance:** `(extracted)`.
- **Gate verdict:** `strengthen` (Gate 1 PASS / Gate 2 strengthen line 258 / Gate 3 principle).
  - Gate 2 evidence: `canonical-markdown-rules.md:258` said `images/name.png` —
    misleading example, since source-transcript.md is in job root.
- **Landing zone:** `references/canonical-markdown-rules.md` — clarified relative path.

### Candidate D — add_new: Q&A ordering rule

- **Trigger (verbatim):** "解析没有在对应的练习下面" + "其他的练习你不排查吗？"
- **Classification:** `missing` — no existing rule on Q&A positioning.
- **Provenance:** `(extracted)`.
- **Gate verdict:** `add_new` (Gate 1 PASS / Gate 2 `new` — grep no hits / Gate 3 principle).
- **Landing zone:** `references/canonical-markdown-rules.md` Question Analysis Blocks
  + `SKILL.md` Step 6 self-check.

### Candidate E — add_new: sweep-on-report

- **Trigger (verbatim):** "其他的练习你不排查吗？你应该调用子代理全部排查因为其他地方也有这个问题"
- **Classification:** `missing` — model fixed only the pointed-out instance.
- **Provenance:** `(extracted)`.
- **Gate verdict:** `add_new` (Gate 1 PASS / Gate 2 `new` / Gate 3 principle).
- **Landing zone:** `SKILL.md` Step 6 self-check.

### Batch metadata

- **Pairwise conflict check:** 5 candidates, all pairs checked, no conflicts.
- **Dev Eval:** 46 tests pass before and after (documentation-only changes).
- **Outcome:** APPROVED (user approved full batch).
- **Files written:**
  - `references/canonical-markdown-rules.md` (Candidates A, C, D)
  - `SKILL.md` (Candidates B, D, E + strengthened fraction self-check)
- **Snapshots:**
  - `SKILL.md.bak-2026-06-16`
  - `references/canonical-markdown-rules.md.bak-2026-06-16`
- **Recurrence count:** All 0 (first occurrence for each).
- **Active-context staleness:** editing the repo file does not change the
  currently-loaded skill text; recommend a fresh session to exercise the
  improved rules.

