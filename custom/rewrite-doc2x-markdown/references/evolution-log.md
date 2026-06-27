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

---

## 2026-06-17 — batch: 4 lessons from pages 179-209 rework

Session rewriting pages 179-209 produced follow-up corrections on rendered
Markdown structure. Four candidates were surfaced and approved by the user.

### Candidate A — human_review approved: two-row choice table separator

- **Trigger (verbatim):** "两行表格时 下面会多出> | :---: | :---: |"
- **Classification:** `rework` — the long-choice table example instructed a
  second alignment row after the C/D row, which rendered as an extra visible row.
- **Provenance:** `(extracted)` — in-session user correction and current file
  verification.
- **Gate verdict:** `human_review` (Gate 1 PASS / Gate 2 conflict / Gate 3
  principle).
  - Gate 2 evidence: `canonical-markdown-rules.md` long-choice example had a
    second `> | :---: | :---: |` after C/D.
  - Adversarial: the old example is normal Markdown-table syntax. Counter: the
    user's actual Obsidian/Typora rendering showed an unwanted extra row, and the
    project contract prioritizes canonical Markdown that renders well.
- **Landing zone:** `references/canonical-markdown-rules.md` Choice Format.

### Candidate B — strengthen: simple formula-list comma placement

- **Trigger (verbatim):** "$m, n$ $\\alpha, \\beta$ 有一些公式中的逗号，就是我的意思是这种应该是  $m$, $n$ $\\alpha$, $\\beta$ 就是逗号该在公式外，这种明显排列的公式，当然复杂公式的话，逗号确实需要再公式中。"
- **Classification:** `rework` — simple lists stayed inside one inline math span.
- **Provenance:** `(extracted)` — in-session user correction and corrected
  output scan (`simple_list_inside_math_count= 0`).
- **Gate verdict:** `strengthen` (Gate 1 PASS / Gate 2 strengthen / Gate 3
  principle).
  - Gate 2 evidence: existing rule said "Keep punctuation outside math delimiters
    when possible" but did not distinguish simple lists from intervals/functions.
  - Adversarial: a broad regex would break intervals and function arguments.
    Counter: the rule explicitly requires semantic classification and preserves
    complex formula commas.
- **Landing zone:** `references/canonical-markdown-rules.md` Formulas + `SKILL.md`
  Step 6 self-check.

### Candidate C — strengthen: display math delimiter blocks

- **Trigger:** subagent review found inline-style display math such as
  `$${g}^{\\prime}\\left(x\\right)=...>0$$`.
- **Classification:** `rework` — formulas used display delimiters on the same line.
- **Provenance:** `(extracted)` — in-session subagent finding and corrected scan.
- **Gate verdict:** `strengthen` (Gate 1 PASS / Gate 2 strengthen / Gate 3
  principle).
  - Gate 2 evidence: existing rule said display math is a standalone `$$...$$`
    block, but did not forbid `$$formula$$` explicitly.
  - Adversarial: validators already false-positive around display math. Counter:
    this is a concrete Markdown formatting rule with a cheap grep self-check.
- **Landing zone:** `references/canonical-markdown-rules.md` Formulas + `SKILL.md`
  evidence checks.

### Candidate D — strengthen: semantic heading hierarchy

- **Trigger (verbatim):** "第三讲的结构压根就不对"
- **Classification:** `rework` — prior fix removed level jumps but left generic
  headings (`知识点总结`, `经典例题`, `归纳总结`) as siblings of their owning topics.
- **Provenance:** `(extracted)` — in-session screenshot/user correction, plus
  memory corroboration of a prior heading-hierarchy correction on 122-178.
- **Gate verdict:** `strengthen` (Gate 1 PASS / Gate 2 strengthen / Gate 3
  principle).
  - Gate 2 evidence: existing Heading Hierarchy said "Never skip levels or use
    inconsistent hierarchy" but did not require checking rendered outline
    semantics.
  - Recurrence evidence: `MEMORY.md` records prior "标题层级不对，重新整理" and
    "normalize heading hierarchy across the document, not just at the local
    offending heading."
  - Adversarial: document-specific topic names should not be hard-coded. Counter:
    the rule generalizes to generic child headings under any topic.
- **Landing zone:** `references/canonical-markdown-rules.md` Heading Hierarchy +
  `SKILL.md` judgment self-check.

### Batch metadata

- **Pairwise conflict check:** 4 candidates, checked as a batch; only Candidate A
  conflicted with the old table example and was explicitly approved by the user.
- **Dev Eval:** corrected output passed:
  `py -3 ...\\validate_canonical_markdown.py --md product\\2026-06-17-jimi-daoshu-179-209\\source-transcript.md --fix --dry-run`
  → `DRY RUN: would auto-fix 0 issue(s)`.
- **Outcome:** APPROVED (user replied "批准").
- **Files written:**
  - `references/canonical-markdown-rules.md` (Candidates A-D)
  - `SKILL.md` (Candidates B-D self-checks)
  - `references/evolution-log.md` (this entry)
- **Snapshots:**
  - `SKILL.md.bak-2026-06-17`
  - `references/canonical-markdown-rules.md.bak-2026-06-17`
- **Recurrence count:** Candidate D has prior same-substance memory evidence;
  log recurrence treated as first in append-only evolution log for this exact
  rule. Candidates A-C are first.
- **Active-context staleness:** editing the repo file does not change the
  currently-loaded skill text; recommend a fresh session to exercise the
  improved rules.

## 2026-06-23 — add_new + strengthen: adjacent-figure-merge gate (md split-figure root cause)

- **Trigger (verbatim user message):** "47页相邻三张图怎么没有并排放？难道是技能校验门这里还有漏洞？49页末和50页初这两张也是相邻的应该并排放，不知道是不是 md 格式错误？还有 52页末两张图" + "62页末两张图没有并排放"
- **Classification:** `missing` (rework surfaced downstream in scan skill, but root cause was rewrite producing split figures)
- **Provenance:** `(extracted)` — full session transcript in-context.
- **Root-cause analysis:** `source-transcript.md` (canonical output of this skill) emitted 5 groups of logically-grouped images as adjacent independent `<figure>` blocks (e.g. 对偶性质图1/2/3, 内切圆图1/2, 例题4示意图1/2, 仅一个交点情形5图1/2, 第三定义图1/2), each a single-image figure separated only by blank lines. The existing rule `references/canonical-markdown-rules.md:281` ("Adjacent images should be merged") existed but had **no executable gate** — `lint_multi_image_figures` only checks multi-image *inside one* figure, so single-image figures side-by-side passed silently. This is the same "rule exists, no executable gate" gap pattern as scan skill's C24→C27 (2026-06-17 discard was a mis-diagnosis). The downstream scan skill's C27 side-by-side gate could not catch it either, because the images were never grouped in the first place.
- **Gate verdict:** `add_new` (Gate 1 PASS general — any multi-view/sub-figure group / Gate 2 `new` for the executable gate, `strengthen` for the rule text / Gate 3 principle — structural layout correctness, verifiable)
  - Gate 2 evidence (rule text): `canonical-markdown-rules.md:281` existed ("should be merged") but was guidance only.
  - Gate 2 evidence (gate): grep `lint_adjacent|adjacent_figures` in `validate_canonical_markdown.py` → no hits before this change.
  - Dev Eval (non-regression): `python3 -m pytest tests/ -q` → 76 passed (was 75; +1 new regression test). New lint verified to (a) catch a minimal split-figure md and (b) NOT flag prose-separated independent figures.
- **Pairwise conflict:** fast path (1 candidate).
- **Landing zone:** `scripts/validate_canonical_markdown.py` (new `lint_adjacent_figures_must_merge`, wired into dispatch); `references/canonical-markdown-rules.md:281` (rule hardened, "should"→"MUST", notes enforcement); `SKILL.md` Step 6 (new judgment self-check item); `tests/test_validate_canonical_markdown.py` (regression test).
- **Strongest reason NOT to add:** the rule text already existed; arguably model should just follow it. **Counter:** the user empirically hit the failure twice (this session + the rule's pre-existence proves it was never reliably followed), and the scan-skill C24→C27 history shows "guidance without a gate" repeatedly fails. An executable gate is the durable fix.
- **Outcome:** APPROVED (user selected "rewrite: 加相邻图合并校验门（核心）").
- **Files written:**
  - `scripts/validate_canonical_markdown.py` (new `lint_adjacent_figures_must_merge` + dispatch wiring)
  - `references/canonical-markdown-rules.md` (rule line 281 hardened)
  - `SKILL.md` (Step 6 self-check "Adjacent figures merged")
  - `tests/test_validate_canonical_markdown.py` (regression test)
- **Snapshots:**
  - `SKILL.md.bak-2026-06-23`
  - `scripts/validate_canonical_markdown.py.bak-2026-06-23`
  - `references/canonical-markdown-rules.md.bak-2026-06-23`
  - `tests/test_validate_canonical_markdown.py.bak-2026-06-23`
- **Recurrence count:** first for the executable gate; the rule text existed since 2026-06-16 but was never enforced.
- **Active-context staleness:** editing the repo file does not change this session's loaded skill text; recommend a fresh session to exercise the improved gate.
- **Discarded candidate (this session):** "禁止 [!note] '已在上面保留，不重复抄录' 占位符 callout" — classified `missing` but Gate 1 borderline (single-document content judgment, not a generalizable class) → user did not select it. Substance: redundant-summary placeholder callouts should be silently omitted rather than emitted as `[!note]`. Not written.

---

## 2026-06-28 — batch: 3 lessons from deepseek-v4-flash stress test

- **Trigger (verbatim user message):** "C:\Users\lt\Desktop\Write\math\资料库 将资料库中除了 agents.md 之外，其他所有 Markdown 的例题引用块，都按照你的格式要求去操作。你调用 opencode-go 的 deepseek v4 flash 去测试看看普通模型，能否跑通你的规则验证，你通过不断loop迭代，将技能进化到完美。" → then "轻量直改" (approve lightweight landing) → then "可以" (approve archiving to this log).
- **Source of evidence (unusual):** NOT a user rework on a real transcript run. The evidence came from a **deliberate stress test**: deepseek-v4-flash (a weaker model) was given a distilled prompt derived from this skill's rules and asked to rewrite 6 adversarial fixtures (5 single-defect + 1 combined-defect). The judge (`product/2026-06-28-skill-stress-test/judge.py`) scored outputs against validator + golden + content-integrity checks. So provenance is `(stress-test-extracted)`, not `(extracted)` from a live rework. This is noted explicitly per the Hard Contract's provenance discipline; the lessons are still evidence-backed (real model outputs), just from an experiment rather than a user correction.
- **Provenance:** `(stress-test-extracted)` for all trace fields below. No user-pasted transcript.
- **Round results:** R1 (prompt v1) F1-F5 = 5/5 PASS; R2 (prompt v2) + F6 combined = 5/6 (F6 dropped headings); R3 (prompt v3 literal-echo) = 6/6 structural pass (heading defect fixed; F6's residual flag was a fixture-design QA-ordering artifact, not a rewrite defect).

### Lesson A — `strengthen`: document headings preserved verbatim during rewrite (the headline finding)

- **Classification:** `missing` → `strengthen` (rule was implicit in template, not stated + no executable guard step).
- **Gate verdict:** `strengthen` (Gate 1 PASS general — any multi-section document / Gate 2 strengthen — `question-block-rewrite-guide.md` Subagent Template assumed context preservation but gave no explicit copy step / Gate 3 principle — structural completeness, verifiable).
  - **Stress-test evidence (the crux):** deepseek-v4-flash on F6 (combined: `# 导数综合` + `## 第一节 经典例题` + 2 questions) **stably dropped ALL `#`/`##` headings** under prompt v1 AND v2 — even v2's dedicated "preserve all headings" emphasis rule did NOT fix it. Only **prompt v3's literal-echo step** ("scan every `#` line, then copy each verbatim into the output") moved `heading_preservation` check from FAIL → PASS. Provenance: `round-2/F6-combined-mess.json` (heading dropped), `round-3/F6-combined-mess.json` (heading preserved).
  - **Root cause:** weaker models frame "rewrite the question blocks" as "output ONLY the question blocks", silently discarding section titles. Mere emphasis is ignored; an explicit executable copy step is what works.
- **Pairwise conflict:** fast path (≤3 candidates).
- **Dev Eval:** 73/73 pytest pass after change (pure doc edit; no lint logic touched). Heading-preservation has no automated lint yet — this lesson landed as a subagent guard step + self-check, not a validator gate (heading-drop is content-loss, not a structural regex catch). Honest framing: the guard reduces but cannot eliminate the defect for the weakest models.
- **Landing zone:** `references/question-block-rewrite-guide.md` (new "Document headings preserved verbatim" rule at top of Rewrite Format + new Step 0 literal-echo in Subagent Template + new Self-Check item); `references/canonical-markdown-rules.md` (Page And Heading Shape: new bullet cross-referencing the guard step); `SKILL.md` (no change — already implies full-document output).
- **Strongest reason NOT to add:** the main orchestrating model is strong and rarely drops headings, so this may be over-indexing on one weak-model failure. **Counter:** the rewrite is dispatched to subagents (per the template), which may be weaker models; the explicit copy step is cheap insurance and the stress test proved emphasis alone fails.
- **Outcome:** APPROVED (user "轻量直改" then "可以").

### Lesson B — `strengthen`: Step 4 hard gate distinguishes rewrite-structure lints from formula-normalization lints

- **Classification:** `missing` (no existing guidance on sorting validator FAIL lines by family).
- **Gate verdict:** `strengthen` (Gate 1 PASS general — any validator failure / Gate 2 strengthen — `SKILL.md` Step 4 listed all lints flat with no family distinction / Gate 3 principle — diagnostic correctness, prevents infinite rework loops).
  - **Stress-test evidence:** F4 output was flagged `FAIL: \dfrac inside sqrt should be \tfrac (nested fraction rule)`, but this is a formula-normalization lint OUTSIDE the rewrite's scope — the rewrite prompt says "preserve every LaTeX construct verbatim", so the model keeping `$\sqrt{1+\dfrac{1}{4}}$` intact is CORRECT and must not be sent back to "re-run the rewrite". Provenance: `round-1/F4-analysis-lump.json` (validator out-of-scope), judge.py `classify_validator_messages` splits in-scope vs out-of-scope.
- **Pairwise conflict:** none vs Lesson A (different files/sections).
- **Dev Eval:** N/A — diagnostic-guidance text, no output lint.
- **Landing zone:** `SKILL.md` Step 4 (new "Two lint families — diagnose them separately" paragraph after the title-line lint bullet, listing the two families with member lints).
- **Strongest reason NOT to add:** arguably an agent should already know formula lints ≠ rewrite lints. **Counter:** the stress test shows the conflation is a real trap (F4 would have been sent back to re-run Step 2.7 over a formula lint it was told to preserve); explicit family split prevents the loop.
- **Outcome:** APPROVED (user "轻量直改").

### Lesson C (NOT a skill change — judge-instrumentation finding, recorded for traceability)

- **Finding:** `$`-count conservation is too strict a fidelity check for real rewrites — a faithful rewrite may restructure (inline ↔ display `$$`), changing the raw `$` count without losing content. The stress-test judge iterated 3× (strict $count → ±4 tolerance vs golden → **formula-content-preservation**: extract every meaningful `$...$` from the fixture and check presence in output). Golden calibrated 5/5 PASS. This is a **test-harness design lesson** (lives in `product/2026-06-28-skill-stress-test/judge.py`, NOT in the skill), recorded here only so future stress tests reuse the calibration.
- **Outcome:** NOT written to skill files. Recorded for trace.

- **Files written (this session, all 3 = commit d4c110f):**
  - `references/question-block-rewrite-guide.md` (Lesson A: rule + Step 0 + Self-Check)
  - `SKILL.md` (Lesson B: two-lint-family paragraph in Step 4)
  - `references/canonical-markdown-rules.md` (Lesson A: Page And Heading Shape bullet)
- **Snapshots:**
  - `SKILL.md.bak-2026-06-28`
  - `references/canonical-markdown-rules.md.bak-2026-06-28`
  - `references/question-block-rewrite-guide.md.bak-2026-06-28`
- **Recurrence count:** first for heading-preservation; first for lint-family distinction.
- **Active-context staleness:** editing the repo file does not change this session's loaded skill text; recommend a fresh session to exercise the improved guard step against a weak model.
