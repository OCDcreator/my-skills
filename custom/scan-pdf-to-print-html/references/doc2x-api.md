# Doc2X API

Use this as the primary OCR path for scanned or image-only PDFs.

## Environment

- `DOC2X_API_KEY`: required bearer token
- `DOC2X_BASE_URL`: optional, defaults to `https://v2.doc2x.noedgeai.com`

## Default Recommendations

- model: `v3-2026`
- export format: `md`
- `formula_mode`: `normal`
- `formula_level`: `0`
- `merge_cross_page_forms`: `false` for page-faithful jobs

## Request Flow

1. `POST /api/v2/parse/preupload`
2. `PUT` the PDF binary stream to the returned upload URL
3. Poll `GET /api/v2/parse/status?uid=...`
4. Optionally `POST /api/v2/convert/parse`
5. Poll `GET /api/v2/convert/parse/result?uid=...`
6. Download the returned export URL immediately

## Why Keep Both Parse Results And Exports

- page-level parse results are easy to review and preserve page boundaries
- export markdown/docx is easier to hand off downstream
- server-side results expire, so download them promptly
- keep `source-transcript.md` sourced from page-level parse output
- keep export markdown under `doc2x/export/` for reference instead of overwriting the canonical transcript
- when the export zip already contains local `images/`, localize `doc2x/export/export.md` to those sibling assets instead of leaving matching crop URLs on the Doc2X CDN

## Failure Notes

- missing API key: fail fast with a clear message
- parse quota / concurrency / task limit: surface the API error directly
- export polling failure: keep parse results and stop with a useful error
- suspicious OCR: compare against local rendered pages before manual fixes
- if the export archive contains markdown, preserve it as a supplemental file only; do not collapse page markers by replacing `source-transcript.md`
