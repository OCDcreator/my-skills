"""Compatibility wrapper for older commands and tests.

Prefer `python scripts/validate_print_layout.py ...` in new instructions.
"""

from scripts.validate_print_layout import main


if __name__ == "__main__":
    raise SystemExit(main())
