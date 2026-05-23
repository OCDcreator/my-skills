---
name: pdf-toc-bookmarker
description: Create a new PDF with clickable bookmarks/outline from scanned or image-only table-of-contents pages. Use when Codex needs to add PDF bookmarks from TOC screenshots/pages, especially for scanned Chinese books where local OCR is unreliable. Requires the user to provide a PDF file path, the TOC page range, and the actual PDF page where printed page 1 begins before rendering or writing bookmarks.
---

# PDF TOC Bookmarker

## Required Inputs

Do not start rendering or editing until all three inputs are known:

- `pdf_path`: absolute path to the PDF.
- `toc_pages`: TOC page range in actual PDF page numbers, such as `11-16`.
- `printed_page_1_pdf_page`: the actual PDF page where the book's printed page `1` begins, such as `17`.

If any required input is missing, ask for it before doing work. Do not infer the anchor from the TOC unless the user explicitly asks for automatic detection.

Compute:

```text
offset = printed_page_1_pdf_page - 1
target_pdf_page = printed_page + offset
```

Also create a top-level bookmark named `目录` that targets the first page in `toc_pages`. This lets the PDF outline jump back to the scanned table of contents for a full-book overview. Do not include this `目录` entry in `toc_items.json`; add it when writing the outline.

## Workflow

1. Verify the PDF exists and inspect page count.
2. Create a dedicated working directory for this PDF, such as `<current-workdir>/<pdf-stem>_toc_work`, so images and JSON from different books do not mix.
3. Render `toc_pages` to images with `scripts/render_toc_pages.py`.
4. If there are more than 6 rendered TOC images, split them into batches of 3-5 images and run separate subagents. Large single image batches can fail with request-size errors.
5. Send the rendered images to a subagent and ask it to return strict JSON:

```json
[{ "title": "...", "level": 1, "page": 12 }]
```

Rules for the subagent:

- `title` preserves numbering and visible title text.
- `level` is a hierarchy integer. Prefer chapters as `1`, sections as `2`, Chinese numbered items such as `一、` as `3`, and detailed items such as `考点1` / `1.` / `问题一` as `4`.
- `page` is the printed page number shown in the TOC, not the PDF page number.
- Return only JSON, no Markdown.
- Mark uncertain titles with `[?]`.

6. Save the JSON as a working file, normally `<workdir>/toc_items.json`. If the TOC was split into batches, merge batch JSON files in page order.
7. Before writing the PDF, inspect the JSON:
   - count items,
   - search for `[?]`,
   - confirm printed pages are nondecreasing unless the book visibly resets numbering,
   - confirm `printed_page + offset` stays within the PDF page count.
8. Write a new PDF with `scripts/write_pdf_outline.py`, passing `--toc-page <first TOC page>` so the first bookmark is `目录`.
9. Reopen the output PDF and verify:
- output exists,
- page count is unchanged,
- TOC count matches JSON item count plus the `目录` bookmark,
- first bookmark targets the first TOC page,
- last bookmark target is in range.

## Scripts

Use scripts from this skill folder.

Render TOC pages:

```bash
python scripts/render_toc_pages.py --pdf "C:\path\book.pdf" --pages 11-16 --out "C:\path\work\toc_pages"
```

Write outline:

```bash
python scripts/write_pdf_outline.py --pdf "C:\path\book.pdf" --toc-json "C:\path\work\toc_items.json" --printed-page-1-pdf-page 17 --toc-page 11 --out "C:\path\book.with-toc.pdf"
```

If `--out` is omitted, write next to the input PDF using `.with-toc.pdf`.

## Combined Books And Page Jumps

Some PDFs are combined books or edited scans where printed page numbers jump, reset, or refer to another volume. If `write_pdf_outline.py` rejects out-of-range targets, do not alter the TOC JSON first. Verify the mapping.

Use these checks:

- Render the target PDF page from `printed_page_1_pdf_page` and confirm its printed footer is page `1`.
- Render the failing target/tail pages and inspect their printed footers.
- If the mapping changes, establish segment anchors such as:

```text
PDF 26 -> printed 1
PDF 414 -> printed 390
PDF 415 -> printed 407
PDF 606 -> printed 598
```

Then use a temporary or patched mapping function to write bookmarks by segment. If printed pages are absent from the PDF, map those TOC items to the nearest available boundary page and report that in the final answer.

Do not trust a low-resolution page-footer contact sheet when anchors conflict. Render key pages individually and inspect them.

## Safety Rules

- Never overwrite the input PDF. Always write a new output file.
- Reject bookmark targets outside the PDF page range.
- Keep intermediate TOC images and JSON so the user can inspect or correct recognition results.
- Report warnings for uncertain titles (`[?]`) or decreasing printed page numbers before final delivery.
- Prefer PyMuPDF (`fitz`) for rendering and outline writing.
- If PyMuPDF is missing, tell the user it is required instead of switching to a fragile ad hoc method.
