# Frontmatter Spec

Single source of truth for the YAML frontmatter that `source-transcript.md` may carry. Both `rewrite-doc2x-markdown` (writes the frontmatter) and `scan-pdf-to-print-html` (reads it) conform to this spec.

## Purpose

Frontmatter is a **pure record of explicit user intent** — it stores choices the user (or an AskUserQuestion prompt) made, so downstream steps do not have to re-guess or re-ask. It does NOT auto-infer anything. Unknown intent = no field = fall back to default + ask.

## Shape

```yaml
---
pagination-level: h2
cover: false
---
```

- Must be the **first** thing in the file (optional BOM / leading blank lines tolerated).
- Flat `key: value` only — no nesting, no lists, no quoting. Values are lowercased.
- A single pair of `---` fences. The parser (`scripts/parse_frontmatter.py`) recognizes only a leading block anchored to the start; `---` thematic breaks later in the body are never touched.
- Missing fields = default value. A document with no frontmatter at all is fully valid and behaves as if every field were at its default (backward compatible).

## Fields

### `pagination-level`

| | |
|---|---|
| Type | enum string |
| Allowed | `h2`, `h3` |
| Default | `h2` |
| Semantics | Which heading levels force a fresh sheet (page break) in the rendered handout. |

- `h2` (default): every h2 begins a new sheet. h3 never forces a break. Legacy behavior.
- `h3`: every h2 **and** every h3 begins a new sheet — **but** a h3 breaks only if its owning h2 already has body content on the current sheet. If the h2 is immediately followed by the h3 with no prose in between, that h3 does **not** break (it stays on the h2's sheet), which prevents the h2 from becoming a stranded lone-heading page.

**Use case for `h3`**: a single section extracted from a larger document is authored with the section title at the top (`#`/`h2` after render) and its sub-sections at `h3`. Those sub-sections must paginate so each starts on a fresh sheet. The "上级须有内容" guard ensures this never strands the parent h2.

### `cover`

| | |
|---|---|
| Type | enum string |
| Allowed | `true`, `false` |
| Default | `false` |
| Semantics | Whether to inject a concept-map cover sheet. |

- `true`: inject a cover. If the job directory has `concept-map.png`, use it. If not, **do not error** — prompt the user whether to route to the cover-generation skill (`a4-novak-html-cover`) to produce the image first, then inject.
- `false`: no cover, even if a `concept-map.png` happens to exist. YAML is the single authority.
- missing: ask the user (batched with any other missing fields in one AskUserQuestion).

## How scan reads it

1. `build_faithful_handout_html.py` → `parse_frontmatter()` strips the block (so it never leaks into the rendered HTML) and captures the dict.
2. Captured fields are emitted as `<meta>` tags in `<head>`:
   ```html
   <meta name="pagination-level" content="h3">
   <meta name="cover" content="true">
   ```
   Default values are **not** emitted — absence of a `<meta>` means "default", keeping old jobs byte-identical.
3. `postprocess_handout_for_contract.py` reads `<meta name="pagination-level">` to decide whether h3 headings force page breaks.

## How rewrite writes it

After rewrite completes (for handout-type documents), ask the user the pagination level and cover choice via one AskUserQuestion, then write the answers into the frontmatter at the top of `source-transcript.md`. This records intent so scan does not have to re-ask.

## Resilience

- Malformed frontmatter (e.g. missing closing `---`) → treated as "no frontmatter"; the whole text is returned as body unchanged. The build never breaks on a bad block; it simply yields no metadata (caller falls back to defaults + ask).
- Unknown keys → ignored with a stderr warning (so typos surface, intent is not silently dropped).
- Invalid values → ignored with a warning; the field is treated as missing (default + ask).

See `scripts/parse_frontmatter.py` → `--self-test` for the canonical behavior cases.
