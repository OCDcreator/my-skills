# Runtime Requirements

## Default runtime model

The bundled validator assumes a Python environment that can run Playwright and, when needed, install missing dependencies.

Default behavior:

- auto-installs missing Python packages such as `playwright` and `pymupdf`
- auto-installs Playwright Chromium when needed
- attempts to install or discover `qpdf` for PDF fast-view optimization

## Recommended environment

- Python 3.10+
- network access when dependencies are not already installed
- permission to install Python packages and browser/runtime dependencies
- enough disk space for browser artifacts, screenshots, and exported PDFs

## Auto-created local runtime directories

This skill intentionally creates a few local working directories when validation or review runs execute:

- `.venv-print/` — local Python environment for the print toolchain
- `.local-libs/` — locally installed Python packages when auto-install is used
- `.local-qpdf/` — locally discovered or installed `qpdf` helper files
- `artifacts/knowledge-handout/<slug>/` — generated working files, screenshots, and exported PDFs
- `__pycache__/` plus nested `evals/__pycache__/` / `scripts/__pycache__/` — Python bytecode caches

These are runtime byproducts, not part of the authored skill contract. In this repo they are ignored by Git and are safe to delete whenever you want to reset local state.

## High-DPI image-only PDF output

The validator's default `--device-scale-factor 1.5` is suitable for layout review, but its A4 page PNGs are only about 144 DPI. When a user asks for a 图片型 PDF / raster PDF / image-only PDF, run a separate final pass at 300 DPI:

```bash
python scripts/validate_print_layout.py --html <path> --device-scale-factor 3.125 --out-dir <artifact-dir>/screens/high-dpi
```

At the default A4 CSS page size, `--device-scale-factor 3.125` produces roughly `2478 × 3506` page images, close to 300 DPI. This is the default quality target for image-only handouts. Use 450 DPI only when the user explicitly needs print-shop raster output or the document has unusually small labels; do not default to 600 DPI.

## Restricted or offline environments

If network/package-manager access is unavailable:

1. preinstall the required Python packages
2. preinstall a Playwright-compatible Chromium runtime
3. preinstall `qpdf`
4. run:

```bash
python scripts/validate_print_layout.py --html <path> --no-auto-install
```

Use `--no-auto-install` in locked-down environments so failure is immediate and explicit instead of partially attempting installs.

## Review packet language

`scripts/review_print_pages.py` supports:

- `--review-language auto` — default; tries to match the handout language
- `--review-language en`
- `--review-language zh`

Even when the review prompt is Chinese, the JSON schema keys remain:

- `page`
- `pass`
- `issues`
- `fixes`

## Canonical entry points

Prefer:

- `python scripts/validate_print_layout.py ...`
- `python scripts/review_print_pages.py ...`

The root-level script names are compatibility wrappers for older commands and tests.
