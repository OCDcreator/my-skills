"""Tests for the `--only` flag: filtering which lints run.

The `--only` flag exists to support the refinement-agent-chain self-check
(references/refinement-agent-chain.md), where each role runs ONLY its own lints
so it sees only its own FAILs and can fix them in place. These tests lock that
contract: a named subset runs, unknown names fail loudly, and the default
(no --only) behavior is unchanged.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_canonical_markdown.py"


def run_validator(tmp_path: Path, markdown: str, *extra_args: str) -> subprocess.CompletedProcess[str]:
    md_path = tmp_path / "source-transcript.md"
    md_path.write_text(markdown, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--md", str(md_path), *extra_args],
        check=False,
        capture_output=True,
        text=True,
    )


# A markdown sample that triggers TWO defects from TWO different lints:
#   - "# Source Transcript"  → lint_headings_and_print_noise  ("top title must describe")
#   - plain "\frac"          → lint_formulas                   ("plain \\frac is not allowed")
# Using two real, distinct lints is what proves --only narrows which defects surface.
SAMPLE_WITH_TWO_DEFECTS = """# Source Transcript

## 第一节

已知 $\\frac{1}{2}$，求值。
"""


def test_only_runs_just_the_named_lint(tmp_path: Path) -> None:
    """`--only lint_formulas` surfaces the \frac defect but NOT the title defect
    (which belongs to lint_headings_and_print_noise)."""
    result = run_validator(tmp_path, SAMPLE_WITH_TWO_DEFECTS, "--only", "lint_formulas")
    assert result.returncode == 1, f"expected FAIL (frac defect present), got rc=0\n{result.stdout}"
    assert "frac" in result.stdout.lower(), f"formulas lint should fire\n{result.stdout}"
    # The title defect belongs to a DIFFERENT lint and must NOT surface under --only lint_formulas.
    assert "top title" not in result.stdout.lower(), (
        f"--only must suppress other lints; title defect leaked through\n{result.stdout}"
    )


def test_only_supports_comma_separated_list(tmp_path: Path) -> None:
    """`--only a,b` runs both; both defects surface."""
    result = run_validator(
        tmp_path,
        SAMPLE_WITH_TWO_DEFECTS,
        "--only",
        "lint_formulas,lint_headings_and_print_noise",
    )
    assert result.returncode == 1
    assert "frac" in result.stdout.lower()
    assert "top title" in result.stdout.lower()


def test_only_unknown_name_aborts(tmp_path: Path) -> None:
    """Unknown lint name → non-zero exit + ERROR line naming the unknown.
    Unknown names are a caller bug (stale role->lint mapping) and must abort
    loudly, never silently run nothing."""
    md_path = tmp_path / "source-transcript.md"
    md_path.write_text("# ok\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--md", str(md_path), "--only", "lint_nonexistent"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    combined = (result.stdout + result.stderr).lower()
    assert "unknown lint name" in combined


def test_default_no_only_runs_everything(tmp_path: Path) -> None:
    """Without --only, both defects surface (regression guard: the flag must not
    change default behavior)."""
    result = run_validator(tmp_path, SAMPLE_WITH_TWO_DEFECTS)
    assert result.returncode == 1
    assert "frac" in result.stdout.lower()
    assert "top title" in result.stdout.lower()


def test_only_on_clean_subset_returns_ok(tmp_path: Path) -> None:
    """When --only selects a lint whose target is clean, exit 0 (no FAIL)."""
    # No \frac here, so --only lint_formulas passes even though the title is generic
    # (the title defect is in a different lint that --only excludes).
    clean = "# 实文档\n\n## 第一节\n\n正文。\n"
    result = run_validator(tmp_path, clean, "--only", "lint_formulas")
    assert result.returncode == 0, f"expected OK, got\n{result.stdout}"
    assert "ok" in result.stdout.lower()


def test_only_rejects_lint_proofreading_which_lives_on_its_own_branch(tmp_path: Path) -> None:
    """`lint_proofreading` is NOT in the lint_markdown() registry — it lives on
    its own `--check-proofreading` CLI branch. So `--only lint_proofreading` must
    error with 'unknown lint name', NOT silently run nothing. This locks the
    contract documented in refinement-agent-chain.md (role ⑥ uses
    `--check-proofreading`, not `--only`)."""
    md_path = tmp_path / "source-transcript.md"
    md_path.write_text("# 实文档\n\n## 第一节\n\n正文。\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--md", str(md_path), "--only", "lint_proofreading"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    combined = (result.stdout + result.stderr).lower()
    assert "unknown lint name" in combined
    assert "lint_proofreading" in combined

