"""Compatibility wrapper for older commands and tests.

Prefer `python scripts/review_print_pages.py ...` in new instructions.
"""

from scripts.review_print_pages import main


if __name__ == "__main__":
    raise SystemExit(main())
