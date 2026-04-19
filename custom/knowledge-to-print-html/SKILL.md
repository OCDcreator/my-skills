---
name: knowledge-to-print-html
description: Use when the user wants notes, keywords, drafts, lesson content, or research findings turned into a print-ready HTML/PDF teaching handout, including requests like “知识点整理成讲义”, “可打印 HTML”, “打印成 PDF”, “教学页”, “knowledge handout”, “print-ready HTML handout”, “teaching handout from notes”, or “A4 learning handout with diagrams”.
---

# Knowledge To Print HTML

Turn rough knowledge material into a polished, print-first `handout.html` that is stable on A4, exports cleanly to PDF, and passes sequential page review before hand-off.

This skill coordinates research, writing, diagram work, HTML/CSS refinement, print validation, and page-by-page review. It is for **teaching handouts**, not for generic webpages or slide decks.

## Use This Skill When

Typical requests include:

- “根据这些知识点整理一份图文讲义”
- “把草稿做成可打印 HTML，最后导出 PDF”
- “做一份教学页 / 学习页 / 复习手册”
- “Turn these notes into a knowledge handout”
- “Make a print-ready HTML handout from notes”
- “Create an A4 teaching handout with diagrams and sources”

## Do Not Use This Skill When

- the user only wants a simple summary or rewrite
- the deliverable is a slide deck / PPT / presentation
- the job is editing an existing PDF rather than generating a new handout
- the request is plain Markdown-to-HTML conversion with no research, teaching design, or print validation

## Inputs And Defaults

Minimum inputs:

- knowledge-point keywords, notes, or draft prose

Helpful optional inputs:

- audience
- target depth or page count
- desired visual tone
- required/banned sources
- whether the topic needs current information

Default assumptions when the user does not specify:

- audience: motivated beginner to intermediate reader
- depth: one strong explainer, roughly 4–8 A4 pages
- language: match the user's language
- citation mode: supported claims plus a final references section
- visual preset: `editorial-atlas`
- output directory: `artifacts/knowledge-handout/<slug>/`

## Canonical Working Files

Follow `references/output-contract.md`.

Standard pipeline files:

- `raw-input.md`
- `brief.md`
- `research.md`
- `outline.md`
- `article.md`
- `diagrams/`
- `handout.html`

Canonical validation scripts in this repo:

- `scripts/validate_print_layout.py`
- `scripts/review_print_pages.py`

Root-level `validate_print_layout.py` and `review_print_pages.py` are compatibility wrappers only. Prefer the `scripts/` paths in new instructions.

Read these references before finalizing:

- `references/layout-guardrails.md`
- `references/diagram-guardrails.md`
- `references/review-loop.md`
- `references/print-checklist.md`
- `references/runtime-requirements.md`
- `references/visual-presets.md`
- `references/working-file-templates.md`

## Skill Routing And Fallbacks

Check whether each downstream skill exists in the current environment before using it. Do not assume external skills are installed.

| Need | Priority | Preferred skill | If unavailable |
|------|----------|-----------------|----------------|
| source support for each core knowledge point | default, must when facts may be unstable | `searxng` | use the built-in web/search capability and keep primary sources |
| cited research → structured prose | recommended | `content-research-writer` | draft `article.md` directly from `research.md` with explicit citations |
| explanatory SVG diagrams | recommended | `baoyu-diagram` | build inline SVG diagrams manually |
| dense summary infographic | optional | `baoyu-infographic` | skip the infographic unless it clearly improves teaching value |
| real product / brand feel | optional | `design-reference-router` | stay on `editorial-atlas` or another built-in preset |
| calm printable document discipline | recommended | `minimalist-ui` | apply `visual-presets.md` + guardrails directly in CSS |
| final visual polish | recommended | `frontend-design` | refine typography, figures, spacing, and callouts manually |
| Markdown → HTML conversion | recommended | `baoyu-markdown-to-html` | convert `article.md` into semantic HTML manually |
| browser validation and screenshots | must | `webapp-testing` | run the bundled Playwright-based scripts directly |

Why the page-review gate is strict: the editing agent is too close to the layout to judge it reliably. A fresh page-review subagent catches whitespace, overflow, hierarchy drift, and HTML/PDF mismatch that the editor routinely misses.

## Workflow

### 1. Normalize the brief

Convert raw user input into:

- topic slug
- audience
- reading goal
- known material
- missing material
- visual target
- print constraints

Ask only the shortest follow-up questions needed to unblock real work.

### 2. Extract what the user already knows

Save the untouched user input to `raw-input.md` first.

Do not normalize, summarize, or reorder the raw sample before saving it.

Then extract from that preserved sample into `brief.md`.

Split incoming material into:

- a core knowledge point list
- confirmed knowledge points
- draft prose worth preserving
- unsupported claims that need checking
- concepts that deserve visuals

Save this to `brief.md`.

### 3. Research every core knowledge point by default

The user's knowledge points are the skeleton. Research adds the missing muscle, examples, and precision.

Keep the user's voice in the final writing, but do not let “voice” become an excuse to skip research.

Each core knowledge point should usually be researched until you have:

- an authoritative explanation or mechanism description
- key boundaries, easy confusions, or misconceptions
- at least one example, application, case study, or counterexample
- source support that can be traced in `research.md`

Adjacent sub-points can be researched together, but do not skip a whole core point just because it looks familiar or because the user already mentioned it.

When comprehensive external research is not possible, switch to constrained mode only if:

- the user explicitly says not to search
- the environment is offline or search access is blocked
- the material is private and cannot be checked externally
- the user provides a closed source pack and explicitly says to use only that pack

In constrained mode, record the reason in `brief.md`, keep the limitation visible in the final hand-off, and still organize `research.md` by core knowledge point using the available material.

Save findings and links to `research.md`.

### 4. Build an outline for print reading

Create `outline.md` for a printable explainer, not a scroll-first blog post.

Default shape:

1. title + one-sentence promise
2. why it matters
3. core mental model
4. key concepts or steps
5. worked example / case study
6. visual explanation blocks
7. pitfalls / misunderstandings
8. practical takeaway
9. references

### 5. Draft in Markdown first

`article.md` is the content source of truth unless the user explicitly asks for hand-authored HTML only.

The article must:

- read like a polished explainer, not a search dump
- include at least one concrete example or scenario
- keep citations traceable in `research.md` and the final references section, not as learner-facing provenance notes inside the body
- keep process notes and packaging filler out of the learner-facing body

### 6. Add teaching visuals

Prefer explanatory SVGs over decorative artwork.

Use visuals to teach:

- process
- mechanism
- structure
- comparison

Full readability rules live in `references/diagram-guardrails.md`.

### 7. Choose the visual preset

Use `references/visual-presets.md`.

Default to `editorial-atlas`.

Only switch when the topic clearly calls for it:

- `refined-minimal`
- `technical-briefing`

If the user explicitly wants a real product or brand feel, route through `design-reference-router` first.

### 8. Render to HTML, then refine for print

Default rendering path:

1. convert `article.md` into semantic HTML
2. refine layout and CSS for A4
3. save final artifact as `handout.html`

The final HTML must be:

- printable on A4 by default
- comfortable to read on screen
- free of app chrome, sticky nav, and workflow narration
- free of topic labels / provenance notes / “this handout will…” filler in the teaching body
- free of dense multi-card dashboard grids used as the main page structure
- free of compressed body typography used only to force content onto the page
- protected against text overflow inside panels, callouts, table cells, code blocks, tags, and grid children with appropriate `overflow-wrap`, `word-break`, and `hyphens` rules
- protected against SVG visual enclosure failures: every diagram outer frame / card / 外框 must actually contain the text, pills, icons, and child boxes it visually claims to group
- protected against compact SVG text-box padding failures: inner padding must stay comfortable, the final line must not hug the bottom edge, and side spacing should keep visual balance

Full page-density and chrome rules live in `references/layout-guardrails.md`.

### 9. Validate with the canonical scripts

Use the bundled scripts, not ad-hoc screenshots.

Smoke validation:

```bash
python scripts/validate_print_layout.py --html artifacts/knowledge-handout/<slug>/handout.html
```

Sequential review packet:

```bash
python scripts/review_print_pages.py --html artifacts/knowledge-handout/<slug>/handout.html
```

What the validator is responsible for:

- per-page HTML screenshots clipped to exact printable page areas
- true A4 sheet checks
- print PDF export
- fast-view review PDF export
- rendered PDF-page screenshots
- HTML-vs-PDF parity metadata
- linked-SVG visual enclosure checks for frames/cards that fail to wrap their contents
- machine-readable validation report

If the user asks for an **image-only / raster / 图片型 PDF**, do not build it from the default 1.5-scale page screenshots; that produces roughly 144 DPI A4 images and can make text look soft. Run a final high-DPI validation pass and use the generated `*-fastview.pdf` (or an equivalent image-only PDF assembled from those high-DPI page PNGs):

```bash
python scripts/validate_print_layout.py --html artifacts/knowledge-handout/<slug>/handout.html --device-scale-factor 3.125 --out-dir artifacts/knowledge-handout/<slug>/screens/high-dpi
```

Treat **300 DPI** as the default raster-PDF target for A4 handouts: it yields about `2480 × 3508` pixels per page, which keeps body text clear without making files unnecessarily large. Use 450 DPI only when the user explicitly needs print-shop-grade raster output or the page contains unusually tiny labels; avoid 600 DPI by default because the file-size and render-time cost usually outweighs visible gains for teaching handouts.

Detailed script behavior and environment requirements live in:

- `references/review-loop.md`
- `references/runtime-requirements.md`

### 10. Run the mandatory sequential page-review loop

This skill uses **Plan C: sequential page review by default**.

The flow is:

1. run validation
2. generate review packets
3. review page 1 with a fresh subagent
4. if page 1 fails, fix only what page 1 needs
5. rerun validation + review packet generation
6. review page 1 again
7. only after page 1 passes, move to page 2
8. continue until every page passes
9. run one final full-document validation pass

Full operational details, JSON contract, and subagent review rules live in `references/review-loop.md`.

## Non-Negotiable Quality Gates

Do not hand off `handout.html` unless all of these are true:

1. `scripts/validate_print_layout.py` passes the true-A4 sheet checks.
2. The export includes both a print PDF and a fast-view PDF.
3. HTML page count and PDF page count match exactly.
4. The review packet includes per-page HTML screenshots, PDF screenshots, and parity metadata.
5. Each page has been reviewed in order by a fresh page-review subagent.
6. After the last page passes, a final full-document validation run completes.
7. If the hand-off includes a 图片型 / raster / image-only PDF, it is generated from approximately 300 DPI page images, not the default lower-resolution validation screenshots.

If no subagent/delegation tool is available, stop and report that the review gate is blocked. Do not substitute self-approval.

## Environment Notes

Read `references/runtime-requirements.md`.

Important defaults:

- `scripts/validate_print_layout.py` will try to auto-install missing runtime dependencies unless `--no-auto-install` is used.
- In offline or restricted environments, preinstall dependencies first and run with `--no-auto-install` so failure is immediate and explicit.
- `scripts/review_print_pages.py` uses `--review-language auto` by default so the generated subagent prompt matches the handout language when possible.

## Content And Visual Rules

Keep these front-of-mind:

- explain before optimizing for beauty
- prefer one strong case study over many shallow examples
- use diagrams to teach, not decorate
- print first, screen second
- no dense card-grid/dashboard-card soup, sparse hero pages, or top-heavy pages with a blank lower half
- no tiny unreadable diagrams
- no diagram outer frame / 外框 that fails to contain its own labels, pills, icons, or child boxes
- no learner-facing meta/process text inside the handout body

Use the reference files for the full rule sets instead of duplicating them in the page.

## Hard Anti-Patterns

Treat these as fail conditions, not soft advice:

- Do not build the page around multi-column micro-card grids. A single large teaching callout is acceptable; a wall of small cards is not.
- Do not “fix” page density by shrinking font size or crushing line-height / paragraph spacing. Rebalance content or layout instead.
- Do not write learner-facing provenance or process notes such as “based on user-provided notes”, “compiled from the draft”, or “this handout was generated from”.

## Hand-Off Requirements

Before claiming success, provide:

- raw input path
- final `raw-input.md` path
- final `handout.html` path
- working folder path
- generated diagram paths
- chosen visual preset
- print recommendations
- image-only PDF path and raster DPI, if the user requested one

Recommended print settings unless the page was deliberately built otherwise:

- paper: A4
- scale: 100%
- background graphics: enabled
- headers/footers: disabled

Do not place those hand-off notes inside the printed teaching body.

## Common Failure Modes

- starting from HTML before the argument is solid → Fix: finish `brief.md`, `research.md`, and `outline.md` first.
- losing the user's original wording and structure too early → Fix: save the untouched sample to `raw-input.md` before any normalization or classification.
- doing unstructured broad browsing instead of per-point research → Fix: return to the core knowledge point list and research each point with focused queries.
- searching only the points that feel uncertain → Fix: research every core knowledge point before drafting, even when the user already supplied a rough explanation.
- producing stylish pages with weak teaching value → Fix: strengthen the mental model, worked example, and diagram purpose before polishing visuals.
- shrinking diagrams until they stop teaching → Fix: enlarge the figure, simplify labels, or split it into two figures.
- letting process chrome leak into the learner-facing page → Fix: move provenance/process notes back into `brief.md`, `research.md`, or the final hand-off message.
- accepting a page with an obvious empty lower half just because it technically fits → Fix: merge blocks, enlarge teaching visuals, add a comparison/worked example, or rebalance neighboring pages.
- relying on heuristic checks without the sequential subagent review gate → Fix: rerun the validator, regenerate the packet, and re-review the current page before advancing.
