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
python review_print_pages.py --html artifacts/knowledge-handout/<slug>/handout.html
```

3. Read `screens/py-latest/page-review/page-review-manifest.json`
4. Start with page 1:
   - spawn a fresh review subagent for that page
   - hand the page screenshot to that subagent
   - include the page packet JSON and the prompt from that packet
   - ask for structured `pass/fail`, issues, and fixes
5. If page 1 fails:
   - modify the HTML/CSS/content
   - rerun `review_print_pages.py`
   - re-review page 1
6. Only after page 1 passes may page 2 be reviewed
7. Continue until all pages pass
8. Run one final full-document validation pass before hand-off

## Subagent contract

The subagent reviews. The main agent edits.

Use exactly one review subagent per page at a time.

Do not let multiple workers rewrite the same handout page in parallel.

The review result must be structured and page-local:

- `pass`
- `issues`
- `fixes`

Avoid vague feedback like “looks a bit crowded” or “maybe larger”.

## What counts as a page-review failure

- meta/process chrome appears in the handout body
- diagrams are too small to read
- diagram text overflows or becomes cramped
- the page wastes a large lower section with obvious blank space
- the page reads like web chrome rather than a teaching handout
- blocks split awkwardly or feel visually unbalanced
