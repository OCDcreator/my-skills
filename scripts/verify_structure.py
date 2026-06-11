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


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def skill_dirs() -> list[Path]:
    return sorted(path.parent for path in ROOT.rglob("SKILL.md") if ".git" not in path.parts)


def parse_sh_skill_sources(text: str) -> dict[str, tuple[str, str, str, str]]:
    sources: dict[str, tuple[str, str, str, str]] = {}
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "SKILL_SOURCES=(":
            in_block = True
            continue
        if in_block and stripped == ")":
            break
        if not in_block or not stripped.startswith('"'):
            continue
        entry = stripped.strip('"')
        name, url, branch, source_dir, *rest = entry.split("|")
        copy_mode = rest[0] if rest else ""
        sources[name] = (url, branch, source_dir, copy_mode)
    return sources


def parse_ps1_skill_sources(text: str) -> dict[str, tuple[str, str, str, str]]:
    sources: dict[str, tuple[str, str, str, str]] = {}
    pattern = re.compile(
        r'@\{\s*Name\s*=\s*"([^"]+)";\s*Url\s*=\s*"([^"]+)";\s*'
        r'Branch\s*=\s*"([^"]+)";\s*SourceDir\s*=\s*"([^"]+)"'
        r'(?:;\s*CopyMode\s*=\s*"([^"]+)")?\s*\}'
    )
    for match in pattern.finditer(text):
        name, url, branch, source_dir, copy_mode = match.groups()
        sources[name] = (url, branch, source_dir, copy_mode or "")
    return sources


def parse_sh_excludes(text: str) -> list[str]:
    excludes: list[str] = []
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "EXCLUDE_NAMES=(":
            in_block = True
            continue
        if in_block and stripped == ")":
            break
        if in_block and stripped.startswith('"'):
            excludes.append(stripped.strip('"'))
    return sorted(excludes)


def parse_ps1_excludes(text: str) -> list[str]:
    match = re.search(r"\$ExcludeNames\s*=\s*@\((.*?)\)", text, re.S)
    if not match:
        return []
    return sorted(re.findall(r'"([^"]+)"', match.group(1)))


def parse_sources_yaml() -> dict[str, dict[str, str | bool]]:
    """Read config/sources.yaml as the single source of truth."""
    if not SOURCES_YAML.exists():
        return {}
    data = yaml.safe_load(read(SOURCES_YAML))
    sources: dict[str, dict[str, str | bool]] = {}
    for src in data.get("skill_sources", []):
        sources[src["name"]] = {
            "repo": src.get("repo", ""),
            "branch": src.get("branch", ""),
            "subdir": src.get("subdir", ""),
            "mode": src.get("mode", ""),
            "tier": src.get("tier", "community"),
            "include_in_main_catalog": src.get("include_in_main_catalog", True),
        }
    for src in data.get("reference_sources", []):
        sources[src["name"]] = {
            "repo": src.get("repo", ""),
            "branch": src.get("branch", ""),
            "subdir": src.get("subdir", ""),
            "mode": src.get("mode", ""),
            "tier": src.get("tier", "reference"),
            "include_in_main_catalog": src.get("include_in_main_catalog", False),
        }
    return sources


def main() -> int:
    failures: list[str] = []
    readme = read(README)
    agents = read(AGENTS)
    update_sh = read(UPDATE_SH)
    update_ps1 = read(UPDATE_PS1)
    catalog = read(CATALOG) if CATALOG.exists() else ""
    full_catalog = read(FULL_CATALOG) if FULL_CATALOG.exists() else ""
    sources_yaml = parse_sources_yaml()

    skills = skill_dirs()
    root_skills = [path for path in skills if path.parent == ROOT]
    if root_skills:
        failures.append(
            "Root-level skill directories must live under custom/: "
            + ", ".join(path.name for path in root_skills)
        )

    # 1. Check sources.yaml exists
    if not SOURCES_YAML.exists():
        failures.append("config/sources.yaml is missing — it is the single source of truth for external sources.")
    else:
        # 2. Check that update.sh / update.ps1 sources match sources.yaml
        sh_sources = parse_sh_skill_sources(update_sh)
        ps1_sources = parse_ps1_skill_sources(update_ps1)
        
        yaml_skill_sources = {k: v for k, v in sources_yaml.items() if v.get("tier") != "reference"}
        
        # Compare by name presence (full migration to sources.yaml will happen later)
        sh_names = set(sh_sources.keys())
        ps1_names = set(ps1_sources.keys())
        yaml_names = set(yaml_skill_sources.keys())
        
        if sh_names != yaml_names:
            missing_in_yaml = sh_names - yaml_names
            missing_in_sh = yaml_names - sh_names
            if missing_in_yaml:
                failures.append(f"update.sh sources not in sources.yaml: {missing_in_yaml}")
            if missing_in_sh:
                failures.append(f"sources.yaml sources not in update.sh: {missing_in_sh}")
        
        if ps1_names != yaml_names:
            missing_in_yaml = ps1_names - yaml_names
            missing_in_ps1 = yaml_names - ps1_names
            if missing_in_yaml:
                failures.append(f"update.ps1 sources not in sources.yaml: {missing_in_yaml}")
            if missing_in_ps1:
                failures.append(f"sources.yaml sources not in update.ps1: {missing_in_ps1}")

    # 3. Check EXCLUDE_NAMES match
    sh_excludes = parse_sh_excludes(update_sh)
    ps1_excludes = parse_ps1_excludes(update_ps1)
    if sh_excludes != ps1_excludes:
        failures.append("update.ps1 EXCLUDE_NAMES do not match update.sh")

    for excluded in sh_excludes:
        for path in (ROOT / "external").rglob(excluded):
            if path.is_dir() and (path / "SKILL.md").exists():
                failures.append(f"Excluded example/template skill is still mirrored: {path.relative_to(ROOT)}")

    # 4. Check all skills are indexed in full catalog
    for skill in skills:
        rel = skill.relative_to(ROOT).as_posix()
        if rel.startswith("custom/") and f"{rel}/" not in readme:
            failures.append(f"README.md does not mention custom skill path: {rel}/")
        if not full_catalog:
            continue
        if f"| `{rel}` |" not in full_catalog:
            failures.append(f"docs/full-catalog.md does not index skill path: {rel}")

    # 5. Check curated catalog does not contain bulk skills
    if catalog and sources_yaml:
        bulk_sources = [name for name, meta in sources_yaml.items() if meta.get("tier") == "bulk"]
        for bulk_source in bulk_sources:
            # Check if any skill from bulk source appears in curated catalog
            bulk_prefix = f"external/{bulk_source}/"
            if bulk_prefix in catalog:
                failures.append(
                    f"SKILLS.md (curated) contains skills from bulk source '{bulk_source}'. "
                    f"Bulk sources should only appear in docs/full-catalog.md."
                )

    # 6. Check curated catalog links to full catalog
    if catalog and "docs/full-catalog.md" not in catalog:
        failures.append("SKILLS.md should link to docs/full-catalog.md for the complete index.")

    # 7. Check stale tokens
    forbidden_readme = ["windows-project-level-tools"]
    for token in forbidden_readme:
        if token in readme:
            failures.append(f"README.md still contains stale token: {token}")
    if re.search(r"^├── pdf-toc-bookmarker/", readme, re.M):
        failures.append("README.md still documents pdf-toc-bookmarker as a root-level skill")

    if "update.bat" in agents:
        failures.append("AGENTS.md still refers to update.bat instead of update.ps1")
    if "update.bat" in read(ROOT / "custom/skill-catalog-maintainer/SKILL.md"):
        failures.append("skill-catalog-maintainer still refers to update.bat")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(f"OK: {len(skills)} skill directories indexed and structure checks passed.")
    print(f"     - Curated catalog (SKILLS.md): {len([s for s in skills if not str(s).startswith(str(ROOT / 'external'))])} custom + curated external")
    print(f"     - Full catalog (docs/full-catalog.md): {len(skills)} total skills")
    if sources_yaml:
        print(f"     - Sources config (config/sources.yaml): {len(sources_yaml)} sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())
