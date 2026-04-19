# Mandatory Sequential Review Loop

This skill uses a default mandatory page-review loop.

## Rule

Do not review page `N + 1` until page `N` has:

1. been screenshot,
2. been reviewed by a page-review subagent,
3. been fixed if needed,
4. been revalidated.

## Required order

1. Generate `handout.html`
2. Run:

```bash
python scripts/review_print_pages.py --html artifacts/knowledge-handout/<slug>/handout.html
```

3. Read `screens/py-latest/page-review/page-review-manifest.json`
4. Start with page 1:
   - spawn a fresh review subagent for that page; do not self-review
   - hand the page screenshot to that subagent
   - include `page-XX-review.json`
   - include `page-XX-subagent-prompt.md`
   - require structured JSON only
5. If page 1 fails:
   - modify the HTML/CSS/content
   - rerun `review_print_pages.py`
   - re-review page 1
6. Only after page 1 passes may page 2 be reviewed
7. Continue until all pages pass
8. Run one final full-document validation pass before hand-off

The page screenshot handed to the subagent must be a true printable-page clip:

- clip to the exact printable page area for that `.sheet`
- preserve true A4 page proportions in the PNG
- do not substitute viewport-sized or stacked screenshots for page review

Treat this as a hard gate, not a preference:

- if the validator reports non-A4 page screenshots, stop and fix the capture pipeline before asking a subagent to review the page

The review packet generator defaults to `--review-language auto` so the subagent prompt can follow the handout language. If language detection is wrong, rerun with `--review-language zh` or `--review-language en`.

## Subagent contract

The subagent reviews. The main agent edits.

Use exactly one review subagent per page at a time.

Do not let multiple workers rewrite the same handout page in parallel.

If the environment has no subagent/delegation tool, the review gate is blocked. The main agent must tell the user this instead of self-approving the page.

The review result must be structured, page-local JSON:

```json
{
  "page": 1,
  "pass": false,
  "issues": [
    {
      "type": "diagram_readability",
      "severity": "fail",
      "evidence": "Labels in the lower flowchart are too small to read at page scale.",
      "fix": "Split the flowchart into two figures or enlarge it to full width."
    }
  ],
  "fixes": [
    "Rebuild page 1 before reviewing page 2."
  ]
}
```

Required fields:

- `pass`
- `issues`
- `fixes`

Avoid vague feedback like “looks a bit crowded” or “maybe larger”.

## What the subagent must check

For each page, review all of these:

- **Meta leakage** — print instructions, topic labels, provenance notes, “user-provided notes”, workflow narration, or any equivalent source/process chrome in the learner-facing body
- **Diagram readability** — figures are large enough, teach a real concept, have readable labels, and do not contain text overflow or cramped arrows
- **Page density** — the lower page region is not obviously empty unless the composition has a clear teaching reason
- **Component density** — the page is not built from a dense dashboard-like grid of small cards or micro-boxes
- **Overflow and clipping** — figures, callouts, tables, code blocks, captions, and reference items stay inside the page
- **Teaching hierarchy** — title, section headings, examples, captions, and takeaways have clear relative importance
- **Typographic rhythm** — body text remains comfortable at print size and spacing is not obviously crushed to make the page fit
- **Repair quality** — suggested fixes improve structure/content/layout instead of just shrinking type or squeezing spacing
- **Print identity** — the page feels like a study handout, not a website hero, dashboard, mood board, or marketing page
- **Page-local continuity** — blocks are not awkwardly split and the page can be understood in sequence

When the page fails, prefer fixes in this order:

1. rebalance content across neighboring pages
2. merge or split related blocks
3. enlarge or simplify the teaching visual
4. replace a small-card grid with sections, a table, or a worked example

Do not recommend shrinking font size, line-height, or paragraph spacing as the primary repair.

## What counts as a page-review failure

- meta/process chrome appears in the handout body
- diagrams are too small to read
- diagram text overflows or becomes cramped
- diagrams act as decoration instead of explanation
- the page wastes a large lower section with obvious blank space
- the page relies on dense small-card grids or microtext boxes
- the page fits only because typography rhythm has been visibly compressed
- the page reads like web chrome rather than a teaching handout
- blocks split awkwardly or feel visually unbalanced
- the page passes heuristics but the screenshot still looks visually broken
