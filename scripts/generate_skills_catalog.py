#!/usr/bin/env python3
"""Generate SKILLS.md from SKILL.md files and update.sh source metadata."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPDATE_SH = ROOT / "update.sh"
CATALOG = ROOT / "SKILLS.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def md_cell(text: str, *, limit: int | None = None) -> str:
    value = one_line(text).replace("|", "\\|")
    if limit is not None and len(value) > limit:
        value = value[: limit - 3].rstrip() + "..."
    return value


def frontmatter(path: Path) -> tuple[str, str]:
    text = read(path)
    if not text.startswith("---"):
        return path.parent.name, ""
    end = text.find("\n---", 3)
    if end == -1:
        return path.parent.name, ""
    block = text[3:end].splitlines()
    name = path.parent.name
    description = ""
    collecting_description = False
    collected: list[str] = []
    for line in block:
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip('"')
            collecting_description = False
            continue
        if line.startswith("description:"):
            value = line.split(":", 1)[1].strip()
            collecting_description = value in {">", ">-", "|", "|-"} or not value
            if value and not collecting_description:
                description = value.strip().strip('"')
            continue
        if collecting_description:
            if line and not line.startswith((" ", "\t")) and re.match(r"^[A-Za-z0-9_-]+:", line):
                collecting_description = False
                continue
            collected.append(line.strip())
    if collected:
        description = " ".join(part for part in collected if part)
    return name, one_line(description)


def parse_sources() -> dict[str, dict[str, str]]:
    sources: dict[str, dict[str, str]] = {}
    text = read(UPDATE_SH)
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
        name, url, branch, source_dir, *rest = stripped.strip('"').split("|")
        sources[name] = {
            "repo": url,
            "branch": branch,
            "source_dir": source_dir,
            "mode": rest[0] if rest else "",
        }
    return sources


def category_for(path: str, name: str, description: str) -> str:
    haystack = f"{path} {name} {description}".lower()
    if any(
        token in haystack
        for token in ["openclash", "subconverter", "sub-web", "wallrule", "proxy", "router", "qwrt"]
    ):
        return "DevOps/Config"
    if any(token in haystack for token in ["obsidian", "canvas", "bases", "vault"]):
        return "Obsidian"
    if any(token in haystack for token in ["pdf", "docx", "ppt", "xlsx", "print", "markdown", "slide"]):
        return "Documents"
    if any(token in haystack for token in ["frontend", "ui", "design", "brand", "css", "html"]):
        return "Frontend/UI"
    if any(token in haystack for token in ["search", "research", "url", "transcript", "youtube", "web"]):
        return "Web/Research"
    if any(token in haystack for token in ["image", "video", "audio", "media", "comic"]):
        return "Media"
    if any(token in haystack for token in ["agent", "mcp", "plugin", "automation", "loop", "codex", "opencode", "claude"]):
        return "Automation/Agents"
    if any(token in haystack for token in ["ssh", "sync", "provider", "config", "release", "deploy", "git", "fork"]):
        return "DevOps/Config"
    return "Content/Publishing"


def install_hint(path: str, source_repo: str, branch: str, source_subdir: str) -> str:
    return (
        f"Clone `{source_repo}` at `{branch}` and copy `{source_subdir}` to "
        "`.claude/skills/`, `.agents/skills/`, and `.opencode/skills/` as needed."
    )


def external_source_subdir(rel: str, source: dict[str, str]) -> str:
    parts = rel.split("/")
    remainder = "/".join(parts[2:])
    base = source["source_dir"]
    if source["mode"] == "preserve":
        return remainder
    if not remainder:
        return base
    if base == ".":
        return remainder
    return f"{base}/{remainder}"


def main() -> None:
    sources = parse_sources()
    skill_paths = sorted(
        path.parent.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("SKILL.md")
        if ".git" not in path.parts
    )

    rows = []
    duplicates: dict[str, list[str]] = defaultdict(list)
    for rel in skill_paths:
        name, description = frontmatter(ROOT / rel / "SKILL.md")
        duplicates[name].append(rel)
        if rel.startswith("custom/"):
            source_repo = "git@github.com:OCDcreator/my-skills.git"
            branch = "main"
            source_subdir = rel
        elif rel.startswith("external/"):
            source_name = rel.split("/")[1]
            source = sources.get(source_name, {})
            source_repo = source.get("repo", "Needs source review")
            branch = source.get("branch", "Needs source review")
            source_subdir = external_source_subdir(rel, source) if source else "Needs source review"
        else:
            source_repo = "git@github.com:OCDcreator/my-skills.git"
            branch = "main"
            source_subdir = rel
        category = category_for(rel, name, description)
        rows.append(
            {
                "path": rel,
                "name": name,
                "description": description or "Needs review",
                "category": category,
                "repo": source_repo,
                "branch": branch,
                "source_subdir": source_subdir,
                "install": install_hint(rel, source_repo, branch, source_subdir),
            }
        )

    custom_rows = [row for row in rows if row["path"].startswith("custom/")]
    external_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["path"].startswith("external/"):
            external_groups[row["path"].split("/")[1]].append(row)

    duplicate_lines = [
        f"- `{name}`: " + ", ".join(f"`{path}`" for path in paths)
        for name, paths in sorted(duplicates.items())
        if len(paths) > 1
    ]

    lines: list[str] = [
        "# Skills Catalog",
        "",
        f"Generated from repository state on {date.today().isoformat()}.",
        "",
        "## Quick Picker",
        "",
        "| Need | Recommended skill(s) | Notes |",
        "|---|---|---|",
        "| Choose the right repo-local skill before real work | `custom/skill-router` | Reads this source repo instead of installed mirrors. |",
        "| Maintain README, AGENTS, SKILLS, or mirrored sources | `custom/skill-catalog-maintainer` | Keeps source paths, install hints, and duplicate names explicit. |",
        "| Obsidian plugin debug or runtime validation | `custom/obsidian-plugin-autodebug` | Use project profiles for plugin-specific assertions. |",
        "| OpenCode unattended coding loop | `custom/opencode-loop` | Use for self-healing multi-iteration project work. |",
        "| Brand/product style reference before UI work | `custom/design-reference-router` | Routes to concrete `awesome-design-md` references first. |",
        "",
        "## Common Combinations",
        "",
        "| Workflow | Skill combination | Why |",
        "|---|---|---|",
        "| Add or reorganize skills | `skill-catalog-maintainer` + this catalog | Update docs and indexes together. |",
        "| Obsidian plugin release proof | `obsidian-plugin-release-manager` + `obsidian-plugin-autodebug` + `obsidian-plugin-debug-logging` | Version, deploy, and verify runtime behavior. |",
        "| Project-level agent tooling | `project-level-tools` + `lean-ctx-deploy` | Keep GitNexus and lean-ctx local to one repo. |",
        "",
        "## Custom Skills",
        "",
        "| Path | Name | Use when |",
        "|---|---|---|",
    ]

    for row in custom_rows:
        lines.append(f"| `{row['path']}` | `{row['name']}` | {md_cell(row['description'], limit=420)} |")

    lines.extend(["", "## External Skills", "", "| Source | Notable skills | Use when |", "|---|---|---|"])
    for source_name, group in sorted(external_groups.items()):
        notable = ", ".join(f"`{row['name']}`" for row in group[:8])
        if len(group) > 8:
            notable += f", ... ({len(group)} total)"
        source = sources.get(source_name, {})
        use_when = f"Mirrored from `{source.get('repo', 'Needs source review')}`."
        lines.append(f"| `{source_name}` | {notable} | {use_when} |")

    if duplicate_lines:
        lines.extend(["", "## Duplicate Names", "", "Duplicate names are expected for external sources; select by path and source, not name alone.", ""])
        lines.extend(duplicate_lines)

    lines.extend(
        [
            "",
            "## Full Index",
            "",
            "| Path | Name | Category | Use when | Source repo | Source branch | Source subdir | Install hint |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| `{row['path']}` | `{row['name']}` | {row['category']} | {md_cell(row['description'], limit=360)} | "
            f"`{row['repo']}` | `{row['branch']}` | `{row['source_subdir']}` | {row['install']} |"
        )

    CATALOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {CATALOG.relative_to(ROOT)} with {len(rows)} skills.")


if __name__ == "__main__":
    main()
