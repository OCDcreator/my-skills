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
