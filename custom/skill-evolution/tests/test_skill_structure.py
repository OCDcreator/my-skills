"""Structural well-formedness checks for the skill-evolution skill.

Run: py -3 -m pytest custom/skill-evolution/tests/test_skill_structure.py -v
"""
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
REFERENCES = SKILL_DIR / "references"


def _read():
    return SKILL_MD.read_text(encoding="utf-8")


def test_skill_md_exists():
    assert SKILL_MD.is_file(), f"missing {SKILL_MD}"


def test_frontmatter_has_name_and_description():
    text = _read()
    assert text.startswith("---"), "SKILL.md must start with YAML frontmatter"
    head = text.split("---", 2)[1]
    assert "name: skill-evolution" in head
    assert "description:" in head and len(head) > 50


def test_skill_md_under_500_lines():
    n = len(_read().splitlines())
    assert n <= 500, f"SKILL.md is {n} lines; keep under 500 (progressive disclosure)"


def test_required_references_exist():
    required = [
        "lesson-schema.md",
        "quick-gate-criteria.md",
        "landing-zone-rules.md",
        "evolution-log-format.md",
        "dev-eval.md",
        "target-skill-scope.md",
    ]
    for name in required:
        assert (REFERENCES / name).is_file(), f"missing references/{name}"


def test_hard_contract_present():
    text = _read()
    assert "Hard Contract" in text or "## Hard Contract" in text


def test_custom_only_scope_rule_present():
    text = _read()
    assert "custom/" in text and ("only" in text.lower() or "refus" in text.lower())


def test_decision_matrix_present():
    text = _read()
    # the matrix must mention the two non-auto-resolve safety valves
    assert "conflict" in text and "human_review" in text
    assert "discard" in text and "strengthen" in text and "add_new" in text


def test_evidence_backed_claims_rule_present():
    text = _read()
    # v0.5 M2: evidence-pasting discipline
    assert "evidence" in text.lower(), "Hard Contract must require evidence-backed claims"
    assert "unverified" in text, "claims without evidence must be tagged 'unverified'"


def test_capture_provenance_present():
    text = _read()
    # v0.5 M1: CAPTURE provenance tagging + main-context execution
    assert "reconstructed" in text, "CAPTURE must tag reconstructed-vs-extracted provenance"
    assert "main orchestrating context" in text or "main context" in text.lower(), \
        "CAPTURE must run in the main orchestrating context, not a subagent"


def test_dev_eval_implemented_not_deferred():
    text = _read()
    # v0.5 S4: Step 5 Dev Eval is now implemented (references dev-eval.md), not deferred
    step5_block = text.split("### Step 5", 2)[1].split("### Step 6", 2)[0]
    assert "deferred" not in step5_block.lower(), "Step 5 Dev Eval must not still be marked deferred"
    assert "dev-eval.md" in step5_block, "Step 5 must reference references/dev-eval.md"


def test_unified_diff_approval_present():
    text = _read()
    # v0.5 S1: approval on the full unified-diff packet, not a summary
    assert "unified diff" in text.lower(), "must present a unified diff for approval"
    assert "summary" in text.lower(), "must forbid summary-only approval"


def test_known_limitation_section_present():
    text = _read()
    # v0.5 M4: Verification Ceiling documented as a known medium-property
    assert "Verification Ceiling" in text, "Known Limitation: Verification Ceiling section required"


def test_fast_path_present():
    text = _read()
    # v0.5 S2: fast path for ≤3 corrections
    assert "Fast path" in text or "fast path" in text.lower(), "fast path for ≤3 corrections required"
    assert "≤3" in text or "<=3" in text, "fast path threshold (≤3) required"
