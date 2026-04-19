# IGCSE 0620 Ionic Equations Retrofit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retrofit `artifacts/knowledge-handout/igcse-0620-ionic-equations/` so it satisfies the hardened `knowledge-to-print-html` workflow: preserved-input reconstruction, honest brief metadata, stronger weak pages, fresh sequential page review, and final validation evidence.

**Architecture:** Keep the existing five-page handout and repair it in place instead of rebuilding from zero. Treat the retrofit as two focused layers: first restore the missing workflow contract files, then improve page-2/page-4 teaching clarity and drive the strict validator plus fresh subagent review loop to completion.

**Tech Stack:** Markdown, hand-authored HTML/CSS, inline SVG, Python validation scripts, fresh page-review subagents

---

## File Structure

- Create: `artifacts/knowledge-handout/igcse-0620-ionic-equations/raw-input.md`
- Modify: `artifacts/knowledge-handout/igcse-0620-ionic-equations/brief.md`
- Modify: `artifacts/knowledge-handout/igcse-0620-ionic-equations/article.md`
- Modify: `artifacts/knowledge-handout/igcse-0620-ionic-equations/handout.html`
- Modify: `artifacts/knowledge-handout/igcse-0620-ionic-equations/diagrams/01-ionic-equation-method.svg`
- Modify: `artifacts/knowledge-handout/igcse-0620-ionic-equations/diagrams/02-electrode-memory-map.svg`
- Regenerate: `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/*`

Responsibilities:

- `raw-input.md` stores the reconstructed preserved-input proxy and clearly marks the missing original-note limitation.
- `brief.md` records normalized scope, `research mode`, and provenance boundary.
- `article.md` stays the prose source of truth when content emphasis or wording changes during layout repair.
- `handout.html` remains the rendered print artifact and absorbs layout/CSS/content balancing changes.
- `diagrams/*.svg` hold the teaching visuals that need to read better at print scale.
- `screens/py-latest/*` is regenerated evidence only; never hand-edit generated validator artifacts.

### Task 1: Restore the missing preserved-input contract

**Files:**
- Create: `artifacts/knowledge-handout/igcse-0620-ionic-equations/raw-input.md`
- Modify: `artifacts/knowledge-handout/igcse-0620-ionic-equations/brief.md`

- [ ] **Step 1: Create the reconstructed preserved-input file**

Write `artifacts/knowledge-handout/igcse-0620-ionic-equations/raw-input.md` with a transparent reconstruction notice and a raw-note-shaped source block like:

```md
# Raw Input

## Source
- reconstructed on 2026-04-19 from surviving project files because the original upstream note document was not preserved
- reconstruction inputs: `brief.md`, `research.md`, `outline.md`, `article.md`

## Preservation Rule
This file preserves the closest recoverable source shape for future workflow runs.
It is not the exact missing historical note document.

## Reconstructed Sample
- Topic: Cambridge IGCSE Chemistry 0620（2026–2028）离子式 / 离子方程式 / 离子检验复习讲义
- Audience: IGCSE Chemistry 学生；中文主讲，但保留高频英文术语
- Must cover:
  - common ions and charges
  - ionic equations with state symbols
  - ionic half-equations in electrolysis
  - qualitative analysis for anions and cations
  - strong vs weak acid reminder for ionic equations
  - redox electron definitions
- Exam-safe corrections to preserve:
  - `Br⁻` + acidified `AgNO3` -> `cream ppt.`
  - `Cu²⁺` + `NaOH` -> `light blue ppt.`
  - aluminium extraction anode half-equation -> `2O²⁻ → O₂ + 4e⁻`
- Output target:
  - 5-page A4 print-first handout
  - Chinese explanation + English chemistry keywords
  - technical-briefing visual direction
```

- [ ] **Step 2: Update `brief.md` to record the current workflow metadata**

Add or revise sections in `artifacts/knowledge-handout/igcse-0620-ionic-equations/brief.md` so they explicitly include:

```md
## Research Mode

- mode: comprehensive
- reconstruction status: original upstream note file missing; preserved-input layer reconstructed from surviving artifact files on 2026-04-19
- known vs inferred boundary:
  - known: topic, audience, scope, exam-safe corrections, 5-page print target
  - inferred: the exact original wording/order of the pre-hardening note document
```

Keep the existing topic, scope, output shape, and print constraints sections; do not flatten them into a shorter template if that removes useful detail.

- [ ] **Step 3: Review the preserved-input diff before touching layout**

Run:

```powershell
git diff -- artifacts/knowledge-handout/igcse-0620-ionic-equations/raw-input.md artifacts/knowledge-handout/igcse-0620-ionic-equations/brief.md
```

Expected: only the new preserved-input file and the brief metadata/provenance additions appear.

- [ ] **Step 4: Commit the contract restoration slice**

Run:

```powershell
git add -- artifacts/knowledge-handout/igcse-0620-ionic-equations/raw-input.md artifacts/knowledge-handout/igcse-0620-ionic-equations/brief.md
git commit -m "docs: restore ionic equations preserved-input contract"
```

Expected: commit contains only the two artifact metadata files above. If unrelated changes are staged, stop and unstage them before committing.

### Task 2: Rebalance page 2 around the ionic-equation teaching visual

**Files:**
- Modify: `artifacts/knowledge-handout/igcse-0620-ionic-equations/article.md`
- Modify: `artifacts/knowledge-handout/igcse-0620-ionic-equations/handout.html`
- Modify: `artifacts/knowledge-handout/igcse-0620-ionic-equations/diagrams/01-ionic-equation-method.svg`

- [ ] **Step 1: Simplify and enlarge the page-2 diagram**

Refactor `artifacts/knowledge-handout/igcse-0620-ionic-equations/diagrams/01-ionic-equation-method.svg` so the figure carries fewer competing text lines and larger labels. Keep the same concept, but favor larger step labels and a shorter worked-example footer. A valid target shape is:

```svg
<text x="92" y="282" class="step-title">一拆</text>
<text x="92" y="326" class="step-body">强酸 / 强碱 / 可溶盐(aq)</text>
<text x="92" y="364" class="step-body">可以拆成离子</text>
```

and trim any redundant explanatory sentences that only repeat the page body text.

- [ ] **Step 2: Widen the diagram slot and reduce page-2 fragmentation**

Adjust the page-2 layout in `artifacts/knowledge-handout/igcse-0620-ionic-equations/handout.html` by changing the top grid and formula-card section so the teaching figure gets more horizontal authority. Favor edits in this shape:

```html
<div class="grid-2 page2-top">
  <figure class="figure figure-wide">
    <img src="diagrams/01-ionic-equation-method.svg" alt="离子方程式四步法示意图" />
  </figure>
  <div class="stack page2-side">...</div>
</div>
```

```css
.page2-top{grid-template-columns:1.58fr .72fr;gap:7px}
.figure-wide{padding:12px}
.formula-grid{grid-template-columns:1fr 1fr;gap:7px}
```

If the formula cards feel too dashboard-like, merge the weakest card into the bottom reminder block instead of shrinking text.

- [ ] **Step 3: Keep `article.md` aligned with the page-2 emphasis**

Update the relevant section in `artifacts/knowledge-handout/igcse-0620-ionic-equations/article.md` so the prose source still matches the handout’s teaching emphasis: four-step method, one worked example, and the must-memorize ionic equations. Keep the same facts, but align any wording you changed in the visual or side notes.

Example target wording:

```md
## Ionic equation method：一拆二删三平四标

- 能拆：强酸、强碱、可溶盐溶液
- 不拆：solid、gas、water、weak acid、metal
- Worked example：`H⁺(aq) + OH⁻(aq) → H₂O(l)`
```

- [ ] **Step 4: Run a targeted validation pass for page 2**

Run:

```powershell
python scripts/validate_print_layout.py --html artifacts/knowledge-handout/igcse-0620-ionic-equations/handout.html
```

Expected: validator passes, regenerates `screens/py-latest/handout-print-page-2.png`, and page 2 no longer looks undersized relative to its figure slot.

- [ ] **Step 5: Commit the page-2 improvement slice**

Run:

```powershell
git add -- artifacts/knowledge-handout/igcse-0620-ionic-equations/article.md artifacts/knowledge-handout/igcse-0620-ionic-equations/handout.html artifacts/knowledge-handout/igcse-0620-ionic-equations/diagrams/01-ionic-equation-method.svg
git commit -m "feat: strengthen ionic equation teaching page"
```

Expected: commit contains only the page-2-related source files listed above.

### Task 3: Rebalance page 4 around the electrolysis memory map

**Files:**
- Modify: `artifacts/knowledge-handout/igcse-0620-ionic-equations/article.md`
- Modify: `artifacts/knowledge-handout/igcse-0620-ionic-equations/handout.html`
- Modify: `artifacts/knowledge-handout/igcse-0620-ionic-equations/diagrams/02-electrode-memory-map.svg`

- [ ] **Step 1: Simplify the electrolysis SVG for print-scale reading**

Refactor `artifacts/knowledge-handout/igcse-0620-ionic-equations/diagrams/02-electrode-memory-map.svg` so the central teaching hook and the electrode example boxes read clearly at print size. Keep the cathode/anode split, but reduce decorative phrasing and leave more room for the equations:

```svg
<text x="108" y="326" class="body">reduction = gain of electrons</text>
<text x="136" y="475" class="chem">2H⁺(aq) + 2e⁻ → H₂(g)</text>
```

If needed, shorten the title/subtitle before shrinking equation text.

- [ ] **Step 2: Give page 4 more visual hierarchy and less card competition**

Adjust `artifacts/knowledge-handout/igcse-0620-ionic-equations/handout.html` so page 4 privileges the memory-map figure and keeps the support blocks secondary. Use edits in this shape:

```css
.page4-top{grid-template-columns:1.56fr .74fr;gap:7px}
.page4-top .figure{padding:12px}
.page4-bottom{grid-template-columns:1.08fr .92fr}
```

If the lower support boxes still fight the figure, merge repetitive bullets before reducing type size.

- [ ] **Step 3: Sync `article.md` with the revised page-4 priorities**

Update the electrolysis/redox section in `artifacts/knowledge-handout/igcse-0620-ionic-equations/article.md` so the source text still matches the handout: cathode/reduction, anode/oxidation, two or three must-memorize half-equations, and the weak-acid reminder.

Example target wording:

```md
## Ionic half-equations in electrolysis

- Cathode = reduction = gain of electrons
- Anode = oxidation = loss of electrons
- Must memorise:
  - `2Cl⁻(aq) → Cl₂(g) + 2e⁻`
  - `2O²⁻ → O₂(g) + 4e⁻`
```

- [ ] **Step 4: Re-run validator and confirm page 4 improves without overflow**

Run:

```powershell
python scripts/validate_print_layout.py --html artifacts/knowledge-handout/igcse-0620-ionic-equations/handout.html
```

Expected: validator passes, page 4 stays within A4 bounds, and the updated figure reads more comfortably than the prior narrow version.

- [ ] **Step 5: Commit the page-4 improvement slice**

Run:

```powershell
git add -- artifacts/knowledge-handout/igcse-0620-ionic-equations/article.md artifacts/knowledge-handout/igcse-0620-ionic-equations/handout.html artifacts/knowledge-handout/igcse-0620-ionic-equations/diagrams/02-electrode-memory-map.svg
git commit -m "feat: strengthen electrolysis revision page"
```

Expected: commit contains only the page-4-related source files listed above.

### Task 4: Regenerate the full validation packet

**Files:**
- Regenerate: `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/handout-validation-report.json`
- Regenerate: `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/handout-print-page-*.png`
- Regenerate: `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/handout-pdf-page-*.png`
- Regenerate: `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/page-review/*`

- [ ] **Step 1: Run the full validator**

Run:

```powershell
python scripts/validate_print_layout.py --html artifacts/knowledge-handout/igcse-0620-ionic-equations/handout.html
```

Expected: `pass: true` in `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/handout-validation-report.json`.

- [ ] **Step 2: Regenerate the sequential review packet**

Run:

```powershell
python scripts/review_print_pages.py --html artifacts/knowledge-handout/igcse-0620-ionic-equations/handout.html
```

Expected: regenerated `page-review-manifest.json` with `nextPageToReview: 1` and prompt files for pages 1 through 5.

- [ ] **Step 3: Inspect the machine-readable gate before dispatching subagents**

Run:

```powershell
Get-Content artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/page-review/page-review-manifest.json
```

Expected:

```json
{
  "reviewMode": "sequential-page-gate",
  "nextPageToReview": 1,
  "subagentRequired": true
}
```

- [ ] **Step 4: Commit the regenerated validation evidence**

Run:

```powershell
git add -- artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest
git commit -m "test: regenerate ionic equations print validation packet"
```

Expected: commit contains only generated evidence under the artifact’s `screens/py-latest/` tree.

### Task 5: Execute the strict sequential fresh-subagent review gate

**Files:**
- Modify if needed after review: `artifacts/knowledge-handout/igcse-0620-ionic-equations/handout.html`
- Modify if needed after review: `artifacts/knowledge-handout/igcse-0620-ionic-equations/article.md`
- Modify if needed after review: `artifacts/knowledge-handout/igcse-0620-ionic-equations/diagrams/01-ionic-equation-method.svg`
- Modify if needed after review: `artifacts/knowledge-handout/igcse-0620-ionic-equations/diagrams/02-electrode-memory-map.svg`
- Use generated prompts: `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/page-review/page-01-subagent-prompt.md`
- Use generated prompts: `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/page-review/page-02-subagent-prompt.md`
- Use generated prompts: `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/page-review/page-03-subagent-prompt.md`
- Use generated prompts: `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/page-review/page-04-subagent-prompt.md`
- Use generated prompts: `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/page-review/page-05-subagent-prompt.md`

- [ ] **Step 1: Review page 1 with one fresh subagent**

Use the exact prompt content from `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/page-review/page-01-subagent-prompt.md` and require JSON-only output with keys `page`, `pass`, `issues`, `fixes`.

Expected success shape:

```json
{
  "page": 1,
  "pass": true,
  "issues": [],
  "fixes": []
}
```

If `pass` is `false`, stop, fix only page-1 issues, rerun Task 4, and repeat page 1 before moving on.

- [ ] **Step 2: Review page 2 with a fresh subagent only after page 1 passes**

Use `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/page-review/page-02-subagent-prompt.md`.

Expected: page 2 either passes outright or returns page-local feedback about diagram readability, hierarchy, or density. If page 2 fails, fix the source files, rerun Task 4, and re-review page 2 before touching page 3.

- [ ] **Step 3: Review page 3 with a fresh subagent only after page 2 passes**

Use `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/page-review/page-03-subagent-prompt.md`.

Expected: no meta leakage, no table clipping, and no HTML/PDF drift.

- [ ] **Step 4: Review page 4 with a fresh subagent only after page 3 passes**

Use `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/page-review/page-04-subagent-prompt.md`.

Expected: the strengthened electrolysis figure reads as a primary teaching element rather than a cramped side graphic. If page 4 fails, fix only page-4-local issues, rerun Task 4, and repeat page 4 before page 5.

- [ ] **Step 5: Review page 5 with a fresh subagent only after page 4 passes**

Use `artifacts/knowledge-handout/igcse-0620-ionic-equations/screens/py-latest/page-review/page-05-subagent-prompt.md`.

Expected: the exam-playbook page passes without hierarchy drift, clipping, or HTML/PDF mismatch.

- [ ] **Step 6: Run one final full-document validation pass after page 5 passes**

Run:

```powershell
python scripts/validate_print_layout.py --html artifacts/knowledge-handout/igcse-0620-ionic-equations/handout.html
```

Expected: final validator run still returns `pass: true` after all review-driven fixes.

- [ ] **Step 7: Commit the final reviewed artifact**

Run:

```powershell
git add -- artifacts/knowledge-handout/igcse-0620-ionic-equations
git commit -m "feat: retrofit ionic equations handout to hardened workflow"
```

Expected: final commit includes only files under `artifacts/knowledge-handout/igcse-0620-ionic-equations/`. If unrelated repo changes appear, unstage them before committing.

## Self-Review Notes

- Spec coverage map:
  - preserved-input reconstruction -> Task 1
  - page-2/page-4 readability improvements -> Tasks 2 and 3
  - validator/review packet regeneration -> Task 4
  - strict fresh sequential page review -> Task 5
- Placeholder scan: no `TODO`, `TBD`, or “similar to previous task” shortcuts remain.
- Boundary check: every planned file lives inside `artifacts/knowledge-handout/igcse-0620-ionic-equations/` except the plan document itself.
