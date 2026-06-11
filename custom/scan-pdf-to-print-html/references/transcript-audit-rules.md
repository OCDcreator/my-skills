# Transcript Audit Rules

Use this before turning `source-transcript.md` into HTML.

## Goal

Turn `doc2x/page-transcript.raw.md` into an audited `source-transcript.md` without changing the source meaning.

## Non-Negotiable Rules

- Keep page markers exactly visible: `## Page N`.
- Keep source order, numbering, and language.
- Do not summarize, explain, or simplify.
- Only fix OCR mistakes you can verify from the source page.
- If you cannot verify a character or symbol, write `[TO VERIFY: ...]`.

## Required Transcript Fixes

- Fix obvious OCR typos and spacing damage.
- If a line is clearly a section title in the source but appears as a plain paragraph, promote it to a heading.
- Keep heading hierarchy stable. The first real content heading under a `## Page N` marker should normally start at `###`.
- Do not jump heading levels by more than one step.
- If the first numbered heading on a page starts at `2` or `二`, treat that as a verify-first signal. Check whether an earlier heading was lost or whether the excerpt really starts there.
- If Doc2X merged several relations into one inline formula, split them into separate inline formulas and move punctuation outside the math delimiters.
  Example:
  `\( a // \alpha , a \subset \beta , \alpha \cap \beta = b \Rightarrow a // b \)`
  becomes
  `\( a // \alpha \)，\( a \subset \beta \)，\( \alpha \cap \beta = b \Rightarrow a // b \)`
- Prefer `\dfrac{...}{...}` for simple fractions such as `\dfrac{1}{2}`.
- If the numerator or denominator already contains another formula, operator, or nested fraction, use `\tfrac{...}{...}` instead.
- Keep code as fenced code blocks; do not flatten code into paragraphs.
- For choice examples, put the stem and options in one blockquote.
- Put options in list form so the builder can spread them evenly:
  `- A. ...`
  `- B. ...`
  `- C. ...`
  `- D. ...`
- Normalize fill-in blanks to exactly `__________`.
- Put solution text in its own paragraph starting with `解析：`.

## Approval Gate

- Run `py -3 scripts/lint_transcript_structure.py --job-dir "C:\path\job"` before transcript approval.
- Do not build HTML while `job.json.transcript_audit_status` is `pending`.
- Do not build HTML while `job.json.transcript_structure_lint_status` is `pending` or `failed`.
- After the user approves `source-transcript.md`, set `job.json.transcript_audit_status` to `approved`.
