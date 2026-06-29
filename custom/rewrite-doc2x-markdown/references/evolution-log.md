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

---

## 2026-06-29 — batch: 4 lessons (A–D) from 复数 ch07 i/1 OCR session

Session cleaning `product/2026-06-26-mst-bixiu2-ch07-复数/source-transcript.md` produced
a user-reported OCR-symbol defect plus two follow-up correctness/consistency findings.
The trigger was the user pasting an `i×i=-1` / `(-i)×(-i)=1` block and suspecting an
OCR `i`/`1` swap. Four candidates extracted, all approved by user ("上一轮的四个候选也强化进去").

- **Trigger (verbatim user messages):**
  - U2: "[pasted i×i=-1 / (-i)×(-i)=1 block] 这一块似乎有问题 OCR 的时候把 i 这个虚数单位识别为1了，你看看是不是这样，排查下其余所有的内容，可以让 deepseek 去全面排查。"
  - U3: "是这样的吗？...我把1 改成 i 了，我以为是正确的，结果是错的吗？然后就是这里面有的 i 是 \mathrm{i} 有的不是，有的甚至没有被 包裹在 $ 符号里，将他们统一为 \mathrm{i}"
- **Provenance:** `(extracted)` — full session transcript in-context.
- **Key correction (U3):** the user initially *edited* `-1` → `-i` believing it correct; byte-check against raw (`page-transcript.raw.md:684` = `(-1)×(-1)=1`) + math-sense (`(-i)×(-i)=i²=-1`, not `1`) confirmed the raw `-1` was right. This became the evidence for Candidate C (active math-sense audit) and reframed Candidate A.

### Candidate A — `strengthen`: OCR confusion list add `i`(imaginary unit) ↔ `1`

- **Classification:** `rework` → `strengthen`.
- **Gate verdict:** `strengthen` (Gate 1 PASS general — any complex-number/algebra/trig doc / Gate 2 strengthen / Gate 3 principle — verifiable OCR char fidelity).
  - Gate 2 evidence: `references/proofreading-checklist.md:36-42` listed `l/1/|`, `O/0`, `S/5`, `B/8` but **omitted** `i`(imaginary)↔`1` — the exact pair that failed this session.
  - Adversarial: "the list already has `l/1`." Counter: `i` is a different glyph and the single highest-value swap in complex-number docs (corrupts every formula); the user empirically hit it.
- **Landing zone:** `references/proofreading-checklist.md` (added bullet under English/math typos, with the high-risk complex-number context note).
- **Strongest reason NOT to add:** arguably covered by general "verify against page image". Counter: an explicit high-risk pair is what makes the proofreader actually look; implicit coverage failed this session.

### Candidate B — `add_new`: `\mathrm{i}` normalization rule

- **Classification:** `missing` → `add_new` (Gate 3 was **borderline** — surfaced explicitly, user approved).
- **Gate verdict:** `add_new` (Gate 1 PASS general / Gate 2 `new` — grep `\mathrm{i}|虚数单位统一` → 0 hits in skill / Gate 3 borderline→approved).
  - Gate 3 borderline reasoning: italic `i`(variable) vs upright `\mathrm{i}`(constant) is math-typography consensus, BUT the skill previously enforced `\mathrm{}` on no other single symbol — so this is a *new* typographic standard, not a restatement. Surfaced per Hard Contract; user approved.
  - Adversarial: "preference, not principle." Counter: the inconsistency is a real readability defect (Doc2X emits `i` 3 ways: `\mathrm{i}`, bare `i`, bare `i` in prose), and the user explicitly requested it; lands as a doc-scoped rule with a self-check, not a validator regex.
- **Landing zone:** `references/canonical-markdown-rules.md` (new "## Imaginary-Unit Notation (`\mathrm{i}`)" section after Punctuation Consistency).
- **Strongest reason NOT to add:** single-symbol `\mathrm{}` mandate has no precedent in the skill. Counter: scoped to imaginary-unit docs only; rule is model-enforced with a self-check, no validator coupling.

### Candidate C — `add_new`: active math-sense consistency audit (Step 2)

- **Classification:** `missing` → `add_new`.
- **Gate verdict:** `add_new` (Gate 1 PASS general — any OCR math doc / Gate 2 `new` — grep `math-sense|数理自洽|consistency check` → 0 hits; F4 covers *reactive* byte-check, not *active* audit / Gate 3 principle — math correctness is the highest-fidelity concern).
  - Session evidence: raw `page-transcript.raw.md:488` `i^{10+10+1}` (garbled exponent) and `:447` `(i²)^{505}=-2^{1010}` (sign/factor error) — both transcription-faithful but mathematically impossible; fixed by math-sense, not by raw trust.
  - Adversarial: "hard to mechanize." Counter: it is the *active* form of F4; the session proved 2 real formulas needed it; framed as a model check with a `[TO VERIFY]` escape, not a validator.
- **Landing zone:** `SKILL.md` Step 2 (new key check #7).
- **Strongest reason NOT to add:** F4 already demands byte-level verification. Counter: F4 is *reactive* (only when a user complains); C is *proactive* (scan every chain), and the session showed 2 defects that no user complaint had surfaced.

### Candidate D — `add_new`: validator math-stripper glitch note (Step 4)

- **Classification:** `missing` → `add_new`.
- **Gate verdict:** `add_new` (Gate 1 PASS general — any validator run over `\mathrm{}`-bearing analysis / Gate 2 `new` — grep `stripper.*glitch|prose.*count.*mathrm` → 0 hits; 2026-06-28 Step-4 lint-family note covers formula-vs-rewrite, not this counter glitch / Gate 3 principle — diagnostic correctness prevents rework loops).
  - Session evidence: validator reported `line 665: prose chars=312, limit=300` on a line whose true prose was ~15 chars — the math-stripper mis-split on `\mathrm{i}\sin`, counting LaTeX fragments as prose. Confirmed by byte-diffing line 665-666 before/after (only `i`→`\mathrm{i}` changed; prose unchanged).
  - Adversarial: "single validator bug, too narrow." Counter: it triggered a real false FAIL and would have caused a wasted re-run-Step-2.7 loop; a 4-line note stops the bleed.
- **Landing zone:** `SKILL.md` Step 4 (new "Known validator glitch" paragraph after the two-lint-family paragraph).
- **Strongest reason NOT to add:** arguably the validator should be fixed, not documented. Counter: the note is the immediate止血 while the validator fix is deferred; the note also tells the model the correct *structural* fix (blank line between sub-answers) without deleting `\mathrm{}`.

### Batch metadata

- **Pairwise conflict check:** 4 candidates, all 6 pairs checked (A↔B detect-then-render; A↔C char-vs-chain; A↔D unrelated; B↔C render-vs-correctness; B↔D rule-vs-tool; C↔D unrelated). No conflicts.
- **Dev Eval:** `py -3 -m pytest tests/ -q` → **85 passed** (unchanged from baseline; pure doc edits). Validator on the corrected source-transcript.md → `OK` (exit 0).
- **Outcome:** APPROVED (user "上一轮的四个候选也强化进去").
- **Files written:**
  - `references/proofreading-checklist.md` (Candidate A)
  - `references/canonical-markdown-rules.md` (Candidate B)
  - `SKILL.md` (Candidate C: Step 2 check #7; Candidate D: Step 4 glitch note)
  - `references/evolution-log.md` (this entry)
- **Snapshots (same-day, after the OpenCode-agent wiring snapshots):**
  - `SKILL.md.bak-2026-06-29-2`
  - `references/proofreading-checklist.md.bak-2026-06-29`
  - `references/canonical-markdown-rules.md.bak-2026-06-29-2`
- **Recurrence count:** All 4 first occurrence (no prior `i/1` OCR, `\mathrm{i}`, math-sense, or stripper-glitch entries in this log).
- **Verification summary:** Dev Eval machine-verified (pytest 85 pass + validator OK) for non-regression; the 4 lessons themselves are auditable-evidence-only (doc/rule edits, no new lint logic) — Candidate D is a *note about* a validator glitch, not a fix to the validator.
- **Active-context staleness:** editing the repo file does not change this session's loaded skill text; recommend a fresh session to exercise the improved rules.

---

## 2026-06-29 — progressive-disclosure refactor (SKILL.md 514 → 229 lines)

- **Trigger (verbatim user message):** "使用 skill-creator 做一次技能的渐进式披露的结构的梳理，避免主 skill.md 过于臃肿，影响效果。"
- **Classification:** `style-pref` (structural cleanup) → executed directly via `skill-creator` methodology, NOT a rule candidate. This is a *refactor* (move content, preserve behavior), recorded for traceability. (skill-evolution's gate pipeline is for rule candidates; a pure restructure is logged as an event, not gated.)
- **Provenance:** `(extracted)` — full session in-context.
- **Problem:** SKILL.md had grown to **514 lines / 45.5KB**, exceeding the `skill-creator` Layer-2 target of <500 lines. Bloat sources: F1–F5 (~45 lines), Step 1-GATE bash block (~40 lines), Step 6 self-check (~45 lines), Parallel Chunking Workflow (~55 lines) — all inlined despite the skill's established "defer detail to `references/`" pattern.
- **Method (per `skill-creator` progressive-disclosure guidance):** moved 4 large inlined blocks to **new standalone Layer-3 reference files** (one concern per file, matching the existing `auto-fix-rules.md`/`proofreading-checklist.md` pattern):
  1. `references/forbidden-patterns.md` — F1–F5 (full reasoning + code examples)
  2. `references/auto-fix-gate.md` — Step 1-GATE 7 mandatory checks (commands)
  3. `references/self-check.md` — Step 6 checklist (10 evidence + 18 judgment items; added the Imaginary-unit notation check from this session's Candidate B)
  4. `references/parallel-chunking.md` — Parallel Chunking Workflow (chunk planning + dispatch table + assembly)
- **SKILL.md now a lean orchestrator**: kept the workflow skeleton (Steps 0–7), Hard Contract, Preconditions, Inputs — each step reduced to its orchestration logic + a one-line pointer to its reference file. Added a consolidated "References (read on demand, per step)" list at the top.
- **Content-preservation verification:**
  - All 5 Forbidden Patterns present (5 `## F[1-5]` headings in forbidden-patterns.md)
  - All 10 Hard Contract items still in SKILL.md
  - All 13 workflow step headings still in SKILL.md (Step 0, 0-A, 1, 1-GATE, 2, 2.5, 2.7, 3, 4, 5, 6, 6.5, 7)
  - This session's Candidate C (math-sense) and D (stripper-glitch) both still present in SKILL.md
  - All 12 reference pointers resolve (the one "MISSING" — `frontmatter-spec.md` — is a correct cross-skill ref to `scan-pdf-to-print-html/references/`, which exists)
- **Dev Eval:** `py -3 -m pytest tests/ -q` → **85 passed** (unchanged — pure doc move, no lint logic touched).
- **Outcome:** APPROVED (user selected "激进：拆 4 块" + "新建独立文件").
- **Files written:**
  - `SKILL.md` (rewritten: 514 → 229 lines / 45.5KB → 21.1KB)
  - `references/forbidden-patterns.md` (new)
  - `references/auto-fix-gate.md` (new)
  - `references/self-check.md` (new)
  - `references/parallel-chunking.md` (new)
  - `references/evolution-log.md` (this entry)
- **Snapshot:** `SKILL.md.bak-pre-refactor-20260629-125509` (full pre-refactor state).
- **Recurrence count:** first structural refactor of SKILL.md (prior entries added/edited rules; this one restructured layout).
- **Active-context staleness:** editing the repo file does not change this session's loaded skill text; the refactored SKILL.md (229-line orchestrator + pointers) takes effect in a fresh session.

---

## 2026-06-29 — batch: 5 candidates (C1-C4, C7, C8) from ch09 统计 session

Session rewriting `product/2026-06-26-mst-bixiu2-ch09-统计/source-transcript.md` produced
≥7 user rework corrections. The user's framing was strategic: "用哪种方案从根上避免——
多Agent / 代码验证 / 硬约束？" Analysis classified the 7 corrections into **3 root causes**
and chose a defense per root cause ("万箭齐发" — multiple methods, divided by root cause).
Five candidates landed; C5/C6 discarded.
- **Trigger (verbatim user messages):**
  - U1: "选项没有转为表格，还有选项错误的加入 ## 标题…需要全面排查…弄一个专门的子代理"
  - U2: "例题缺少的图我给换了一个本地的你记得上传到图床"
  - U3: "${60}\% , {60}\% …公式内逗号问题并没有解决…非常多"
  - U4: "例题19公式过长也没有用 array 对齐换行"
  - U5: "…=$ 0.0296 为什么这个后面不在公式里…公式总是不完整"
  - U6: "③相应的频率=样本容量…原文是频数除以相应的频率等于样本容量"
  - U7: "$\lbrack {5.31}, {5.33})…区间之间分隔逗号还有漏的" + "总结…分析到底应该采取哪种方案"
- **Provenance:** `(extracted)` — full session in-context.
- **Root-cause → defense mapping (the core analysis):**
  - **Root cause A (Step 2.7 skipped at dispatch)** — U1/U2/U3(part): rule "2.7 MANDATORY" existed but was ignored. Adding a louder rule is ineffective for `ignored` (landing-zone-rules.md). → **defense = ③dispatch-time guard** (candidate C7), NOT a louder rule.
  - **Root cause B (structural defect, guidance exists but no executable gate)** — U3/U5/U7/U4: self-check had judgment items but no lint. → **defense = ②code validation** (candidates C1/C2/C3/C4), the highest-value fix. Matches evolution-log's recurring lesson (2026-06-23 adjacent-figure, 2026-06-28 heading): "self-check alone fails; executable gate is the durable fix."
  - **Root cause C (raw OCR math-wrong, no math-sense)** — U6: code validators cannot judge math truth. → **defense = ①multi-agent cross-examination** (candidate C8), a fresh subagent re-derives formulas.

### Candidate C1 — `add_new`: lint_formula_dangling_tail (formula truncation)
- **Classification:** `missing` → `add_new`.
- **Gate verdict:** add_new (G1 PASS — any OCR math doc / G2 `new` — grep `dangling|腰斩|truncat` → only proofreading-checklist.md:76 cross-page note, no output lint / G3 principle — formula completeness is verifiable).
  - Session evidence: ch09 L761 `${s}^{2}=...= 0.0296` — the `0.0296` tail leaked out of `$` as prose because the span closed at `=$`.
- **Landing zone:** `scripts/validate_canonical_markdown.py` (new `lint_formula_dangling_tail`, registered in dispatch); `tests/test_validate_canonical_markdown.py` (regression test).
- **Strongest reason NOT to add:** naive regex may misfire on `$f(x,y)$` or `\left\lbrack...\right\rbrack`. **Counter:** the lint uses a conservative heuristic (span ends with a dangling operator AND the text after `$` looks like a stray value, with a prose allowlist); ch09 verified 0 false-positives on the corrected spans.
- **Outcome:** APPROVED (user "全要 C1+C2+C3").

### Candidate C2 — `add_new`: lint_list_inside_math (list of units in one span)
- **Classification:** `missing` → `add_new`.
- **Gate verdict:** add_new (G1 PASS / G2 `new` — rule canonical-markdown-rules.md:200 listed `$m$, $n$` and single `$(0,1)$` but no multi-interval-list example and no lint / G3 principle).
  - Session evidence: ch09 L349/L363/L630 — multiple intervals crammed in one `$...$` (`$\lbrack 5.31,5.33), \lbrack 5.33,5.35), \cdots$`).
- **Landing zone:** `scripts/validate_canonical_markdown.py` (new `lint_list_inside_math`); `references/canonical-markdown-rules.md` (multi-interval-list example); `tests/` (regression).
- **Strongest reason NOT to add:** single interval `$(0,1)$` or function arg `$f(x,y)$` could false-positive. **Counter:** the lint requires a REPEATING unit (≥2 openers separated by commas), so a single unit never fires; ch09 single-interval verified unflagged.
- **Outcome:** APPROVED.

### Candidate C3 — `strengthen`: comma-placement rule + self-check gain multi-interval-list sub-case
- **Classification:** `rework` → `strengthen`.
- **Gate verdict:** strengthen (G1 PASS / G2 strengthen — self-check item 28 + canonical-rules:200 existed but only covered `$m$, $n$`, not multi-interval lists / G3 principle).
- **Landing zone:** `references/canonical-markdown-rules.md:200` (multi-interval-list sub-bullet); `references/self-check.md` (item 28 area — new "list-of-units" check).
- **Outcome:** APPROVED.

### Candidate C4 — `add_new`: lint_long_inline_formula (multi-equality chain, coarse)
- **Classification:** `missing` → `add_new`.
- **Gate verdict:** add_new (G1 PASS / G2 `new` — self-check item 36 existed but no lint / G3 principle, borderline — aligned quality is semantic, so lint is COARSE).
  - Session evidence: ch09 例19 s₁²/s₂² long sums not folded.
  - **Calibration incident:** first version flagged any `$...$` >60 chars → 16 ch09 hits, most were legitimate single-`=` sums (false-positive noise). Tightened to "length>90 AND ≥2 equalities" (a chain), which targets only `a=b=c` chains that genuinely need `\begin{aligned}`. A single long expression is a legit inline span.
- **Landing zone:** `scripts/validate_canonical_markdown.py` (new `lint_long_inline_formula`); `references/canonical-markdown-rules.md` (new multi-equality-chain rule); `references/self-check.md` (item 36 strengthened); `tests/`.
- **Strongest reason NOT to add:** when-to-fold is semantic. **Counter:** coarse "long chain" signal is enough to point the model at the spot; context-judgment still applies (lint message says so).
- **Outcome:** APPROVED (user "lint化 粗粒度").

### Candidate C7 — `add_new`: Step 2-Dispatch declare-which-steps guard
- **Classification:** `missing` (process/dispatch) → `add_new`.
- **Gate verdict:** add_new (G1 PASS — any dispatched rewrite / G2 `new` — grep `dispatch.*declare|2\.5.*2\.7` → no dispatch-time step-naming rule (the "2.7 MANDATORY" rule is step-level, not dispatch-level) / G3 principle — the 2026-06-29 session empirically skipped 2.7 at dispatch).
  - Diagnosis: this is root cause A — the rule existed and was `ignored`. Per landing-zone-rules.md, a louder rule rarely fixes `ignored`; the fix is forcing the dispatcher to NAME the steps. So this is a dispatch-time guard, not a louder "2.7 is mandatory".
- **Landing zone:** `SKILL.md` (new "Step 2-Dispatch" section between Step 1-GATE and Step 2.5, with the document-shape→steps table + the anti-pattern); `references/self-check.md` (new "Dispatch declared its steps" check).
- **Strongest reason NOT to add:** may over-constrain. **Counter:** the failure (running only 2.5) really happened; a one-line dispatch declaration is cheap insurance.
- **Outcome:** APPROVED (user "加显式dispatch约束").

### Candidate C8 — `add_new`: Step 2.8 Math-sense cross-review subagent
- **Classification:** `missing` → `add_new`.
- **Gate verdict:** add_new (G1 PASS — any formula-heavy chapter / G2 `new` — Step 2 math-sense is the rewriter's INLINE check; C8 is a SEPARATE cross-examining subagent, a distinct mechanism (multi-agent defense ①) / G3 principle — math truth is the highest-fidelity concern).
  - Session evidence: ch09 `③频率=样本容量` survived all structural lints (structure was clean; only re-deriving the math caught it as OCR-wrong).
- **Landing zone:** `SKILL.md` (new "Step 2.8" section after Step 2.7, before Step 3); `references/self-check.md` (new "Math-sense cross-review ran" check).
- **Strongest reason NOT to add:** a strong rewriter already does math-sense inline. **Counter:** the rewriter is anchored to its own assumptions and can rationalize past a math error (it trusted the raw OCR's `频率=样本容量`); a fresh subagent is not so anchored. This is the user's explicit "交叉质询" request and the only defense against root cause C (code validators provably cannot judge math truth).
- **Outcome:** APPROVED (user "加交叉审查子代理").

### Discarded candidates
- **C5 (math-sense strengthen)** — `duplicate`: 2026-06-29 prior batch already added the Step 2 inline math-sense check. This session's U6 was an *execution* failure of that existing rule, not a rule gap → routed to C8 (the separate subagent) rather than restating the rule.
- **C6 (Step 2.7 louder rule)** — `duplicate` + `ignored` diagnosis: SKILL.md L139 already marked 2.7 MANDATORY; the failure was dispatch ignoring it, which C7 addresses at the right layer (dispatch, not the rule text).

### Batch metadata
- **Pairwise conflict check:** 7 candidates, all pairs checked; no conflicts. C1/C2/C3 are comma/truncation family but land in different files (lint vs rule vs self-check) — complementary. C7 (dispatch) and C8 (cross-review) target different root causes (A vs C).
- **Dev Eval:** `py -3 -m pytest tests/ -q` → **88 passed** (was 85; +3 regression tests for C1/C2/C4). Validator on ch09 corrected output: dangling-tail & list-inside-math = **0 false-positives** (corrected spans clean); long-inline-formmula flags 16 real multi-equality chains still un-folded in ch09 (lint correctly pointing at unfinished cleanup).
- **Outcome:** APPROVED (user answered the 4 scope questions: C1+C2+C3 全要 / C4 lint化粗粒度 / C7 加dispatch约束 / 根因C 加交叉审查子代理).
- **Files written:**
  - `scripts/validate_canonical_markdown.py` (C1 lint_formula_dangling_tail, C2 lint_list_inside_math, C4 lint_long_inline_formula + all 3 registered in lint_markdown dispatch)
  - `references/canonical-markdown-rules.md` (C3 multi-interval-list sub-bullet + C1 truncation rule + C4 multi-equality-chain rule, all near line 200)
  - `references/self-check.md` (C3 list-of-units + truncation checks; C7 dispatch-declared check; C8 cross-review-ran check)
  - `SKILL.md` (C7 new "Step 2-Dispatch" section; C8 new "Step 2.8" section)
  - `tests/test_validate_canonical_markdown.py` (3 regression tests)
  - `references/evolution-log.md` (this entry)
- **Snapshots (same-day, 3rd):**
  - `SKILL.md.bak-2026-06-29-3`
  - `scripts/validate_canonical_markdown.py.bak-2026-06-29-3`
  - `references/canonical-markdown-rules.md.bak-2026-06-29-3`
  - `references/self-check.md.bak-2026-06-29-3`
  - `references/question-block-rewrite-guide.md.bak-2026-06-29-3` (snapshot taken, not edited)
  - `references/parallel-chunking.md.bak-2026-06-29-3` (snapshot taken, not edited)
  - `references/opencode-agent-invocation.md.bak-2026-06-29-3` (snapshot taken, not edited)
- **Recurrence count:** All first occurrence as rules. The *pattern* "guidance exists, no executable gate" recurs across 2026-06-23 / 2026-06-28 / this session — C1/C2/C4 are the third strike of that pattern; this run finally mechanized it for formula-comma/truncation/long-chain rather than relying on self-check.
- **Verification summary:** Dev Eval machine-verified (pytest 88 pass + ch09 validator false-positive check). The 5 lessons are: C1/C2/C4 = executable lint (machine-enforced); C3 = rule+self-check (auditable-evidence); C7/C8 = process/subagent guards (auditable-evidence only — no automated gate, honest framing per Verification Ceiling).
- **Active-context staleness:** editing the repo file does not change this session's loaded skill text; the new lints (C1/C2/C4) take effect immediately when the validator script runs, but the Step 2-Dispatch (C7) and Step 2.8 (C8) subagent guards take effect in a fresh rewrite session.
