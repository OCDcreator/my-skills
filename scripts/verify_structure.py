#!/usr/bin/env python3
"""Verify repository structure and catalog invariants for my-skills."""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
AGENTS = ROOT / "AGENTS.md"
UPDATE_SH = ROOT / "update.sh"
UPDATE_PS1 = ROOT / "update.ps1"
CATALOG = ROOT / "SKILLS.md"
FULL_CATALOG = ROOT / "docs" / "full-catalog.md"
SOURCES_YAML = ROOT / "config" / "sources.yaml"
EXTERNAL = ROOT / "external"
TMP_CLONE = ROOT / ".tmp-skills"

VALID_TIERS = frozenset({"core", "community", "bulk", "reference"})
VALID_MODES = frozenset({"flatten", "preserve"})

# Fields required for every source entry (skill or reference)
REQUIRED_FIELDS = frozenset({"name", "repo", "branch", "subdir", "mode", "tier", "include_in_main_catalog"})


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def skill_dirs() -> list[Path]:
    """Return all SKILL.md parent directories, excluding git and temp dirs."""
    excluded = {".git", ".tmp-skills"}
    return sorted(
        path.parent
        for path in ROOT.rglob("SKILL.md")
        if excluded.isdisjoint(path.parts)
    )


def parse_sources_yaml() -> dict:
    """Read config/sources.yaml as the single source of truth.

    Returns a dict with keys:
        sources: dict[name] -> source metadata
        exclude_names: list[str]
        raw: the raw parsed YAML data (for schema validation)
    """
    if not SOURCES_YAML.exists():
        return {"sources": {}, "exclude_names": [], "raw": {}}

    data = yaml.safe_load(read(SOURCES_YAML)) or {}
    sources: dict[str, dict] = {}

    for src in data.get("skill_sources", []):
        name = src.get("name", "")
        if name:
            sources[name] = {
                "name": name,
                "repo": src.get("repo", ""),
                "branch": src.get("branch", ""),
                "subdir": src.get("subdir", ""),
                "mode": src.get("mode", ""),
                "tier": src.get("tier", "community"),
                "include_in_main_catalog": src.get("include_in_main_catalog", True),
            }

    for src in data.get("reference_sources", []):
        name = src.get("name", "")
        if name:
            sources[name] = {
                "name": name,
                "repo": src.get("repo", ""),
                "branch": src.get("branch", ""),
                "subdir": src.get("subdir", ""),
                "mode": src.get("mode", ""),
                "tier": src.get("tier", "reference"),
                "include_in_main_catalog": src.get("include_in_main_catalog", False),
            }

    exclude_names: list[str] = []
    raw_excludes = data.get("exclude_names", [])
    if isinstance(raw_excludes, list):
        for item in raw_excludes:
            if isinstance(item, str):
                exclude_names.append(item)

    return {
        "sources": sources,
        "exclude_names": exclude_names,
        "raw": data,
    }


def validate_sources_schema(yaml_data: dict) -> list[str]:
    """Validate sources.yaml schema invariants. Returns a list of failure messages."""
    failures: list[str] = []

    raw = yaml_data.get("raw", {})
    if not raw:
        return failures  # missing file handled elsewhere

    # ── Collect all source entries with their section label ──
    all_sources: list[tuple[str, str, dict]] = []  # (name, section, entry_dict)
    for src in raw.get("skill_sources", []):
        name = src.get("name", "")
        if name:
            all_sources.append((name, "skill_sources", src))
    for src in raw.get("reference_sources", []):
        name = src.get("name", "")
        if name:
            all_sources.append((name, "reference_sources", src))

    # ── Check required fields ──
    for name, section, entry in all_sources:
        missing = REQUIRED_FIELDS - set(entry.keys())
        if missing:
            failures.append(
                f"Source '{name}' in {section} is missing required fields: {', '.join(sorted(missing))}"
            )

    # ── Check for duplicate names ──
    seen: dict[str, str] = {}
    for name, section, _entry in all_sources:
        if name in seen:
            failures.append(
                f"Duplicate source name '{name}' in {section} "
                f"(already defined in {seen[name]})"
            )
        else:
            seen[name] = section

    # ── Validate tier values ──
    for name, section, entry in all_sources:
        tier = entry.get("tier")
        if tier and tier not in VALID_TIERS:
            failures.append(
                f"Source '{name}' in {section} has invalid tier '{tier}'. "
                f"Must be one of: {', '.join(sorted(VALID_TIERS))}"
            )

    # ── Validate mode values ──
    for name, section, entry in all_sources:
        mode = entry.get("mode")
        if mode and mode not in VALID_MODES:
            failures.append(
                f"Source '{name}' in {section} has invalid mode '{mode}'. "
                f"Must be one of: {', '.join(sorted(VALID_MODES))}"
            )

    # ── Validate include_in_main_catalog is boolean ──
    for name, section, entry in all_sources:
        include = entry.get("include_in_main_catalog")
        if include is not None and not isinstance(include, bool):
            failures.append(
                f"Source '{name}' in {section}: include_in_main_catalog must be a boolean, got {type(include).__name__}: {include!r}"
            )

    # ── Warn on tier/catalog mismatches ──
    for name, section, entry in all_sources:
        tier = entry.get("tier", "")
        include = entry.get("include_in_main_catalog")
        if tier in ("bulk", "reference") and include is True:
            failures.append(
                f"Source '{name}' in {section}: tier '{tier}' expects include_in_main_catalog: false, but got true"
            )
        if tier in ("core", "community") and include is False:
            failures.append(
                f"Source '{name}' in {section}: tier '{tier}' expects include_in_main_catalog: true, but got false"
            )

    return failures


def discover_external_skill_dirs() -> list[str]:
    """Return list of source names found under external/ that contain SKILL.md files."""
    names: list[str] = []
    if not EXTERNAL.is_dir():
        return names
    for child in EXTERNAL.iterdir():
        if child.is_dir() and (child / "SKILL.md").exists():
            names.append(child.name)
    return sorted(names)


def main() -> int:
    failures: list[str] = []
    readme = read(README)
    agents = read(AGENTS)
    update_sh = read(UPDATE_SH)
    update_ps1 = read(UPDATE_PS1)
    catalog = read(CATALOG) if CATALOG.exists() else ""
    full_catalog = read(FULL_CATALOG) if FULL_CATALOG.exists() else ""

    parsed = parse_sources_yaml()
    sources_map = parsed["sources"]
    exclude_names = parsed["exclude_names"]

    skills = skill_dirs()

    # ── 0. Root-level skill guard ──
    root_skills = [path for path in skills if path.parent == ROOT]
    if root_skills:
        failures.append(
            "Root-level skill directories must live under custom/: "
            + ", ".join(path.name for path in root_skills)
        )

    # ── 1. Check sources.yaml exists ──
    if not SOURCES_YAML.exists():
        failures.append(
            "config/sources.yaml is missing — it is the single source of truth for external sources."
        )

    # ── 2. Schema validation of sources.yaml ──
    schema_failures = validate_sources_schema(parsed)
    failures.extend(schema_failures)

    # ── 3. Check that update.sh / update.ps1 are thin wrappers ──
    if "scripts/update_external.py" not in update_sh:
        failures.append("update.sh should delegate to scripts/update_external.py")
    if "scripts/update_external.py" not in update_ps1:
        failures.append("update.ps1 should delegate to scripts/update_external.py")

    if "SKILL_SOURCES=(" in update_sh:
        failures.append("update.sh still contains manual SKILL_SOURCES array — should use sources.yaml")
    if "$SkillSources = @(" in update_ps1:
        failures.append("update.ps1 still contains manual $SkillSources array — should use sources.yaml")

    # ── 4. Validate exclude_names from sources.yaml ──
    if exclude_names:
        for excluded in exclude_names:
            excluded_path = EXTERNAL / excluded
            if excluded_path.exists():
                # Check if it's a directory containing SKILL.md
                if excluded_path.is_dir() and (excluded_path / "SKILL.md").exists():
                    failures.append(
                        f"Excluded skill is still mirrored: external/{excluded}/ (listed in exclude_names)"
                    )
    # Also check that .tmp-skills is excluded from discovery
    if TMP_CLONE.exists() and TMP_CLONE.is_dir():
        # Verify no SKILL.md from .tmp-skills leaked into skill_dirs
        tmp_skills = sorted(path.parent for path in TMP_CLONE.rglob("SKILL.md"))
        if tmp_skills:
            failures.append(
                f".tmp-skills/ contains {len(tmp_skills)} SKILL.md files — should be cleaned up"
            )

    # ── 5. Reject unconfigured external directories ──
    external_skill_names = discover_external_skill_dirs()
    for ext_name in external_skill_names:
        if ext_name not in sources_map:
            failures.append(
                f"external/{ext_name}/ contains SKILL.md but is not configured in config/sources.yaml"
            )

    # ── 6. Check all skills are indexed in full catalog ──
    for skill in skills:
        rel = skill.relative_to(ROOT).as_posix()
        if rel.startswith("custom/") and f"{rel}/" not in readme:
            failures.append(f"README.md does not mention custom skill path: {rel}/")
        if not full_catalog:
            continue
        if f"| `{rel}` |" not in full_catalog:
            failures.append(f"docs/full-catalog.md does not index skill path: {rel}")

    # ── 7. Check curated catalog does not contain bulk skills ──
    if catalog and sources_map:
        bulk_sources = [name for name, meta in sources_map.items() if meta.get("tier") == "bulk"]
        for bulk_source in bulk_sources:
            bulk_prefix = f"external/{bulk_source}/"
            if bulk_prefix in catalog:
                failures.append(
                    f"SKILLS.md (curated) contains skills from bulk source '{bulk_source}'. "
                    f"Bulk sources should only appear in docs/full-catalog.md."
                )

    # ── 8. Check curated catalog links to full catalog ──
    if catalog and "docs/full-catalog.md" not in catalog:
        failures.append("SKILLS.md should link to docs/full-catalog.md for the complete index.")

    # ── 9. Check stale tokens ──
    forbidden_readme = ["windows-project-level-tools"]
    for token in forbidden_readme:
        if token in readme:
            failures.append(f"README.md still contains stale token: {token}")
    if re.search(r"^├── pdf-toc-bookmarker/", readme, re.M):
        failures.append("README.md still documents pdf-toc-bookmarker as a root-level skill")

    if "update.bat" in agents:
        failures.append("AGENTS.md still refers to update.bat instead of update.ps1")
    skill_maintainer = ROOT / "custom/skill-catalog-maintainer/SKILL.md"
    if skill_maintainer.exists() and "update.bat" in read(skill_maintainer):
        failures.append("skill-catalog-maintainer still refers to update.bat")

    # ── Report ──
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    # Accurate curated count: custom skills + external skills from core/community tiers
    curated_count = sum(
        1
        for s in skills
        if not str(s).startswith(str(EXTERNAL))
        or any(
            s.name.startswith(name) and meta.get("include_in_main_catalog", False)
            for name, meta in sources_map.items()
        )
    )
    print(f"OK: {len(skills)} skill directories indexed and structure checks passed.")
    print(f"     - Curated catalog (SKILLS.md): {curated_count} custom + curated external skills")
    print(f"     - Full catalog (docs/full-catalog.md): {len(skills)} total skills")
    if sources_map:
        print(f"     - Sources config (config/sources.yaml): {len(sources_map)} sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())
