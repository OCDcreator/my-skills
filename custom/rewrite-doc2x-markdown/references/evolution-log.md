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

---

## 2026-06-30 — 概率 chapter (必修二10：概率) post-task retro

**Session provenance:** CAPTURE extracted from the orchestrator's in-context session (not a subagent). Trace fields tagged `(extracted)`. The probability job ran rewrite-doc2x-markdown (Phase 1, 3 sub-passes) → a4-novak-html-cover (Phase 2) → scan-pdf-to-print-html (Phase 3) → 3 parallel format reviews, all via `opencode run --model opencode-go/deepseek-v4-flash` subagents. All 3 targets are under `custom/` (soft-linked from `my-skills/custom/`).

### Candidate B9 — `strengthen`: `--fix` vs frontmatter corruption (3× recurrence in one job)
- **Classification:** `rework` → `strengthen`.
- **Gate verdict:** strengthen (G1 PASS — any frontmatter-bearing `source-transcript.md` / G2 `strengthen` — existing rule at `SKILL.md:211` "Known limitations: `--fix` may corrupt `---` → `__________` (Rule 5) — verify separators after" was too passive / G3 principle — silent data corruption that breaks downstream pagination).
  - **Evidence (3× recurrence in one job, extracted):** Phase 1b subagent ran `--fix` → frontmatter fences `---` became `__________` (1st); orchestrator hand-fixed. Phase 1c subagent ran `--fix` again → fences corrupted again (2nd); orchestrator hand-fixed. During this retro's own Dev Eval, orchestrator ran `--fix` once more → fences corrupted a 3rd time (3rd); hand-fixed. Each corruption made `parse_frontmatter()` return `{}` — `pagination-level`/`cover` intent silently lost, which would have broken the user's core "每讲从新页" requirement.
  - **Diagnosis:** `weak` — rule existed (L211) but was a passive "verify after" note, not an actionable "don't run --fix blindly / re-assert fences" instruction. The existing line lumped frontmatter fences together with generic section separators, hiding that frontmatter corruption is *silent* (no error, just empty parse).
- **Landing zone:** `SKILL.md` Step 4 (split the old "Known limitations" line: keep the `fix_callout_prefixes.py` clause as-is; expand the `--fix` clause into a dedicated "**`--fix` vs frontmatter — do not learn this the hard way**" block with the strip-and-restore / re-assert-and-reparse procedure + the post-`--fix` verification requirement). Tier-1 cascade: existing Step 4 section; SKILL.md at 266 lines (not near cap).
- **Strongest reason NOT to add:** makes Step 4 longer. **Counter:** 3 recurrences in one job (including by the orchestrator who *knew* the rule) proves the passive warning is insufficient; an actionable procedure is cheaper than the rework it prevents.
- **Outcome:** APPROVED (user "全部批准").

### Candidate C10 — `add_new`: back up before rewriting
- **Classification:** `missing` → `add_new`.
- **Gate verdict:** add_new (G1 PASS — any in-place rewrite of the sole canonical transcript / G2 `new` — grep `backup|备份|\.bak|snapshot|copy.*before` across SKILL.md = 0 hits; none of the 12 Hard Contract items mandate a backup / G3 principle — guard against irreversible edits; user explicitly required it: "清洗前先备份该文件，避免造成不可挽回的错误").
  - **Evidence (extracted):** the orchestrator created `source-transcript.md.bak-preclean-20260629` before Phase 1; that backup is what made the 3 frontmatter re-fixes safe (always restorable). User message U1 verbatim required the backup. The skill had no such rule, so a less cautious subagent could skip it.
- **Landing zone:** `SKILL.md` Hard Contract (new item after the "PDF outline" rule, before the "Forbidden Patterns" section). Tier-1 cascade: the rule governs main-workflow safety → belongs in SKILL.md, and Hard Contract is the right home for an "always do this" mandate.
- **Strongest reason NOT to add:** backups are "common sense", may be redundant. **Counter:** user explicitly required it AND the backup concretely rescued 3 corruptions this job; an explicit rule prevents a future subagent from skipping the step. The cost (one `cp`) is negligible vs the cost (irrecoverable canonical transcript).
- **Outcome:** APPROVED (user "全部批准").

### Discarded candidates
- **A (orchestrator over-asking / plan-mode instead of working)** — `discard` (Gate 1 fail + Gate 3 preference): the user's complaint ("他不是主动去工作，而是立刻进入规划模式，然后就开始问我问题") is an **orchestrator/host behavior**, not in scope of any of the 3 content skills (rewrite/cover/scan). grep across all 3 SKILL.mds for "plan mode / ask / autonomy" = no rule to strengthen. The correct home is the host system-prompt / skill-creator's "Improving the skill" guidance ("if the model is doing busywork, cut, don't add"), which is outside `custom/` skill-evolution scope. Discarded per Step 4 row 2 (Gate 1 fail). **Required discard reasoning (per Step 4 row 5):** user quote cited; why it is out-of-scope (orchestrator layer, not content-skill); existing coverage lives in skill-creator (a different skill); safe to discard because forcing a "don't ask" rule into a content skill would be overfit pollution; recurrence = 0 (first occurrence).

### Batch metadata
- **Pairwise conflict check:** Fast path — 3 candidates, no pairwise check needed. B9 and C10 are complementary (C10 makes B9's failures recoverable; B9 reduces the failures). A is orthogonal (discard).
- **Dev Eval:** `validate_canonical_markdown.py --md <corrected source-transcript.md> --fix` → triggered the **pre-existing Rule-5 frontmatter-corruption bug** (3rd occurrence, hand-fixed) — this is a pre-existing validator bug, NOT a regression introduced by these skill-text edits (the edits change instructions, not validator code). Dev Eval gives no semantic signal here (validator is a structural lint, not a behavior tester) — flagged honestly per Verification Ceiling. The edits are rule-text, auditable-evidence only.
- **Outcome:** APPROVED (user "全部批准" — both B9 strengthen + C10 add_new).
- **Files written:**
  - `SKILL.md` (B9: expanded L211 "Known limitations" into the dedicated "`--fix` vs frontmatter" block at the Step-4 area; C10: new Hard Contract item "Back up before rewriting")
  - `references/evolution-log.md` (this entry)
- **Snapshot (same-day, 1st):** `SKILL.md.bak-2026-06-30`
- **Recurrence count:** B9 = first occurrence *as a strengthened rule* (the underlying `--fix`-corrupts-frontmatter pattern is new to the log; the passive note existed since before 2026-06-29 but was never logged as a lesson). C10 = first occurrence. A = first occurrence (discarded).
- **Verification summary:** No machine verification possible (both edits are instruction text, not executable code). B9 + C10 = auditable-evidence only (the 3× recurrence is extracted session evidence; the backup's rescue role is extracted session evidence). Dev Eval could not confirm non-regression because the pre-existing Rule-5 bug fires on any `--fix` run — this is honestly a validator limitation, not a skill-text regression.
- **Active-context staleness:** editing `my-skills/custom/rewrite-doc2x-markdown/SKILL.md` does not change this session's loaded rewrite-doc2x-markdown skill text (it was loaded at Phase 1). The new rules (C10 backup mandate, B9 frontmatter-safe `--fix` procedure) take effect in a **fresh rewrite session**. Recommend a fresh session to exercise the improved skill.

---

## 2026-06-30 — 9-role refinement chain + path-independent self-check (structural refactor)

**Session provenance:** CAPTURE extracted from the orchestrator's in-context session (not a subagent). Trace fields tagged `(extracted)`. The refactor was driven by user feedback across prior sessions ("3 subagents worked poorly; more single-responsibility subagents worked better") + a `grill-me`/`grilling` interview in this session that resolved the design tree (skeleton layer, role split, executor policy, self-check contract). All targets are under `custom/` (soft-linked from `my-skills/custom/`).

### Retro
- **U1 (verbatim, extracted):** "关于 rewrite 技能，本来是三个子代理，但在之前的两次对话中使用时，发现效果不好。后来我自己增加了更多子代理，测试由单个子代理单独处理文本，效果反而更好，因为任务变得更简单了。所以我需要你根据 [skill-evolution] 技能去重构该 [rewrite-doc2x-markdown] 技能，同时保持 [skill-creator] 的渐进式披露原则。"
- **U2 (verbatim, extracted, grilling correction 1):** "当前的新的代理是否能够涵盖这个重构的流程，我建造的这几个新代理是在旧的代理重写之后产生的，但是其实有一些职能是没有的，比如说像经典的解析块重写就没有。所以我的想法可能是需要把旧的进行拆分。"
- **U3 (verbatim, extracted, grilling correction 2 — executor policy):** "我说的deepseek-v4就是flash" + "就是我可以选择不用子代理只用主代理，原理是一样的…但是当我需要用子代理的时候，才用子代理"
- **U4 (verbatim, extracted, grilling correction 3 — self-check):** "opencode 这些代理自己做完工作后，可以调用 脚本 然后爬一下有没有匹配的错误，这样可以最大化减少返工的情况"
- **U5 (verbatim, extracted, grilling correction 4 — skeleton gap):** "难道没有专门的子代理用于从 raw Markdown 变为 source Markdown 然后才开始有这一连串的子代理开始精修吗？" (rooted in a real gap — verified by Explore agent: SKILL.md:40 used raw as base text directly, no skeleton stage)
- **Provenance:** `(extracted)` — full session in-context. Hard-evidence files (the 3 user-created agents `question-source-merger`/`question-options-to-table`/`math-comma-splitter`, timestamps 6/30) confirmed on disk.
- **Root-cause → defense mapping:**
  - **Root cause A (bundled jobs on weak models)** — U1/U2: the legacy `question-block-rewriter` bundled title+options+subparts+analysis; weaker models skipped/collided them. → **defense = single-responsibility role chain** (R1).
  - **Root cause B (missing skeleton)** — U5: raw edited directly, heading-level alignment drifted across roles. → **defense = skeleton role ★** (R4).
  - **Root cause C (no feedback loop)** — U4: validator output non-structured, re-dispatch was prose-only. → **defense = `--only` flag + path-independent per-role self-check** (R5).
  - **Root cause D (over-eager dispatch)** — U3: the skill auto-dispatched by document size, but the user wants the main agent as default. → **defense = main-agent-default policy** (R6).

### Candidate R1 — `strengthen`: Step 2.7 single-agent → 8-role refinement chain
- **Classification:** `rework` → `strengthen`.
- **Gate verdict:** strengthen (G1 PASS — any question-heavy OCR doc / G2 `strengthen` — SKILL.md:160-171 "Method" existed but described single-agent whole-block rewrite; the chain is its decomposition / G3 principle — single-responsibility = verifiable reliability principle, not taste).
- **Landing zone:** new `references/refinement-agent-chain.md` (single source for all 8 roles); SKILL.md Step 2.7 rewritten to point at it (290 lines, under cap). Legacy `question-block-rewrite-guide.md` demoted to fallback.
- **Strongest reason NOT to add:** 8 roles may over-fragment. **Counter:** each role's `--only` self-check pins failures to the exact role; the old bundle had no such attribution. User explicitly requested the split (U1/U2).
- **Outcome:** APPROVED.

### Candidate R2 — `add_new`: opencode-agent-invocation.md register the 9 agents
- **Classification:** `missing` → `add_new`.
- **Gate verdict:** add_new (G1 PASS / G2 `new` — grep `source-merger|options-to-table|comma-splitter` in opencode-agent-invocation.md = 0 hits; "three agents" hardcoded / G3 principle).
- **Landing zone:** `references/opencode-agent-invocation.md` ("three agents" → "nine agents + 1 legacy"; detection command updated; new executor-policy section + per-role self-check section).
- **Outcome:** APPROVED.

### Candidate R3 — `strengthen`: Step 2-Dispatch fine-grained + user-triggered
- **Classification:** `missing` → `strengthen`.
- **Gate verdict:** strengthen (G1 PASS / G2 `strengthen` — Step 2-Dispatch table existed at SKILL.md:130-144 (C7); R3 extends to role-level + corrects the executor trigger / G3 principle).
- **Landing zone:** SKILL.md Step 2-Dispatch rewritten (Decision 1: who executes; Decision 2: which roles; document-shape→roles table).
- **Outcome:** APPROVED.

### Candidate R4 — `add_new`: skeleton role ★ (source-skeleton-builder)
- **Classification:** `missing` → `add_new`.
- **Gate verdict:** add_new (G1 PASS — any doc needing stable heading hierarchy / G2 `new` — grep `skeleton|骨架` across SKILL.md = 0; SKILL.md:40 used raw as base text directly / G3 principle — fills a verified gap, root cause B).
- **Landing zone:** `references/refinement-agent-chain.md` (role ★); new `.opencode/agents/source-skeleton-builder.md`; SKILL.md new Step 1.5.
- **Strongest reason NOT to add:** adds a stage. **Counter:** the gap (U5) is real and verified; heading drift was a documented recurring nuisance.
- **Outcome:** APPROVED.

### Candidate R5 — `add_new`: validator `--only` flag + path-independent self-check
- **Classification:** `missing` → `add_new`.
- **Gate verdict:** add_new (G1 PASS — every refinement role / G2 `new` — `LintMessage` dataclass (`validate_canonical_markdown.py:158-162`) had only `line`/`text`, no category; grep `--only` = 0 / G3 principle — minimizes rework per U4).
- **Landing zone:** `scripts/validate_canonical_markdown.py` (`--only` arg + registry-based filter in `lint_markdown`); `tests/test_only_flag.py` (5 new tests); every role's self-check documented in `refinement-agent-chain.md` + each agent `.md`.
- **Strongest reason NOT to add:** a role could just run full validator and ignore others. **Counter:** the user explicitly wanted scripts agents call themselves (U4); `--only` makes the self-check path-independent and pins FAILs to the owning role — full-validator-everywhere loses attribution.
- **Outcome:** APPROVED.

### Candidate R6 — `strengthen`: main-agent-default (subagents opt-in)
- **Classification:** `rework` → `strengthen`.
- **Gate verdict:** strengthen (G1 PASS / G2 `strengthen` — `parallel-chunking.md` / `opencode-agent-invocation.md` implied auto-dispatch by size; R6 corrects to user-triggered / G3 principle — user's explicit control per U3).
- **Landing zone:** SKILL.md Hard Contract (new "Default executor is the main agent" item); Step 2-Dispatch Decision 1; `opencode-agent-invocation.md` top section; `parallel-chunking.md` dispatch note.
- **Strongest reason NOT to add:** may under-use subagents on big docs. **Counter:** the user is explicit (U3) that the main agent can do the jobs and dispatch is opt-in; auto-dispatch violated their stated preference.
- **Outcome:** APPROVED.

### Discarded candidates
- (none this session — all 6 candidates survived the gate; the grilling corrections were absorbed into R1/R4/R5/R6 rather than spawning separate discards.)

### Batch metadata
- **Pairwise conflict check:** Fast path — 6 candidates, all pairs reviewed; no conflicts. R1 (chain) and R4 (skeleton) are complementary (skeleton is role ★ of the chain). R5 (`--only`) is the enabler for R1's per-role self-check. R6 (executor policy) governs how R1/R2/R4 are invoked. R3 (dispatch) operationalizes R6.
- **Dev Eval:** `py -3 -m pytest tests/ -q` → **93 passed** (was 88; +5 for `test_only_flag.py`). The `--only` filter verified: named subset runs, unknown names abort loudly, default behavior unchanged. Validator non-regression confirmed. The skill-text edits (R1/R2/R3/R4/R6) are instruction text — auditable-evidence only, no machine verification of their *behavioral* effect (Verification Ceiling applies).
- **Outcome:** APPROVED (user approved the plan after 2 revision rounds incorporating the grilling corrections on executor policy + skeleton layer + self-check path-independence).
- **Files written:**
  - `scripts/validate_canonical_markdown.py` (`--only` arg in `build_parser`; `lint_markdown` rewritten to a named `(name, callable)` registry + filter; `main` passes `args.only`)
  - `tests/test_only_flag.py` (NEW: 5 tests — runs-named-only, comma-list, unknown-aborts, default-unchanged, clean-subset-OK)
  - `references/refinement-agent-chain.md` (NEW: the single source — 9-role chain, universal IRON LAW, path-independent self-check contract, role→lint map, per-role logic)
  - `.opencode/agents/source-skeleton-builder.md` (NEW: role ★)
  - `.opencode/agents/question-subparts-splitter.md` (NEW: role ④)
  - `.opencode/agents/ocr-typo-fixer.md` (NEW: role ⑥)
  - `.opencode/agents/sentence-displacement-fixer.md` (NEW: role ⑦)
  - `.opencode/agents/key-point-marker.md` (NEW: role ⑧)
  - `SKILL.md` (References list +refinement-agent-chain pointer; Hard Contract +2 items [main-agent-default, path-independent self-check]; new Step 1.5; Step 2-Dispatch rewritten; Step 2.5 aligned to role ⑤; Step 2.7 rewritten to the chain). 266 → 290 lines.
  - `references/opencode-agent-invocation.md` (top: main-agent-default section; detection cmd 9 agents; "three agents"→"nine agents +1 legacy" table; per-role self-check section; pitfall updated)
  - `references/self-check.md` (+3 items: skeleton-ran, per-role-only-self-check, executor-choice)
  - `references/question-block-rewrite-guide.md` (top: demoted to LEGACY FALLBACK with default-path pointer)
  - `references/parallel-chunking.md` (dispatch note: user-triggered, not auto; references the chain)
  - `references/evolution-log.md` (this entry)
- **Snapshots (same-day, 2nd):**
  - `SKILL.md.bak-2026-06-30-2`
  - `scripts/validate_canonical_markdown.py.bak-2026-06-30`
  - `references/opencode-agent-invocation.md.bak-2026-06-30`
  - `references/self-check.md.bak-2026-06-30`
  - `references/question-block-rewrite-guide.md.bak-2026-06-30`
  - `references/parallel-chunking.md.bak-2026-06-30`
- **Recurrence count:** All 6 first occurrence as rules. The *pattern* "monolithic agent unreliable on weak models → split into single-responsibility roles" is new to the log.
- **Verification summary:** R5 = machine-verified (pytest 93 pass; `--only` filter behavior locked by tests). R1/R2/R3/R4/R6 = auditable-evidence only (instruction text; the role-split, skeleton layer, executor policy, and dispatch rules have no automated behavior tester — honest framing per Verification Ceiling). The 3 user-created agents on disk (`question-source-merger`/`question-options-to-table`/`math-comma-splitter`) are extracted hard evidence that the split direction is what the user wanted.
- **Active-context staleness:** editing `my-skills/custom/rewrite-doc2x-markdown/*` does NOT change this session's loaded rewrite-doc2x-markdown skill text (loaded at session start). The new chain, skeleton role, `--only` self-check, and main-agent-default policy take effect in a **fresh rewrite session**. The `--only` flag itself takes effect immediately when the validator script runs (it is executable code, not loaded skill text). Recommend a fresh session to exercise the improved skill end-to-end.

---

## 2026-06-30 — ch12 session: 3 anti-shortcut lessons + symlink architecture event

**Session provenance:** CAPTURE extracted from the orchestrator's in-context session
(not a subagent). Trace fields tagged `(extracted)`. Session ran the 8-role refinement
chain on `product/2026-06-26-mst-bixiu2-ch12-直线和圆的方程/`, then a user-driven
retro exposed three "lint-ceiling / anti-shortcut" defects, then a follow-up
investigation produced a symlink architecture change for `.opencode/agents/`.

### Candidate L1 — `strengthen`: multi-point/multi-equation formula fusion (③ role blind spot)

- **Trigger (verbatim, extracted):** "$A(0,0), B(3,-2), C(5,1), D(2,3)$ 我发现这种公式中间的逗号，没有被分析出来" + "每一个坐标点本来就是不同的坐标点，你为什么要把它们放到同一个公式当中呢？这没有理由。" (with additional examples `$|AC|=\sqrt{26}, |BD|=\sqrt{26}$` and `$k, l_1$`).
- **Classification:** `rework` — ③ left ~90 fused formulas un-split.
- **Provenance:** `(extracted)` — full session in-context + lint output as hard evidence.
- **Root cause:** `lint_list_inside_math` (added 2026-06-29 C2) only matches **interval-list** patterns (`[a,b), [c,d)`). It is **SILENT** on three other fusion shapes: (a) multiple labeled coordinate points, (b) multiple independent equations, (c) multi-variable lists. The role-③ pass that split nothing returned a clean `--only` self-check (verified: `lint_list_inside_math` on the un-split file reported only line 103's interval-union, missing all point/equation/variable fusions).
- **Gate verdict:** `strengthen` (G1 PASS — any math OCR doc with enumerated objects / G2 strengthen — 2026-06-29 C2/C3 covered interval-list only; the chain reference + math-comma-splitter agent had no point/equation/variable example / G3 principle — formula delimiter hygiene, verifiable by depth-aware splitting).
- **Landing zone:** `references/refinement-agent-chain.md` (③ role: named the 3 fusion shapes + Ceiling note); `.opencode/agents/math-comma-splitter.md` (new A2 section with before/after examples + anti-over-inhibition clause in Critical distinction). NOTE: the agent edits originally landed in the PROJECT copy; the 2026-06-30 symlink migration (below) moved the canonical source to the skill repo `agents/`, so the edits now live in the truth source.
- **Strongest reason NOT to add:** the rule "split enumerated commas" arguably already exists. **Counter:** the lint's silence + the user's 3 distinct shape examples prove the implicit coverage + lint signal were both insufficient; the model empirically skipped all 90.
- **Outcome:** APPLIED during-session (chain ref + agent); logged here for trace.

### Candidate L2 — `strengthen`: anti-shortcut clause (lint-ceiling, applies to ③⑤⑥)

- **Trigger (verbatim, extracted):** "那如果我让子代理跑，他会犯这个错误吗？" + "那你是不是应该优化这个子代理呢？不然我以后用子代理跑岂不是自讨苦吃了。还有就是你有没有跑解析重写这个环节？"
- **Classification:** `rework` (two strands): (a) "will the subagent make this mistake" → subagent prompt hardening; (b) "did you actually run ⑤" → ⑤ was self-declared done with zero retypesetting.
- **Provenance:** `(extracted)` — full session in-context.
- **Root cause (the unifying defect):** a passing `--only` self-check was treated as proof a role was complete. Verified for ⑤: `lint_markdown_analysis_paragraphs` returned `OK` on a file where ⑤ had done nothing (the lint checks paragraph *length*, not whether retypesetting happened). Same pattern for ③ (L1 above) and ⑥ (`--check-proofreading` returns 100+ FAILs where most are known false positives hiding real defects). This is the **lint-ceiling** anti-pattern (F4 reactive counterpart: don't trust lint as proof of completion).
- **Gate verdict:** `strengthen` (G1 PASS — every semantic role / G2 strengthen — the 2026-06-30 path-independent self-check Hard Contract item sold the lint as verification but did not warn of its blind spots / G3 principle — verifiability discipline; a recurring failure mode).
- **Landing zone:** `SKILL.md` Hard Contract "Path-independent self-check" item (added the "necessary, not sufficient" ceiling note naming ③⑤⑥ blind spots); `.opencode/agents/{math-comma-splitter,analysis-retypesetter,ocr-typo-fixer}.md` (each got an "Anti-shortcut clause" forcing per-unit quantified reporting). NOTE: agent edits now in skill-repo `agents/` via the symlink migration below.
- **Strongest reason NOT to add:** may over-document. **Counter:** the model (main agent, not weak) made the ⑤ shortcut AND the ③ shortcut in one session; the ceiling note is the only durable fix since lints provably cannot see these gaps.
- **Outcome:** APPLIED during-session; logged here for trace.

### Architecture event — `.opencode/agents/` symlink to skill repo (single source of truth)

- **Trigger (verbatim, extracted):** "opencode 的这个agent文件是否支持软链接，如果支持软链接可以放在技能仓库通过软链接链接过去，你可以做个小测试。"
- **Classification:** NOT a rule candidate — a **file-organization architecture change** (recorded as an event, like the 2026-06-29 progressive-disclosure refactor).
- **Problem exposed by this session:** the anti-shortcut edits (L1/L2) were written to the PROJECT `.opencode/agents/*.md` copies. The skill repo `agents/` held only `openai.yaml` — agent `.md` files were never version-controlled in the skill, so fixes did not propagate to other projects. This is the same "two copies drift" risk the skill's symlink convention already uses for `.zcode`/`.codex` skill loading.
- **Empirical verification (extracted, opencode 1.17.11):**
  1. Isolated test project with a symlinked agent → `opencode agent list` discovered it (format `name (mode)`).
  2. Real-scenario canary: skill-repo `agents/repo-canary.md` → project `.opencode/agents/repo-canary.md` symlink → opencode discovered `repo-canary`. (Canary cleaned up after.)
  3. Sync test: appended a marker line to skill-repo `math-comma-splitter.md` → project symlink read it immediately. (Marker cleaned up.)
- **Migration performed:**
  - 11 agent `.md` files copied project → skill repo `agents/` (truth source).
  - Project `.opencode/agents/*.md` deleted, replaced with 11 symlinks → skill repo.
  - `opencode agent list` confirms **11/11** symlinked agents discovered.
- **Files written (skill repo):**
  - `agents/*.md` (11 files — now canonical; carry this session's L1/L2 anti-shortcut edits)
  - `agents/openai.yaml.bak-2026-06-30` (pre-migration snapshot)
- **Files written (project, symlinks not committed):**
  - `.opencode/agents/*.md` → 11 symlinks to skill repo
  - `.opencode/agents.bak-2026-06-30/` (11 real-file backup, in case symlinks break)
- **Known limitation (carried forward):** Windows symlinks are absolute-path; if the skill repo moves, all project symlinks break and must be rebuilt. Symlinks are a local-dev reference, NOT committable (a fresh clone gets dead links). The truth source (skill repo `agents/*.md`) is git-tracked.
- **Outcome:** APPLIED (user "现在就迁移到软链架构").

### Batch metadata

- **Pairwise conflict check:** Fast path — 2 rule candidates (L1, L2) + 1 architecture event. L1 and L2 are complementary (L1 = specific fusion shapes for ③; L2 = the general lint-ceiling discipline across ③⑤⑥). No conflicts.
- **Dev Eval:** N/A — all changes are instruction text / file organization; no validator code or test logic touched. (`validate_canonical_markdown.py` unchanged this session.)
- **Recurrence count:** L1/L2 first occurrence *as strengthened rules*. The *pattern* "guidance exists, no executable gate / lint silent on a shape" recurs across 2026-06-23 (adjacent figures), 2026-06-29 (C1/C2/C4), and this session — L1/L2 are the latest strike; the symlink migration is the first architecture response to the propagation gap.
- **Verification summary:** All verdicts auditable-evidence-only (instruction text + on-disk file states + pasted lint output + opencode discovery output). No machine verification of behavioral effect (Verification Ceiling applies — content skill has no runtime). The opencode symlink discovery (11/11) and the sync test are extracted hard evidence.
- **Active-context staleness:** editing `my-skills/custom/rewrite-doc2x-markdown/*` does NOT change this session's loaded rewrite-doc2x-markdown skill text. The L1/L2 strengthen rules and the symlink architecture take effect in a **fresh rewrite session**. Recommend a fresh session to exercise the improved ③⑤⑥ anti-shortcut discipline + verify a real rewrite benefits from the symlinks.

## 2026-06-30 — ch11 空间向量 session: 3 new rules (E1-E3) + permission-lockdown trace (E4)

**Session provenance:** CAPTURE extracted from the orchestrator's in-context session
(not a subagent). Trace fields tagged `(extracted)`. Session ran the 8-role refinement
chain on `product/2026-06-26-mst-bixiu2-ch11-空间向量与立体几何/`, then a permission
investigation, then a long tail of source-transcript.md content fixes (table→Markdown,
figure side-by-side, comma normalization, MathML attempt, formula splitting) — the
content fixes are job-local, but 4 of them exposed skill-level gaps logged here.

### Candidate E1 — `add_new`: md-cleaner input boundary (RAW OCR only)

- **Trigger (verbatim, extracted):** "什么鬼，你为什么触发的不是那八个子代理而是什么 md-cleaner 子代理？我已经生成了 source-transcript.md 让你清细这个啊，你应该用之后的子代理工作啊"
- **Classification:** `wrong` — orchestrator ran md-cleaner (Step 1 Auto-Fix) on an already-generated `source-transcript.md`, wasting a pass; the user wanted the Step 2.7 refinement chain.
- **Provenance:** `(extracted)` — full session in-context.
- **Gate verdict:** `add_new` (G1 PASS — any already-generated source-transcript.md / G2 `new` — grep `清洗.*source-transcript\|md-cleaner.*source-transcript\|canonical.*2\.7` → 0 hits; no rule distinguished raw-OCR input from canonical-transcript input / G3 principle — correct role selection, prevents wasted passes).
  - Adversarial: "model should infer md-cleaner is for raw." Counter: the main orchestrator (a strong model) made this exact mistake; an explicit boundary is cheap insurance and the user's "什么鬼" proves the ambiguity was real.
- **Landing zone:** `SKILL.md` Step 1 (new "Input boundary" paragraph right under the Step 1 heading, before the auto-fix-rules pointer). Tier-1 cascade: SKILL.md at 290 lines (not near cap); the rule governs main-workflow role selection.
- **Strongest reason NOT to add:** md-cleaner's description already says "mechanically clean a Doc2X OCR Markdown file." Counter: the description describes what it does, not when NOT to invoke it; the user's framing "清洗 source-transcript.md" was ambiguous and the description did not resolve it.
- **Outcome:** APPROVED (user "OK").

### Candidate E2 — `strengthen`: Rule 5 also corrupts table separator rows

- **Trigger (verbatim, extracted):** "调用子代理清洗的时候，为什么没有识别出这个表格异常？...它用的是下划线，但是正常的表格语法不是下划线。" (referring to `| :__________: |` that should be `| :---: |`)
- **Classification:** `rework` → `strengthen`. The 2026-06-30 B9 rule covered `--fix` corrupting frontmatter `---` fences, but NOT Markdown table separator rows.
- **Provenance:** `(extracted)` — full session in-context + byte-diff against `source-transcript.md.bak-20260630-prechain` (the corruption predated the 8-role chain; it was an earlier `--fix` run).
- **Gate verdict:** `strengthen` (G1 PASS — any Markdown-table-bearing file run through `--fix` / G2 `strengthen` — `SKILL.md:238` "Rule 5 ... including the frontmatter `---` fences" named only frontmatter; table separators are a different victim object of the same Rule 5 / G3 principle — silent structural corruption; `lint_tables` is silent on underscore separators, verified).
  - Evidence: 2 corrupted separators found in one job (L191 例3 table, L900 例18 table — both `> | :__________: |`), one inside a callout.
- **Landing zone:** `SKILL.md` Step 4 (new paragraph after the "`--fix` vs frontmatter" block, extending Rule 5's victim list to table separators + the grep-restore procedure + the lint_tables-blind-spot note). Tier-1 cascade.
- **Strongest reason NOT to add:** arguably covered by "re-assert after --fix". Counter: the existing re-assert step only checks frontmatter fences (L244 "first 5 lines MUST still parse as frontmatter"); table separators are mid-document and were not in the check.
- **Outcome:** APPROVED (user "OK").

### Candidate E3 — `add_new`: HTML blocks don't render `$...$`

- **Trigger (verbatim, extracted):** "在 Markdown 中，HTML 表格里的公式如果使用 $ 符号是无法渲染的，只能使用 MathML。"
- **Classification:** `missing` → `add_new`. SKILL.md L212 said `<div class="analysis-block">` requires MathML, but did NOT generalize to `<table>`.
- **Provenance:** `(extracted)` — full session in-context (user stated the technical fact; orchestrator verified KaTeX config: `ignoredTags` does not include `table`, but Markdown processors pass HTML blocks through verbatim without scanning `$`).
- **Gate verdict:** `add_new` (G1 PASS — any HTML-table/HTML-block containing formulas / G2 `new` — grep `table.*MathML\|HTML.*table.*\$` → 0 hits; L212 named `<div>` only / G3 principle — rendering correctness, verifiable).
  - Adversarial: "L212 already says HTML needs MathML." Counter: L212 names `<div class="analysis-block">` specifically; the user hit the `<table>` case and it is NOT covered. The rule generalizes to ALL HTML blocks.
  - Resolution chosen by user: convert HTML table → Markdown table (so `$...$` renders via KaTeX), NOT hand-write MathML (browser `mathvariant` support proved uneven in this session's test pages).
- **Landing zone:** `SKILL.md` Step 3 (new paragraph after the "Parser choice" block, generalizing the HTML-needs-MathML rule to all HTML blocks + the convert-to-Markdown preferred fix). Tier-1 cascade.
- **Strongest reason NOT to add:** borderline preference (Markdown-table vs MathML is a style choice). Counter: the core principle — "HTML blocks don't render `$...$`" — is a verifiable technical fact, not taste; the fix preference (Markdown table) is secondary and aligns with the existing "use plain Markdown" default.
- **Outcome:** APPROVED (user "OK").

### Candidate E4 — permission lockdown (APPLIED during session, trace only)

- **Trigger (verbatim, extracted):** "搞清楚他为什么破坏啊" (re: role ⑤ destroying 6 tables + reverting 例6 label) → root cause: ⑤ used the `task` tool to spawn a grandchild analysis-retypesetter subagent → "根据 opencode 文档我可以控制 agent 能用什么工具/权限，这样他就无法调用子代理了" → "看看还有没有其余的工具或者权限要禁用的，避免复发其余问题"
- **Classification:** NOT a new rule candidate for this retro — it was **applied during the session** and is recorded here for trace (same pattern as the 2026-06-30 architecture events). The 11 agents' `permission:` blocks were rewritten to deny `task`/`skill`/`todowrite`/`grep`/`glob`/all MCP (`lean-ctx_*`/`doc2x_*`/etc.), leaving only `edit`/`write`/`read`/`bash`. Verified empirically: a probe agent + the real `analysis-retypesetter` both report exactly 4 visible tools; a `task` call returns "Model tried to call unavailable tool 'task'".
- **Provenance:** `(extracted)` — full session in-context + on-disk agent files.
- **Files written (during session, via symlink → canonical repo):**
  - `agents/*.md` (11 files — canonical source; each got the lockdown `permission:` block)
  - `references/opencode-agent-invocation.md` (new "## Agent permission lockdown (MANDATORY — evolved 2026-06-30)" section with the full policy + the 3 verification findings: agent-level deny overrides project `"*":"allow"`, wildcard `"server_*": deny` is the reliable MCP form, enumerating `lean-ctx_*` tools individually is insufficient)
- **Strongest reason NOT to add:** over-constrains agents. Counter: the grandchild-dispatch failure empirically destroyed 6 tables; leaf agents provably need only edit/write/read/bash; the lockdown is the durable fix and opencode 1.17.11 enforces it (verified).
- **Outcome:** APPLIED during session (no new write this retro; the canonical files already carry it via the 2026-06-30 edits). Logged here for trace.

### Batch metadata

- **Pairwise conflict check:** Fast path — 3 new-write candidates (E1/E2/E3) + 1 trace-only (E4). E2 (extend Rule 5 victim list) and E3 (HTML render rule) are orthogonal files (Step 4 vs Step 3). E1 (role selection) is orthogonal to both. E4 is trace-only. No conflicts.
- **Dev Eval:** `py -3 -m pytest tests/ -q` → **94 passed** (unchanged from the session's pre-edit baseline; pure instruction-text edits to SKILL.md, no validator/test code touched). Non-regression confirmed.
- **Outcome:** APPROVED (user "OK" after a plain-language summary of the 3 changes).
- **Files written (this retro):**
  - `SKILL.md` (E1: new Step 1 "Input boundary" paragraph; E2: new Step 4 "Rule 5 also corrupts table separators" paragraph; E3: new Step 3 "HTML blocks don't render `$...$`" paragraph). 290 → 302 lines.
  - `references/evolution-log.md` (this entry)
- **Snapshot (same-day, 3rd):** `SKILL.md.bak-2026-06-30-3`
- **Recurrence count:** E1/E2/E3 all first occurrence as rules. E2 is a sibling of the 2026-06-30 B9 frontmatter rule (same Rule 5, different victim object) — logged as a distinct strengthen because the victim (table separator) and its lint blind spot (lint_tables) are different from frontmatter's. E4 is first occurrence (the grandchild-dispatch root cause + permission-lockdown fix are new to the log).
- **Verification summary:** Dev Eval machine-verified (pytest 94 pass) for non-regression. All 4 lessons are auditable-evidence-only (instruction text + extracted session evidence + on-disk file states + pasted grep/validator output) — no machine verification of their *behavioral* effect (Verification Ceiling applies; content skill has no runtime). E4's opencode enforcement (4 visible tools, `task` blocked) is extracted hard evidence.
- **Active-context staleness:** editing `my-skills/custom/rewrite-doc2x-markdown/SKILL.md` does NOT change this session's loaded rewrite-doc2x-markdown skill text (loaded at session start). The 3 new rules (E1 role boundary, E2 table-separator check, E3 HTML-render rule) take effect in a **fresh rewrite session**. The E4 permission lockdown already took effect during this session (it is executable agent config, not loaded skill text). Recommend a fresh session to exercise the improved skill end-to-end.


## 2026-06-30 — ch10 概率 session: 2 new strengthen rules (F1-F2)

**Session provenance:** CAPTURE extracted from the orchestrator's in-context session
(not a subagent). Trace fields tagged `(extracted)`. Session ran the 8-role refinement
chain on `product/2026-06-26-mst-bixiu2-ch10-概率/`, then a tail of rendering/typography
fixes. 3 user corrections examined; 1 was already-resolved (table separator = E2 from
the ch11 session earlier today), 2 were new → strengthened here.

### Candidate F1 — `strengthen`: `aligned` is for ONE chain, not enumerating unrelated formulas

- **Trigger (verbatim, extracted):** "这种公式为什么要用 align？明明它是一行就能写完的，而且它也不是一个公式，而是多个公式。为什么要放在一起？这没有道理。" (re: `\begin{aligned} P(A)&=½\ P(B)&=½\ P(AB)&=¼ \end{aligned}` cramming 3 independent probability values into one aligned block)
- **Classification:** `rework` → `strengthen`.
- **Provenance:** `(extracted)` — full session in-context + byte-diff of the 5 affected blocks (lines 313/321/491/525/549 in source-transcript.md).
- **Gate verdict:** `strengthen` (G1 PASS — any doc with parallel value lists vs calculation chains / G2 `strengthen` — `canonical-markdown-rules.md:203` covers the reverse direction "long inline chain → move to `aligned`" but NOT the forward distinction "aligned = single chain, NOT enumeration"; `SKILL.md:222` says "long formulas use `\begin{aligned}`" without the boundary / G3 principle — semantic correctness; `aligned` force-aligns `=` signs across independent equations, which has no mathematical meaning).
  - Evidence: 5 abused `aligned` blocks found in one job (例10选项B/D, 例19题干, 例20①, 例21 — all parallel P(A)/P(B)/P(AB)-style value lists), vs 5 legitimate chain blocks (例9, 例4传输, 例9家庭, 例11×2 — all single-quantity `&=` step-by-step). The split was unambiguous.
  - Adversarial: "aligned-vs-gathered is a style preference." Counter: the user's reasoning ("它不是一个公式，而是多个公式...这没有道理") is a *semantic* argument — the equations are independent, so aligning their `=` is meaningless. This is typography principle, not taste.
- **Landing zone:** `references/canonical-markdown-rules.md` (extend the existing L203 "long multi-equality chain" rule with the forward boundary). Tier-2 cascade: SKILL.md untouched (progressive disclosure — SKILL.md already says "read references/canonical-markdown-rules.md"). SKILL.md stays at 302 lines.
- **Strongest reason NOT to add:** borderline preference. Counter: the chain-vs-enumeration distinction is verifiable (each `&=` row a different quantity → enumeration), and Doc2X provably abuses this pattern. Documented to stop models from inheriting Doc2X's hallucinated alignment.
- **Outcome:** APPROVED (user "批准").

### Candidate F2 — `strengthen`: `$$` + trailing punctuation breaks KaTeX (`$$.`/`$$,`)

- **Trigger (verbatim, extracted):** "You can't use 'macro parameter character '#' in math mode 他怎么报这个错误怎么回事？...就是从这个之后的公式设锤子为...则样本空间" (re: `$$...$$.` at line 159 of source-transcript.md — the period glued to closing `$$` corrupted KaTeX state, silently breaking every formula from 例6 onward)
- **Classification:** `rework` → `strengthen`.
- **Provenance:** `(extracted)` — full session in-context; root cause verified by byte-inspection (line 159 was `$$.`) + the Doc2X raw transcript (`page-transcript.raw.md` showed `$$.` was an original Doc2X emission, not introduced by any role). Confirmed the failure cascaded: all formula rendering from line 159 onward stopped, with the misleading `#` error pointing at an unrelated `<span style="color:#9370DB">` line.
- **Gate verdict:** `strengthen` (G1 PASS — any Doc2X-derived doc rendered with strict KaTeX / G2 `strengthen` — `canonical-markdown-rules.md:204` "Display math delimiters must be standalone block lines. Never emit `$$formula$$` on one line" already covers the single-line case but NOT the `$$`-followed-by-punctuation case; `auto-fix-rules.md:54` "Move punctuation outside `$...$` delimiters" covers inline `$...$` only, not block `$$` / G3 principle — rendering correctness, verifiable; the failure mode is silent and cascading, exactly the high-cost defect class).
  - Evidence: 1 `$$.` corruption (line 159) + 8 single-line `$$X$$` blocks (lines 61/77/705/727/729/731/733/878) found in one job; all unwrapped, `$` balance 1496 preserved before/after.
  - Adversarial: "L204 already implies `$$` must be on its own line; a careful reader infers `$$.` is wrong." Counter: a strong model (the orchestrator) hit this as a *rendering* failure after completing the full chain — the documented KaTeX error string (`#` math mode) is a red herring and not inferable from L204. A one-line failure-mode warning is cheap insurance.
- **Landing zone:** `references/canonical-markdown-rules.md` (new bullet between L203 and L204, paired with F1). Tier-2 cascade. SKILL.md untouched.
- **Strongest reason NOT to add:** arguably covered by L204's "standalone block lines". Counter: L204 governs delimiter placement but is silent on (a) the `$$`-touches-punctuation failure mode, (b) the misleading `#` red-herring error, (c) the silent cascade. The red-herring note alone saves real debugging time.
- **Outcome:** APPROVED (user "批准").

### Already-resolved (NOT a new lesson — correct discard)

- **U1 — table separator `:__________:` corruption:** reworked during the session, but this is the **same substance** as candidate E2 from the ch11 session earlier today (2026-06-30). E2 already wrote the Rule-5-also-corrupts-table-separators rule to `SKILL.md:250-252`. This session's fix was an *application* of E2, not a new lesson. Correctly classified as Gate 2 `duplicate` → discard (precedence row 3). Logged here for recurrence traceability: this is the 2nd occurrence of the Rule-5-corruption pattern (1st = frontmatter B9, 2nd = table separators E2, this = re-application of E2).

### Batch metadata

- **Pairwise conflict check:** Fast path — 2 strengthen candidates (F1/F2) + 1 discard (U1). F1 (aligned/gathered boundary) and F2 (`$$`-punctuation hygiene) are orthogonal rules in the same reference file. No conflicts.
- **Dev Eval:** INCONCLUSIVE — `py -3 -m pytest tests/ -q` returned `1 failed, 94 passed`. The 1 failure (`test_accepts_verbose_but_short_render_formula`) is **pre-existing in the baseline** (touched no validator/test code this session — pure instruction-text edits to canonical-markdown-rules.md). Per Dev Eval protocol: sample-already-failing → degrade to `unverified`. The edit cannot *cause* regression (instruction text only), but Dev Eval cannot prove non-regression.
- **Recurrence count:** F1/F2 both first occurrence as rules. The *pattern* "Doc2X emits render-breaking formula structures that pass structural lints" recurs across 2026-06-29 (C-class) → F2 is the latest strike on the formula-rendering axis; F1 (aligned abuse) is a genuinely new axis (typography semantics, not rendering).
- **Files written (this retro):**
  - `references/canonical-markdown-rules.md` (F1: new "aligned is ONE chain, not enumeration" bullet; F2: new "`$$`+punctuation breaks KaTeX" bullet). 403 → 405 lines, +1931 bytes.
  - `references/evolution-log.md` (this entry)
- **Snapshot:** `references/canonical-markdown-rules.md.bak-2026-06-30` (first same-day snapshot for this file).
- **Verification summary:** All verdicts auditable-evidence-only (instruction text + extracted session evidence + on-disk file states + pasted grep/validator output). Dev Eval inconclusive (pre-existing baseline failure). No machine verification of behavioral effect (Verification Ceiling applies — content skill has no runtime). The 5-vs-5 aligned split and the 1+8 `$$` corruption count are extracted hard evidence.
- **Active-context staleness:** editing `my-skills/custom/rewrite-doc2x-markdown/references/canonical-markdown-rules.md` does NOT change this session's loaded rewrite-doc2x-markdown skill text (loaded at session start). The 2 new rules (F1 aligned-boundary, F2 `$$`-punctuation) take effect in a **fresh rewrite session**. Recommend a fresh session to exercise the improved formula-hygiene discipline.


## 2026-06-30 — measure_inline_formula_width: real rendered width + three-band classifier

**Session provenance:** CAPTURE extracted from the orchestrator's in-context
session (not a subagent). Trace fields tagged `(extracted)`. Driven by user
feedback that the source-char-based `lint_long_inline_formula` judge was
unreliable (a 275-source-char / 360px-render formula was flagged "long").

### Trigger (verbatim, extracted)

- "这个公式明明不长，为什么还是 align 改的我累死了实在不理解你的长度怎么判定的，能不能计算渲染出的宽度，根据这个来比较？单纯的字符数和等号实在不靠谱。"
- "还有就是，你能不能计算出渲染之后的公式宽度？...基本上超过 A4 三分之二的话，就可以考虑用 inline。"
- "你可以限制三个区间吗？1.短区间 2.长区间 3.中区间（中区间的话，就必须要主动判断）"
- On the markdown-vs-render stage paradox: "就是不走 scan 技能不行吗？就是直接打印不行吗？...你就直接正常打印，你不用他的技能样式打印，你就朴素打印。" + "而且你这个打印的话，就只打印公式就行了"

### Architecture decision (the key insight)

The lint (`validate_canonical_markdown.py`) runs on `source-transcript.md`
(markdown stage) — `handout.html` does not exist yet, and real pixel width
needs a rendered DOM. **The user's solution**: do a PLAIN PRINT (minimal HTML =
KaTeX CDN + formula spans only, no scan/A4 styling) and measure. This bypasses
both the paradox (we measure for sizing, not for delivery) and the scan skill
dependency. Verified 2026-06-30 that inline `.katex` width is
**container-independent** (identical in a wide body vs a 100px-narrow div,
measured via `.katex` itself wrapped in `white-space:nowrap`) — so the plain
print's width equals the real handout width.

### Three-band classifier (A4 physical basis)

A4 text area = 210mm − 13mm×2 = 184mm ≈ 695px @ 96dpi, font-size 12px
(the handout's base size; `.katex` inherits it, no scaling).

- **short** (≤ 464px = A4 2/3): keep inline, regardless of `=` count.
- **long** (> 625px = A4 90%): convert to `$$egin{aligned}$$`.
- **medium** (464–625px): judge in context (derivation chain vs compact eval).

### Candidate M1 — `add_new`: measure_inline_formula_width.py (plain-print width tool)

- **Classification:** `missing` → `add_new`.
- **Gate verdict:** add_new (G1 PASS — any inline-formula-bearing markdown / G2 `new` — grep `measure.*width|render.*width|playwright|getBoundingClientRect` in scripts/ → 0 hits; the validator is pure-Python-regex, no browser / G3 principle — measurement correctness, replaces an unreliable estimate with ground truth).
  - Adversarial: "spins up a browser, too heavy for a lint." Counter: it is a STANDALONE tool called on-demand (NOT wired into the per-role `--only` self-check, which must stay fast); ~1s launch, called once when the coarse lint flags something worth verifying.
  - Adversarial: "violates rewrite Hard Contract (no downstream renderers)." Counter: it does NOT depend on the scan skill or handout.html; it builds its OWN minimal KaTeX HTML. It measures for sizing, not for delivery — within rewrite's scope.
- **Landing zone:** `scripts/measure_inline_formula_width.py` (new); `SKILL.md` Step 3 (the lint-coarse-signal paragraph rewritten to point at this tool + the three bands); `tests/test_measure_inline_formula_width.py` (new, 6 tests incl. the sin β regression).
- **Outcome:** APPLIED (user approved the plan).

### Candidate M2 — `strengthen`: SKILL.md three-band guidance (replaces the coarse-signal paragraph)

- **Classification:** `rework` → `strengthen`.
- **Gate verdict:** strengthen (G1 PASS / G2 strengthen — the 2026-06-30 E-paragraph said "coarse signal, judge in context" but gave no precise tool or physical thresholds / G3 principle).
- **Landing zone:** `SKILL.md` Step 3.
- **Outcome:** APPLIED.

### Evidence (extracted, hard)

- **sin β regression:** measured 359.9px in the wide container, 359.9px in the 100px-narrow container (identical → container-independent confirmed). Band = short. The old source-char lint (275 chars > 90) flagged it "long"; the estimate (53 > 50) also flagged it. Real width says short. This is the defect the tool fixes.
- **Real-doc sweep:** on the actual ch11 source-transcript.md (deduped), the tool reported **3** medium/long formulas (L286 long 628.7px, L475 medium 580.5px, L954 medium 480.6px). The coarse lint had flagged ~80. The precision tool reduces 80 coarse flags to 3 actionable ones.
- **Container-independence probe:** 4 formulas measured in wide vs narrow containers — all identical to <0.1px.

### Batch metadata

- **Pairwise conflict check:** Fast path — 2 candidates (M1 new tool, M2 strengthen guidance). M2 points at M1; complementary, no conflict.
- **Dev Eval:** `py -3 -m pytest tests/ -q` → **101 passed** (was 95; +6 for `test_measure_inline_formula_width.py`: 3 pure-logic + 3 browser-backed, incl. the sin β regression). Non-regression confirmed. The 3 browser-backed tests auto-skip if Playwright/Chromium is unavailable (import-skip + launch-probe), so the suite stays green on minimal environments.
- **Outcome:** APPLIED (user approved the plan).
- **Files written:**
  - `scripts/measure_inline_formula_width.py` (NEW: plain-print width tool — KaTeX CDN + formula spans, Playwright headless measure, three-band classifier, `--md/--json/--band/--dedup` CLI)
  - `tests/test_measure_inline_formula_width.py` (NEW: 6 tests, incl. sin β regression + container-independence via the sin β wide/narrow parity)
  - `SKILL.md` (Step 3: coarse-signal paragraph rewritten → points at the tool + three bands with A4 px thresholds)
  - `references/evolution-log.md` (this entry)
- **Snapshot (same-day, 4th):** `SKILL.md.bak-2026-06-30-4`
- **Recurrence count:** first occurrence. The *pattern* "estimate vs ground truth / lint over-flags" is new to the log; the source-char→estimate change earlier this session (the `estimate_render_width` commit) was the first attempt, this is the durable fix.
- **Verification summary:** Dev Eval machine-verified (pytest 101 pass). The container-independence claim and the sin β short-band verdict are extracted hard evidence (pasted measurement output). The three-band thresholds (464/625px) are derived from the A4 geometry (also extracted from handout.css). The tool's *behavioral* effect on orchestrator decisions is auditable-evidence only (Verification Ceiling).
- **Active-context staleness:** editing `my-skills/custom/rewrite-doc2x-markdown/*` does NOT change this session's loaded skill text. The new tool + three-band guidance take effect in a **fresh rewrite session**. The tool itself is executable now (it is a script, not loaded skill text). Recommend a fresh session to exercise the improved formula-width discipline end-to-end.


## 2026-07-01 — integrate formula-length judgment into the skill flow (canonical-rules + self-check sync)

**Session provenance:** CAPTURE extracted from the orchestrator's in-context
session. Trace fields tagged `(extracted)`. Driven by the user's review question
"现在技能哪个环节搞这个公式长度" + "你得先把技能和流程弄好，把这些工具都在技能当中使用。
完整之后，你再提交仓库。"

### Trigger (verbatim, extracted)

- "关键是子代理你改没改？子代理专门负责公式的有吗？...现在技能哪个环节搞这个公式长度"
- "你得先把技能和流程弄好，把这些工具都在技能当中使用。完整之后，你再提交仓库。"

### Problem (the integration gap)

The 2026-06-30 measure-inline-formula-width work added the tool + three-band
classifier to SKILL.md Step 3, but **two flow documents still carried the old
source-char heuristic (~90 chars)**, so an agent following the flow would hit
stale rules:
- `references/canonical-markdown-rules.md:203` — "over ~90 chars with ≥2 equalities... judge in context" (no measure tool, no three bands)
- `references/self-check.md:36` — "over ~90 chars with ≥2 `=`... automated by lint" (no measure tool, no three bands)

This is the "tool exists but the flow doesn't use it" gap the user flagged.

### Design decision

- **No new subagent.** The measure tool spins up a browser (~1s) — too heavy for
  the 8-role `--only` self-check (retry ≤3 would cost tens of seconds). It is a
  one-shot gate, precedent: ⑥'s `--check-proofreading` (independent CLI branch)
  and Step 2.8 (independent gate).
- **Formula-length judgment stays in Step 3** (structural format, main-agent).
  It is a whole-document scan, not question-block refinement (Step 2.7).
- **Integration = sync the three-band + measure tool into canonical-rules +
  self-check**, so Step 3's "apply canonical-rules" naturally carries the
  correct rule. SKILL.md Step 3 becomes a POINTER (progressive disclosure —
  detailed rule lives in canonical-rules, single source).

### Candidate I1 — `strengthen`: canonical-markdown-rules.md:203 (char → three-band)

- **Classification:** `rework` → `strengthen`.
- **Gate verdict:** strengthen (G1 PASS / G2 strengthen — L203 existed but used the stale ~90-char heuristic / G3 principle — measurement correctness).
- **Landing zone:** `references/canonical-markdown-rules.md:203` (rewritten in place).
- **Outcome:** APPLIED.

### Candidate I2 — `strengthen`: self-check.md:36 (char → three-band judgment item)

- **Classification:** `rework` → `strengthen`.
- **Gate verdict:** strengthen (G1 PASS / G2 strengthen — L36 existed but pointed only at the coarse lint / G3 principle).
- **Landing zone:** `references/self-check.md:36` (rewritten in place).
- **Outcome:** APPLIED.

### Candidate I3 — `strengthen`: SKILL.md Step 3 (deduplicate → pointer)

- **Classification:** `rework` → `strengthen`.
- **Gate verdict:** strengthen (G1 PASS / G2 strengthen — Step 3 had the full three-band text inline, duplicating canonical-rules / G3 principle — progressive disclosure, single source of truth).
- **Landing zone:** `SKILL.md` Step 3 (long inline paragraph → pointer to canonical-rules + the one measure command).
- **Outcome:** APPLIED.

### Batch metadata

- **Pairwise conflict check:** Fast path — 3 candidates, all strengthen the same rule across 3 files (canonical-rules = source, self-check = check, SKILL.md = pointer). Complementary, no conflict.
- **Dev Eval:** `py -3 -m pytest tests/ -q` → **101 passed** (unchanged — pure doc edits, no code/test logic touched).
- **Manual verification:** `~90 chars` grep → 0 hits across all 3 files (cleared); `measure_inline_formula_width` + three-band thresholds (464/625) present in all 3.
- **Outcome:** APPLIED.
- **Files written:**
  - `references/canonical-markdown-rules.md` (I1: L203 char-heuristic → three-band + measure command)
  - `references/self-check.md` (I2: L36 char-heuristic → three-band judgment item + measure command)
  - `SKILL.md` (I3: Step 3 long paragraph → pointer + single command; progressive disclosure)
  - `references/evolution-log.md` (this entry)
- **Snapshots (2026-07-01):**
  - `references/canonical-markdown-rules.md.bak-2026-07-01`
  - `references/self-check.md.bak-2026-07-01`
  - `SKILL.md.bak-2026-07-01`
- **Recurrence count:** first occurrence of the integration (the measure tool itself was added 2026-06-30; this is the flow-sync that makes it actually used).
- **Verification summary:** Dev Eval machine-verified (pytest 101 pass). The three doc edits are auditable-evidence-only (the flow is now self-consistent: Step 3 → canonical-rules → three bands → measure tool → self-check confirms).
- **Active-context staleness:** editing the repo files does NOT change this session's loaded skill text. The integrated flow takes effect in a **fresh rewrite session**.
