---
name: knowledge-to-print-html
description: Use when the user provides knowledge-point keywords, notes, draft text, or learning requirements and wants a polished, source-backed, diagram-rich, print-first HTML handout for A4/PDF. Trigger on "知识点", "讲义", "图文并茂", "可打印 HTML", "打印成 PDF", "根据关键词整理", "把笔记做成教程页", or printable learning-page requests.
---

# Knowledge To Print HTML

Turn `关键词 + 草稿` into a polished, print-first HTML handout that the user can manually export to PDF.

This skill is a workflow skill. It coordinates research, writing, diagrams, visual direction, HTML generation, and print verification so the final page is both readable on screen and stable when printed.

## When To Use

Use this skill when the user wants things like:

- “根据这些知识点整理一份图文讲义”
- “把这段草稿扩写成可打印的 HTML 教程页”
- “先搜索补充案例，再做成漂亮的讲义页面”
- “我要最后手动打印成 PDF，所以 HTML 要适配 A4”
- “做成知识卡片 / 知识手册 / 教学页 / 学习页”

Do not use this skill for:

- Simple summaries with no research or design requirements
- Slide decks and PPT-like outputs
- PDF manipulation on existing PDF files
- Plain Markdown to HTML conversion with no enrichment

## Required Inputs

Minimum:

- A set of knowledge-point keywords
- Rough notes, draft text, or bullet points

Optional:

- Target audience
- Desired depth or page count
- Preferred visual tone
- Required sources or banned sources
- Whether the topic needs current information

## Default Assumptions

If the user does not specify, assume:

- Audience: motivated beginner to intermediate reader
- Depth: one strong explainer, roughly 4-8 A4 pages
- Language: match the user's language
- Citation mode: supported claims plus a final references section
- Visual preset: `editorial-atlas`
- Output directory: `artifacts/knowledge-handout/<slug>/`
- Final artifact: self-contained `handout.html` plus supporting SVG diagrams

## Working Files

Follow `references/output-contract.md`.

Use these files as the standard pipeline:

- `brief.md` — normalized request, assumptions, and research gaps
- `research.md` — source-backed findings, examples, and citations
- `outline.md` — final structure before full drafting
- `article.md` — source of truth for the written content
- `diagrams/` — generated SVG diagrams
- `handout.html` — final print-first HTML deliverable

Also follow:

- `references/layout-guardrails.md`
- `references/diagram-guardrails.md`
- `references/review-loop.md`

## Non-Negotiable Quality Gates

This skill implements **Plan C: mandatory sequential page review** by default.

Do not hand off `handout.html` until all of these are true:

1. `validate_print_layout.py` has generated per-page screenshots where each screenshot contains exactly one `.sheet`.
2. `review_print_pages.py` has generated `page-review-manifest.json` plus one `page-XX-subagent-prompt.md` per page.
3. A fresh page-review subagent has reviewed page 1 using that page's prompt and screenshot.
4. Page 1 has either passed or been fixed and revalidated.
5. Only then may page 2 be sent to a fresh page-review subagent.
6. The same gate repeats until every page passes.
7. A final full-document validation runs after the last page passes.

If the environment has no subagent/delegation tool, stop and report that the visual review gate is blocked. Do not self-approve pages as a substitute.

Main agent and subagent roles are deliberately separate:

- Main agent: researches, writes, edits HTML/CSS, reruns validation.
- Page-review subagent: reviews exactly one page screenshot and returns structured feedback.
- No parallel page edits. No batch approval of later pages.

## Skill Routing

Load these skills in this order when they apply:

1. `searxng` — for current facts, examples, or source discovery
2. `content-research-writer` — for turning research into structured, cited prose
3. `baoyu-diagram` — for process, mechanism, architecture, or intuition diagrams
4. `baoyu-infographic` — only when a dense summary graphic adds clear value
5. `design-reference-router` — only when the user asks for a real brand or product feel
6. `minimalist-ui` — default document-style visual constraints for calm, premium, printable pages
7. `frontend-design` — for cover design, section openers, and high-quality final styling
8. `baoyu-markdown-to-html` — for stable Markdown-to-HTML rendering
9. `webapp-testing` — for print validation, screenshots, and broken-layout checks

If one of these skills is unavailable in the current environment, use the nearest built-in equivalent and say what was substituted.

## Workflow

### 1. Normalize the brief

Convert the user's raw input into:

- topic slug
- audience
- reading goal
- known material
- missing material
- visual target
- print constraints

Ask only the shortest necessary follow-up questions. If the user is vague, proceed with the default assumptions above rather than blocking.

### 2. Extract what the user already knows

Split the incoming material into four buckets:

- confirmed knowledge points
- draft prose worth preserving
- unsupported claims that need checking
- concepts that deserve visuals

Save this to `brief.md`.

### 3. Research only where it adds value

Research is for filling gaps, not for replacing the user's voice.

Use `searxng` or equivalent search to gather:

- definitions that are unclear or unstable
- concrete examples and case studies
- evidence for claims, numbers, or comparisons
- recent developments when the topic is time-sensitive

Save notes and source links to `research.md`.

### 4. Build a strong explainer outline

Create `outline.md` that is useful for print reading, not just web scanning.

Default structure:

1. Title + one-sentence promise
2. Why this matters
3. Core mental model
4. Key concepts or steps
5. Worked example or case study
6. Visual explanation blocks
7. Pitfalls / misunderstandings
8. Practical takeaway
9. References

### 5. Draft the article in Markdown first

`article.md` is the content source of truth. Do not start from raw HTML unless the user explicitly asks for a hand-crafted page with no Markdown stage.

The article must:

- read like a polished explainer, not a search dump
- include at least one concrete case, example, or scenario
- contain clear transitions between sections
- flag uncertainty instead of overstating weak claims
- include citations or traceable source notes for factual claims
- avoid process chrome, provenance notes, packaging filler, or “how this handout was made” language

### 6. Add visuals that teach, not decorate

Default visual order:

- one strong title / cover visual treatment
- one or more SVG diagrams for processes, mechanisms, or structure
- optional summary infographic only when density helps comprehension

Prefer:

- `baoyu-diagram` for explanatory SVGs
- diagrams with captions and one explicit takeaway
- consistent visual language across all diagrams
- diagrams that stay readable at print size without zooming

Avoid:

- random stock-like filler visuals
- image-only pages with weak explanatory value
- diagram styles that fight the page typography
- shrinking a dense figure until labels are hard to read
- allowing text to overflow boxes inside a diagram
- keeping one crowded diagram when two smaller teaching diagrams would be clearer

### 7. Choose the visual preset

Use `references/visual-presets.md`.

Default to `editorial-atlas`.

Only switch when the topic clearly calls for it:

- `refined-minimal` — calmer, book-like, premium
- `technical-briefing` — more structured, analytical, systems-oriented

When the user does not ask for a specific brand style, apply `minimalist-ui` as the baseline visual discipline, then let `frontend-design` add only the amount of flair the document can print safely.

If the user explicitly wants a real product or brand feel, run `design-reference-router` first, then let `frontend-design` interpret that brief.

### 8. Render to HTML, then refine for print

Default rendering path:

1. Use `baoyu-markdown-to-html` to convert `article.md` into styled HTML
2. Refine the output HTML/CSS for print-specific layout and stronger visual quality
3. Keep the final artifact as `handout.html`

The final HTML must be:

- printable on A4 by default
- comfortable to read on screen
- self-contained or safely relative-pathed
- free of fixed UI chrome, sticky nav, or app-like noise
- free of meta text such as print instructions, topic labels, provenance notes, or workflow narration inside the teaching body

Follow `references/print-checklist.md`.

### 9. Upgrade the final look

After the HTML exists, use `frontend-design` to improve:

- cover composition
- typography hierarchy
- section divider rhythm
- callout boxes
- figures and captions
- examples and case-study blocks

Do not turn the page into a landing page. This is a document artifact first, a webpage second.

Do not waste half a page on cover-like spacing. If a page is too sparse, rebalance the layout, enlarge the teaching figure, or merge content with adjacent material.

### 10. Validate before hand-off

Use `webapp-testing` or equivalent browser validation to check:

- HTML opens locally
- images and SVGs resolve correctly
- long sections do not break awkwardly in print
- tables, callouts, lists, and code blocks do not overflow
- page breaks are intentional enough for manual PDF export
- diagrams are large enough to read and do not contain overflowing text
- no page wastes a large empty lower region unless it is clearly justified by the composition

For repo-local smoke validation, you can use:

```bash
python validate_print_layout.py --html evals/<slug>/handout.html
```

By default this writes screenshots, a PDF export, and a JSON report to `evals/<slug>/screens/py-latest/`.

Default mandatory page-review loop:

```bash
python review_print_pages.py --html artifacts/knowledge-handout/<slug>/handout.html
```

This writes a sequential review packet to `screens/py-latest/page-review/`, including:

- `page-review-manifest.json`
- `page-XX-review.json`
- `page-XX-subagent-prompt.md`

Review page 1 first. Give the page screenshot, `page-XX-review.json`, and `page-XX-subagent-prompt.md` to a fresh review subagent. If page 1 fails, fix it, rerun the packet, and re-review page 1. Only then move to page 2.

The subagent must review at least:

- meta/process text leaking into the handout body
- diagram readability, size, and text overflow
- large lower-page blank regions
- clipped or cramped figures, tables, callouts, code, and captions
- print-page balance and break quality
- information hierarchy and teaching clarity
- whether the page reads like a study handout rather than a web hero, dashboard, or marketing page

The subagent must return only structured JSON:

```json
{
  "page": 1,
  "pass": false,
  "issues": [
    {
      "type": "large_bottom_gap",
      "severity": "fail",
      "evidence": "The lower third of the page is empty after the final callout.",
      "fix": "Move the next short section onto this page or enlarge the teaching diagram."
    }
  ],
  "fixes": [
    "Rebalance page 1 before reviewing page 2."
  ]
}
```

If the subagent returns `pass=false`, edit only what is needed for that page, regenerate screenshots and packets, and retry the same page. Do not review later pages while the current page is failing.

Only then hand off `handout.html`.

## Content Quality Rules

- Explain before optimizing for beauty
- Use real examples instead of abstract claims whenever possible
- Prefer one excellent case study over five shallow examples
- Keep citations traceable, even if the final page uses a compact references section
- Match depth to the reader; do not produce expert-only shorthand unless asked
- Keep internal process notes out of the learner-facing artifact

## Visual Rules

- Print first, screen second
- Strong typography, restrained palette, generous whitespace
- One accent color by default
- Two typefaces maximum by default
- SVG diagrams over decorative bitmap art
- No dashboard-card soup
- No generic AI gradients unless the user explicitly wants that direction
- No dark full-page backgrounds by default for print artifacts
- No tiny teaching diagrams used as decorative inserts
- No dense SVG box-and-arrow charts unless the labels remain comfortably readable
- No pages with obvious top-heavy content and an empty lower half

## Hand-off Requirements

Before claiming success, provide:

- the final `handout.html` path
- the working folder path
- any generated diagram paths
- the chosen visual preset
- the browser print recommendations

Do not copy those hand-off items into the printed page itself.

Recommend these print settings unless the page was built differently:

- Paper: A4
- Scale: 100%
- Background graphics: enabled
- Headers/footers: disabled

## Common Mistakes

- Starting from HTML before the argument and outline are solid
- Doing broad search instead of targeted research
- Producing pretty pages with weak teaching value
- Using diagrams as decoration instead of explanation
- Letting page breaks split figures or callouts badly
- Overriding print readability with dark hero sections or excessive effects
- Forgetting to keep `article.md` as the content source of truth
- Letting workflow chrome or provenance notes leak into the learner-facing page
- Shrinking diagrams until they become unreadable
- Accepting a page with a large blank lower half just because it technically fits
