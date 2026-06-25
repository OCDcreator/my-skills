#!/usr/bin/env python3
"""Apply figure band-floor fixes to a handout.html, driven by validate_sheet_bottom_margin.py's hints.

WHY THIS EXISTS (evolved 2026-06-25):
  A weak model (deepseek-v4-flash) reads SKILL.md's "narrow to the exact floor"
  rule but executes imprecisely — it sees "floor 47%" yet writes width: 51% in
  its job-local CSS, leaving the trailing-blank FAIL unresolved. This is a model
  execution-precision limit, not a skill-guidance gap (the rule names the exact
  number; the model still rounds). Rather than depend on the model's precision,
  this script performs the precise narrowing by CODE: it reads the validator's
  machine-parseable `FIX: src=<frag> floor=<pct>` hints and injects an exact
  `img[src*="<frag>"] { width: <pct>% !important; max-width: <pct>% !important; }`
  job-local CSS rule for each. This is the "constrain via code" path: the model
  runs the pipeline, the code guarantees the floor is hit exactly.

CONTRACT:
  - Idempotent: re-running updates the `figure-floor-fixes` style block in place
    (removes the old block, writes a fresh one) rather than stacking duplicates.
  - Conservative: only narrows (floor < current), never widens; only acts on
    `FIX:` lines the validator emits, so it cannot invent fixes.
  - Never edits source-transcript.md — only handout.html's own <style>.

USAGE:
  py -3 apply_figure_floor_fixes.py --html handout.html
  # (run validate_sheet_bottom_margin.py first; this reads its FAIL output)

Exit codes: 0 = applied (or no fixes needed), 1 = error.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate_sheet_bottom_margin.py"
STYLE_BLOCK_ID = "figure-floor-fixes"  # marker comment to find/replace the block

FIX_LINE_RE = re.compile(r"FIX:\s*src=(\S+)\s+floor=(\d+)")


def collect_fixes(validator_output: str) -> list[tuple[str, int]]:
    """Parse `FIX: src=<frag> floor=<pct>` lines → list of (src_fragment, floor_pct)."""
    fixes = []
    for m in FIX_LINE_RE.finditer(validator_output):
        src_frag = m.group(1)
        floor = int(m.group(2))
        fixes.append((src_frag, floor))
    return fixes


def build_css_block(fixes: list[tuple[str, int]]) -> str:
    """Build the job-local <style> block content for the fixes."""
    lines = [
        f"/* job-local {STYLE_BLOCK_ID}: applied by apply_figure_floor_fixes.py",
        "   from validate_sheet_bottom_margin.py FIX hints. Narrows each flagged",
        "   figure to its EXACT band floor so it moves up and clears the trailing",
        "   blank. Do not hand-edit; re-run the script to regenerate. */",
    ]
    for src_frag, floor in fixes:
        lines.append(
            f'img[src*="{src_frag}"] {{'
            f" width: {floor}% !important;"
            f" max-width: {floor}% !important;"
            f" height: auto !important;"
            f"}}"
        )
    lines.append("/* end figure-floor-fixes */")
    return "\n".join(lines)


def apply_fixes(html_path: Path, fixes: list[tuple[str, int]]) -> bool:
    """Inject/replace the figure-floor-fixes <style> block in html_path.

    Returns True if the file was modified.
    """
    html = html_path.read_text(encoding="utf-8")
    new_block_inner = build_css_block(fixes)
    new_style = f'<style id="{STYLE_BLOCK_ID}">\n{new_block_inner}\n</style>'

    # Remove any existing figure-floor-fixes block (idempotent update).
    # Match from the opening <style id="..."> to its closing </style>.
    existing_re = re.compile(
        r'<style id="' + re.escape(STYLE_BLOCK_ID) + r'">.*?</style>',
        re.DOTALL,
    )
    html_cleaned, n_existing = existing_re.subn("", html)

    # Append the (fresh) block just before </head>; if no </head>, before </body>.
    if "</head>" in html_cleaned:
        html_out = html_cleaned.replace("</head>", new_style + "\n</head>", 1)
    elif "</body>" in html_cleaned:
        html_out = html_cleaned.replace("</body>", new_style + "\n</body>", 1)
    else:
        html_out = html_cleaned + "\n" + new_style

    if html_out != html:
        html_path.write_text(html_out, encoding="utf-8")
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--html", required=True, help="Path to handout.html")
    parser.add_argument(
        "--validator",
        default=str(VALIDATOR),
        help="Path to validate_sheet_bottom_margin.py (default: sibling script)",
    )
    args = parser.parse_args()

    html_path = Path(args.html).expanduser().resolve()
    if not html_path.is_file():
        print(f"ERROR: not a file: {html_path}", file=sys.stderr)
        return 1

    # Run the validator to collect FIX hints.
    result = subprocess.run(
        [sys.executable, args.validator, "--html", str(html_path)],
        capture_output=True,
        text=True,
    )
    fixes = collect_fixes(result.stdout)
    if not fixes:
        print("No figure-floor FIX hints from validator. Nothing to apply.")
        return 0

    print(f"Collected {len(fixes)} figure-floor fix(es):")
    for src_frag, floor in fixes:
        print(f"  src~{src_frag}  →  floor {floor}%")

    changed = apply_fixes(html_path, fixes)
    if changed:
        print(f"Applied: injected/updated <style id=\"{STYLE_BLOCK_ID}\"> in {html_path.name}")
        print("Re-run validate_sheet_bottom_margin.py to confirm the FAILs cleared.")
    else:
        print("No change needed (fixes already applied).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
