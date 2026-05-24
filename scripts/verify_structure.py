#!/usr/bin/env python3
"""Verify repository structure and catalog invariants for my-skills."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
AGENTS = ROOT / "AGENTS.md"
UPDATE_SH = ROOT / "update.sh"
UPDATE_PS1 = ROOT / "update.ps1"
CATALOG = ROOT / "SKILLS.md"


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


def main() -> int:
    failures: list[str] = []
    readme = read(README)
    agents = read(AGENTS)
    update_sh = read(UPDATE_SH)
    update_ps1 = read(UPDATE_PS1)
    catalog = read(CATALOG) if CATALOG.exists() else ""

    skills = skill_dirs()
    root_skills = [path for path in skills if path.parent == ROOT]
    if root_skills:
        failures.append(
            "Root-level skill directories must live under custom/: "
            + ", ".join(path.name for path in root_skills)
        )

    for skill in skills:
        rel = skill.relative_to(ROOT).as_posix()
        if rel.startswith("custom/") and f"{rel}/" not in readme:
            failures.append(f"README.md does not mention custom skill path: {rel}/")
        if not catalog:
            continue
        if f"| `{rel}` |" not in catalog:
            failures.append(f"SKILLS.md does not index skill path: {rel}")

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

    sh_sources = parse_sh_skill_sources(update_sh)
    ps1_sources = parse_ps1_skill_sources(update_ps1)
    if sh_sources != ps1_sources:
        failures.append("update.ps1 SKILL_SOURCES do not match update.sh")

    sh_excludes = parse_sh_excludes(update_sh)
    ps1_excludes = parse_ps1_excludes(update_ps1)
    if sh_excludes != ps1_excludes:
        failures.append("update.ps1 EXCLUDE_NAMES do not match update.sh")

    for excluded in sh_excludes:
        for path in (ROOT / "external").rglob(excluded):
            if path.is_dir() and (path / "SKILL.md").exists():
                failures.append(f"Excluded example/template skill is still mirrored: {path.relative_to(ROOT)}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(f"OK: {len(skills)} skill directories indexed and structure checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
