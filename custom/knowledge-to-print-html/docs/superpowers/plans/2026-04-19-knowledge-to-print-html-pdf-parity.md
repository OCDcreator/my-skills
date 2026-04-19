# Knowledge-to-Print HTML PDF Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add automatic dependency provisioning, PDF page rendering, and per-page HTML-vs-PDF subagent review support to `custom/knowledge-to-print-html`.

**Architecture:** Extend the existing validator instead of adding a new entrypoint. Keep automatic checks lightweight and deterministic, and hand visual parity judgment to one fresh review subagent per page through enriched review packets.

**Tech Stack:** Python, Playwright, PyMuPDF, `unittest`

---

### Task 1: Lock the desired behavior with tests

**Files:**
- Modify: `custom/knowledge-to-print-html/evals/test_print_tools.py`

- [ ] Add failing unit tests for dependency auto-install orchestration.
- [ ] Add failing unit tests for PDF parity metadata/report helpers.
- [ ] Add failing unit tests proving review packets include both HTML and PDF screenshot references and parity-review instructions.

### Task 2: Extend validator dependency bootstrapping and PDF parity output

**Files:**
- Modify: `custom/knowledge-to-print-html/validate_print_layout.py`
- Test: `custom/knowledge-to-print-html/evals/test_print_tools.py`

- [ ] Refactor optional imports behind lazy helper functions.
- [ ] Add best-effort auto-install helpers for `playwright`, Playwright Chromium runtime, and `pymupdf`.
- [ ] Render exported PDF pages to PNGs and record their metadata.
- [ ] Add lightweight per-page parity metadata plus required checks.
- [ ] Run the targeted validator tests after each green step.

### Task 3: Extend sequential review packets for HTML vs PDF page review

**Files:**
- Modify: `custom/knowledge-to-print-html/review_print_pages.py`
- Test: `custom/knowledge-to-print-html/evals/test_print_tools.py`

- [ ] Thread PDF screenshot/parity data into each page review packet.
- [ ] Update subagent prompt wording to require single-page HTML-vs-PDF comparison.
- [ ] Keep sequential gating semantics unchanged while expanding review scope.

### Task 4: Update skill documentation

**Files:**
- Modify: `custom/knowledge-to-print-html/SKILL.md`

- [ ] Document automatic PDF export, auto-install behavior, and per-page HTML-vs-PDF subagent review requirements.
- [ ] Clarify that page packets now include both HTML and PDF screenshots and must be reviewed in sequence.

### Task 5: Verify the skill changes

**Files:**
- Test: `custom/knowledge-to-print-html/evals/test_print_tools.py`

- [ ] Run targeted unit tests for `custom/knowledge-to-print-html/evals/test_print_tools.py`.
- [ ] Review the generated output and confirm no unrelated files were changed.
