#!/usr/bin/env python3
"""Generate curated SKILLS.md and full docs/full-catalog.md from SKILL.md files."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


ROOT = Path(__file__).resolve().parents[1]
SOURCES_YAML = ROOT / "config" / "sources.yaml"
CATALOG = ROOT / "SKILLS.md"
FULL_CATALOG = ROOT / "docs" / "full-catalog.md"
README = ROOT / "README.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def md_cell(text: str, *, limit: int | None = None) -> str:
    value = one_line(text).replace("|", "\\|")
    if limit is not None and len(value) > limit:
        value = value[: limit - 3].rstrip() + "..."
    return value


def frontmatter(path: Path) -> tuple[str, str, list[str], list[str]]:
    text = read(path)
    if not text.startswith("---"):
        return path.parent.name, "", [], []
    end = text.find("\n---", 3)
    if end == -1:
        return path.parent.name, "", [], []
    block = text[3:end].splitlines()
    name = path.parent.name
    description = ""
    tags: list[str] = []
    triggers: list[str] = []
    collecting_description = False
    collecting_tags = False
    collecting_triggers = False
    collected: list[str] = []
    for line in block:
        # Handle continuation of multiline description blocks
        if collecting_description:
            if line and not line.startswith((" ", "\t")) and re.match(r"^[A-Za-z0-9_-]+:", line):
                collecting_description = False
                # Fall through to handle the new key (e.g. tags:, triggers:)
            else:
                collected.append(line.strip())
                continue
        # Handle continuation of block-list tags
        if collecting_tags:
            stripped = line.strip()
            if stripped.startswith("- "):
                tag = stripped[2:].strip().strip('"').strip("'")
                if tag:
                    tags.append(tag)
                continue
            elif stripped and re.match(r"^[A-Za-z0-9_-]+:", line):
                collecting_tags = False
                # Fall through
            else:
                continue
        # Handle continuation of block-list triggers
        if collecting_triggers:
            stripped = line.strip()
            if stripped.startswith("- "):
                trigger = stripped[2:].strip().strip('"').strip("'")
                if trigger:
                    triggers.append(trigger)
                continue
            elif stripped and re.match(r"^[A-Za-z0-9_-]+:", line):
                collecting_triggers = False
                # Fall through
            else:
                continue

        # Parse keys
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip('"')
            continue
        if line.startswith("tags:"):
            value = line.split(":", 1)[1].strip()
            if value.startswith("[") and value.endswith("]"):
                # Inline YAML list: tags: [search, research, web]
                inner = value[1:-1]
                tags = [t.strip().strip('"').strip("'") for t in inner.split(",") if t.strip()]
            elif value:
                # Single value: tags: search
                tags = [value.strip().strip('"').strip("'")]
            else:
                collecting_tags = True
            continue
        if line.startswith("triggers:"):
            value = line.split(":", 1)[1].strip()
            if value.startswith("[") and value.endswith("]"):
                # Inline YAML list: triggers: ["search the web", "find information"]
                inner = value[1:-1]
                triggers = [t.strip().strip('"').strip("'") for t in inner.split(",") if t.strip()]
            elif value:
                # Single value: triggers: search the web
                triggers = [value.strip().strip('"').strip("'")]
            else:
                collecting_triggers = True
            continue
        if line.startswith("description:"):
            value = line.split(":", 1)[1].strip()
            collecting_description = value in {">", ">-", "|", "|-"} or not value
            if value and not collecting_description:
                description = value.strip().strip('"')
            continue
    if collected:
        description = " ".join(part for part in collected if part)
    return name, one_line(description), tags, triggers


def parse_sources_yaml() -> dict[str, dict[str, str | bool]]:
    """Read config/sources.yaml as the single source of truth."""
    if not SOURCES_YAML.exists():
        print(f"ERROR: {SOURCES_YAML} not found. Run from repo root.")
        sys.exit(1)
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


def external_source_subdir(rel: str, source: dict[str, str | bool]) -> str:
    parts = rel.split("/")
    remainder = "/".join(parts[2:])
    base = str(source.get("subdir", ""))
    mode = str(source.get("mode", ""))
    if mode == "preserve":
        return remainder
    if not remainder:
        return base
    if base == ".":
        return remainder
    return f"{base}/{remainder}"


def build_rows(skill_paths: list[str], sources: dict[str, dict[str, str | bool]]) -> list[dict[str, str]]:
    rows = []
    for rel in skill_paths:
        name, description, tags, triggers = frontmatter(ROOT / rel / "SKILL.md")
        if rel.startswith("custom/"):
            source_repo = "git@github.com:OCDcreator/my-skills.git"
            branch = "main"
            source_subdir = rel
            tier = "custom"
            include_in_main = True
        elif rel.startswith("external/"):
            source_name = rel.split("/")[1]
            if source_name not in sources:
                print(f"WARNING: external/{source_name}/ is not configured in sources.yaml. Skipping.")
                continue
            source = sources[source_name]
            # Skip reference sources — they are not skills
            if source.get("tier") == "reference":
                continue
            source_repo = str(source.get("repo", "Needs source review"))
            branch = str(source.get("branch", "Needs source review"))
            source_subdir = external_source_subdir(rel, source) if source else "Needs source review"
            tier = str(source.get("tier", "community"))
            raw = source.get("include_in_main_catalog", True)
            if not isinstance(raw, bool):
                print(f"WARNING: include_in_main_catalog for {source_name} is not a boolean: {raw!r}. Defaulting to True.")
                raw = True
            include_in_main = raw
        else:
            source_repo = "git@github.com:OCDcreator/my-skills.git"
            branch = "main"
            source_subdir = rel
            tier = "custom"
            include_in_main = True
        category = category_for(rel, name, description)
        rows.append(
            {
                "path": rel,
                "name": name,
                "description": description or "Needs review",
                "tags": tags,
                "triggers": triggers,
                "category": category,
                "repo": source_repo,
                "branch": branch,
                "source_subdir": source_subdir,
                "install": install_hint(rel, source_repo, branch, source_subdir),
                "tier": tier,
                "include_in_main": include_in_main,
            }
        )
    return rows


def generate_curated_catalog(rows: list[dict[str, str]]) -> list[str]:
    """Generate the curated SKILLS.md (Quick Picker + Custom + curated External)."""
    custom_rows = [row for row in rows if row["path"].startswith("custom/")]
    curated_external = [row for row in rows if row["path"].startswith("external/") and row["include_in_main"]]
    external_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in curated_external:
        external_groups[row["path"].split("/")[1]].append(row)

    lines: list[str] = [
        "# Skills Catalog",
        "",
        f"Generated from repository state on {date.today().isoformat()}.",
        "",
        "This is the **curated** quick-reference index. For the complete list of all 1000+ skills, see [`docs/full-catalog.md`](docs/full-catalog.md).",
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

    if external_groups:
        lines.extend(["", "## External Skills (Curated)", "", "| Source | Tier | Notable skills | Use when |", "|---|---|---|---|"])
        for source_name, group in sorted(external_groups.items()):
            notable = ", ".join(f"`{row['name']}`" for row in group[:8])
            if len(group) > 8:
                notable += f", ... ({len(group)} total)"
            tier = group[0].get("tier", "community")
            tier_badge = f"`{tier}`"
            use_when = f"Mirrored from `{group[0]['repo']}`."
            lines.append(f"| `{source_name}` | {tier_badge} | {notable} | {use_when} |")

    lines.extend([
        "",
        "## Bulk / Archive Sources",
        "",
        "These sources are mirrored but excluded from the main catalog to reduce noise. See [`docs/full-catalog.md`](docs/full-catalog.md) for the complete index.",
        "",
        "| Source | Tier | Why hidden |",
        "|---|---|---|",
        "| `awesome-claude-skills` | bulk | 863 low-signal automation skills (`Automate X via Rube MCP`). Available in full catalog. |",
        "",
    ])

    return lines


def generate_full_catalog(rows: list[dict[str, str]]) -> list[str]:
    """Generate the complete docs/full-catalog.md with all skills."""
    custom_rows = [row for row in rows if row["path"].startswith("custom/")]
    external_rows = [row for row in rows if row["path"].startswith("external/")]
    external_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in external_rows:
        external_groups[row["path"].split("/")[1]].append(row)

    duplicates: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        duplicates[row["name"]].append(row["path"])

    duplicate_lines = [
        f"- `{name}`: " + ", ".join(f"`{path}`" for path in paths)
        for name, paths in sorted(duplicates.items())
        if len(paths) > 1
    ]

    lines: list[str] = [
        "# Full Skills Catalog",
        "",
        f"Generated from repository state on {date.today().isoformat()}.",
        "",
        "This file contains the **complete** index of all skills in the repository, including bulk sources. For the curated quick-reference, see [`SKILLS.md`](../SKILLS.md).",
        "",
        "## Stats",
        "",
        f"- **Total skills**: {len(rows)}",
        f"- **Custom skills**: {len(custom_rows)}",
        f"- **External sources**: {len(external_groups)}",
        f"- **External skills**: {len(external_rows)}",
        "",
        "## Custom Skills",
        "",
        "| Path | Name | Category | Use when |",
        "|---|---|---|---|",
    ]

    for row in custom_rows:
        lines.append(f"| `{row['path']}` | `{row['name']}` | {row['category']} | {md_cell(row['description'], limit=360)} |")

    lines.extend(["", "## External Skills by Source", ""])
    for source_name, group in sorted(external_groups.items()):
        lines.extend([
            f"### `{source_name}` ({len(group)} skills)",
            "",
            "| Path | Name | Category | Use when |",
            "|---|---|---|---|",
        ])
        for row in group:
            lines.append(f"| `{row['path']}` | `{row['name']}` | {row['category']} | {md_cell(row['description'], limit=360)} |")
        lines.append("")

    if duplicate_lines:
        lines.extend(["", "## Duplicate Names", "", "Duplicate names are expected for external sources; select by path and source, not name alone.", ""])
        lines.extend(duplicate_lines)

    lines.extend([
        "",
        "## Full Index",
        "",
        "| Path | Name | Category | Tier | Use when | Source repo | Source branch | Source subdir | Install hint |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for row in rows:
        lines.append(
            f"| `{row['path']}` | `{row['name']}` | {row['category']} | {row['tier']} | {md_cell(row['description'], limit=360)} | "
            f"`{row['repo']}` | `{row['branch']}` | `{row['source_subdir']}` | {row['install']} |"
        )

    return lines


def generate_readme_blocks(rows: list[dict[str, str]], sources: dict[str, dict[str, str | bool]]) -> dict[str, str]:
    """Generate auto-updatable blocks for README.md."""
    blocks: dict[str, str] = {}

    # 1. Custom skills table
    custom_rows = [row for row in rows if row["path"].startswith("custom/")]
    custom_lines = [
        "| 技能 | 说明 |",
        "|------|------|",
    ]
    for row in custom_rows:
        desc = md_cell(row["description"], limit=300)
        custom_lines.append(f"| [{row['name']}]({row['path']}/) | {desc} |")
    blocks["CUSTOM_SKILLS"] = "\n".join(custom_lines)

    # 2. External skill sources table
    skill_sources = {k: v for k, v in sources.items() if v.get("tier") != "reference"}
    external_skill_lines = [
        "| 本地目录 | 源仓库 | 说明 |",
        "|----------|--------|------|",
    ]
    for name, meta in sorted(skill_sources.items()):
        repo = str(meta.get("repo", ""))
        # Extract owner/repo from URL
        repo_link = repo.replace("https://github.com/", "").replace(".git", "")
        tier = str(meta.get("tier", "community"))
        tier_note = ""
        if tier == "bulk":
            tier_note = "（bulk：完整索引见 docs/full-catalog.md）"
        elif tier == "core":
            tier_note = "（core：高质量官方/精选源）"
        # Count skills for this source
        count = len([r for r in rows if r["path"].startswith(f"external/{name}/")])
        desc = f"{count} 个技能{tier_note}"
        external_skill_lines.append(
            f"| `external/{name}/` | [{repo_link}]({repo}) | {desc} |"
        )
    blocks["EXTERNAL_SKILL_SOURCES"] = "\n".join(external_skill_lines)

    # 3. External reference sources table
    ref_sources = {k: v for k, v in sources.items() if v.get("tier") == "reference"}
    ref_lines = [
        "| 本地目录 | 源仓库 | 说明 |",
        "|----------|--------|------|",
    ]
    for name, meta in sorted(ref_sources.items()):
        repo = str(meta.get("repo", ""))
        repo_link = repo.replace("https://github.com/", "").replace(".git", "")
        ref_lines.append(
            f"| `external/{name}/` | [{repo_link}]({repo}) | 设计参考索引 |"
        )
    blocks["EXTERNAL_REFERENCE_SOURCES"] = "\n".join(ref_lines)

    return blocks


def update_readme(blocks: dict[str, str]) -> None:
    """Replace marked sections in README.md with generated blocks."""
    if not README.exists():
        print(f"WARNING: {README} not found, skipping README update.")
        return

    content = read(README)
    updated = content

    for block_name, block_content in blocks.items():
        start_marker = f"<!-- BEGIN GENERATED {block_name} -->"
        end_marker = f"<!-- END GENERATED {block_name} -->"

        if start_marker not in updated or end_marker not in updated:
            print(f"WARNING: README.md markers for {block_name} not found. Skipping.")
            continue

        # Replace content between markers
        pattern = re.compile(
            re.escape(start_marker) + r".*?" + re.escape(end_marker),
            re.DOTALL,
        )
        replacement = f"{start_marker}\n{block_content}\n{end_marker}"
        updated = pattern.sub(replacement, updated)

    if updated != content:
        README.write_text(updated, encoding="utf-8")
        print(f"Updated {README.relative_to(ROOT)} auto-generated blocks.")
    else:
        print(f"No changes needed in {README.relative_to(ROOT)}.")


def generate_skills_index(rows: list[dict[str, str]], sources: dict[str, dict[str, str | bool]]) -> Path:
    """Generate a machine-readable JSON index at docs/skills-index.json."""
    index_path = ROOT / "docs" / "skills-index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    custom_rows = [r for r in rows if r["path"].startswith("custom/")]
    external_rows = [r for r in rows if r["path"].startswith("external/")]

    # Build skills array
    skills = []
    for row in rows:
        if row["path"].startswith("custom/"):
            source_name = "custom"
        else:
            source_name = row["path"].split("/")[1]

        skills.append(
            {
                "path": row["path"],
                "name": row["name"],
                "description": row["description"],
                "category": row["category"],
                "tier": row["tier"],
                "source": source_name,
                "repo": row["repo"],
                "branch": row["branch"],
                "include_in_main": row["include_in_main"],
                "tags": row.get("tags", []),
                "triggers": row.get("triggers", []),
            }
        )

    # Build sources summary
    sources_summary: dict[str, dict[str, object]] = {}
    # External sources from rows
    for source_name in sorted({s["source"] for s in skills if s["source"] != "custom"}):
        source_skills = [s for s in skills if s["source"] == source_name]
        src_config = sources.get(source_name, {})
        sources_summary[source_name] = {
            "repo": str(src_config.get("repo", "")),
            "branch": str(src_config.get("branch", "")),
            "tier": str(src_config.get("tier", "")),
            "skill_count": len(source_skills),
        }
    # Custom source
    sources_summary["custom"] = {
        "repo": "git@github.com:OCDcreator/my-skills.git",
        "branch": "main",
        "tier": "custom",
        "skill_count": len(custom_rows),
    }

    # Build categories count
    categories: dict[str, int] = {}
    for row in rows:
        cat = row["category"]
        categories[cat] = categories.get(cat, 0) + 1
    categories = dict(sorted(categories.items(), key=lambda item: (-item[1], item[0])))

    index = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_skills": len(rows),
            "custom_skills": len(custom_rows),
            "external_skills": len(external_rows),
            "sources_count": len(sources_summary),
        },
        "skills": skills,
        "sources": sources_summary,
        "categories": categories,
    }

    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    return index_path


def main() -> None:
    sources = parse_sources_yaml()
    skill_paths = sorted(
        path.parent.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("SKILL.md")
        if ".git" not in path.parts and ".tmp-skills" not in path.parts
    )

    rows = build_rows(skill_paths, sources)

    # Write curated catalog
    curated_lines = generate_curated_catalog(rows)
    CATALOG.write_text("\n".join(curated_lines) + "\n", encoding="utf-8")
    curated_count = len([r for r in rows if r["include_in_main"] is True or r["path"].startswith("custom/")])
    print(f"Wrote {CATALOG.relative_to(ROOT)} with curated view ({curated_count} skills).")

    # Write full catalog
    FULL_CATALOG.parent.mkdir(parents=True, exist_ok=True)
    full_lines = generate_full_catalog(rows)
    FULL_CATALOG.write_text("\n".join(full_lines) + "\n", encoding="utf-8")
    print(f"Wrote {FULL_CATALOG.relative_to(ROOT)} with full index ({len(rows)} skills).")

    # Update README auto-generated blocks
    readme_blocks = generate_readme_blocks(rows, sources)
    update_readme(readme_blocks)

    # Generate machine-readable index
    index_path = generate_skills_index(rows, sources)
    print(f"Wrote {index_path.relative_to(ROOT)} with {len(rows)} skills.")


if __name__ == "__main__":
    main()
