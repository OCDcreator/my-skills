# Knowledge-to-Print HTML PDF Parity Design

## Goal

Extend `custom/knowledge-to-print-html` so the validator automatically exports PDF from `handout.html`, auto-installs required runtime dependencies when allowed, renders PDF pages back to images, and generates page-review packets that let fresh subagents compare each HTML page screenshot against the corresponding PDF page screenshot.

## Current State

- `validate_print_layout.py` already validates `.sheet`-based print layouts, exports stacked and per-page HTML screenshots, and exports a PDF.
- `review_print_pages.py` already generates sequential per-page review packets for HTML screenshots only.
- The skill hardens A4 screenshot capture, but it does not yet:
  - auto-install missing Python/browser dependencies,
  - render PDF pages back into PNGs,
  - package HTML vs PDF page pairs for subagent review,
  - enforce PDF-vs-HTML parity as a first-class review gate.

## Requirements

### 1. Automatic dependency preparation

- Validation must lazily import optional dependencies instead of failing at module import time.
- If Playwright is missing, the tool should attempt `python -m pip install playwright`.
- If the Playwright Chromium runtime is missing, the tool should attempt `python -m playwright install chromium`.
- If PDF rendering support is missing, the tool should attempt `python -m pip install pymupdf`.
- Browser/system fallback may use the host package manager only when browser provisioning is still blocked after Playwright runtime install.
- The default behavior is auto-install enabled, with an opt-out CLI flag for controlled environments.

### 2. PDF page rendering

- After exporting `handout.pdf`, the validator must render each PDF page to a PNG in the same output directory.
- PDF page screenshots must preserve page boundaries and A4 aspect expectations.
- The validator report must record PDF page PNG paths and dimensions.

### 3. HTML vs PDF page parity data

- For each page, the validator must pair:
  - HTML page screenshot,
  - PDF-rendered page screenshot,
  - basic parity metadata such as dimensions, page mapping, and a lightweight image-difference score.
- The validator should fail required checks when:
  - PDF page count does not match HTML sheet count,
  - rendered PDF page PNG count does not match HTML page screenshot count,
  - PDF page screenshots do not preserve A4-like aspect.
- The image-difference score is advisory metadata for review packets, not the sole approval mechanism.

### 4. Sequential subagent review packets

- `review_print_pages.py` must package both HTML and PDF page screenshots into each `page-XX-review.json`.
- Each `page-XX-subagent-prompt.md` must explicitly instruct the page-review subagent to compare HTML page vs PDF page for that one page only.
- Review scope must include:
  - text reflow or missing text after PDF export,
  - figure loss, clipping, scaling drift, or margin drift,
  - page composition changes between HTML and PDF,
  - layout degradation that breaks print fidelity.
- The flow remains sequential: do not review page `N+1` until page `N` passes after fixes and regeneration.

### 5. Tests

- Add unit coverage for dependency auto-install orchestration.
- Add unit coverage for PDF page rendering metadata/report structure using isolated helpers.
- Add unit coverage that review packets now include both HTML and PDF screenshots and parity review instructions.
- Keep existing end-to-end validator smoke tests intact.

## Design

### Validator structure

`validate_print_layout.py` will move optional imports behind helper functions:

- `ensure_python_package(...)`
- `ensure_playwright_runtime(...)`
- `load_playwright(...)`
- `load_pymupdf(...)`

These helpers keep the main validator deterministic while allowing best-effort environment bootstrapping.

The validator will also add PDF rendering helpers:

- render PDF pages to PNG with PyMuPDF,
- read rendered PNG dimensions,
- compute a coarse parity score between HTML page PNG and PDF page PNG using resized grayscale sampling.

### Report additions

The JSON report will gain a `pdf.screenshots.pages` array and a `parity.pages` array, plus a required check such as `pdfScreenshotsUseA4Aspect`. Parity entries should be page-local and structured enough for `review_print_pages.py` to reuse directly.

### Review packet changes

Each page packet will include:

- `htmlScreenshot`
- `pdfScreenshot`
- `pdfMetrics`
- `parity`
- updated prompt text telling the review subagent to compare the two images and judge whether PDF export preserved the HTML layout.

## Risks and mitigations

- **Missing native/browser runtime**: auto-install is best-effort and reports actionable errors if provisioning still fails.
- **False positives from image diff**: use the score as heuristic metadata only; final pass/fail remains a subagent page review.
- **Large context windows**: keep one page per subagent prompt, never bundle the whole document into a single visual review.

## Success criteria

- Running `python validate_print_layout.py --html <handout.html>` can self-provision missing runtime dependencies in normal environments.
- The validator exports HTML page PNGs, PDF page PNGs, PDF file, and a JSON report with parity metadata.
- Running `python review_print_pages.py --html <handout.html>` generates sequential page-review packets that explicitly compare each HTML page screenshot against its PDF-rendered counterpart.
- Targeted tests pass.
