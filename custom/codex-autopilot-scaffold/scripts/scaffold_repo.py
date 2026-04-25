#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field, replace
from json import JSONDecodeError
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_ROOT = SKILL_ROOT / "templates"
COMMON_TEMPLATES_ROOT = TEMPLATES_ROOT / "common"
PRESET_TEMPLATES_ROOT = TEMPLATES_ROOT / "presets"
SCAFFOLD_NAME = "codex-autopilot-scaffold"
SCAFFOLD_VERSION = "1.1.5"
SCAFFOLD_VERSION_MARKER = Path("automation/autopilot-scaffold-version.json")
SEED_PLAN_DESTINATION = Path("docs/status/autopilot-seed-plan.md")
SEED_SPEC_DESTINATION = Path("docs/status/autopilot-seed-spec.md")

ALLOWED_SOURCE_SUFFIXES = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".py",
    ".rs",
    ".go",
    ".java",
    ".kt",
    ".swift",
}

SKIP_DIRECTORIES = {
    ".git",
    "__pycache__",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "target",
    "vendor",
    ".next",
    ".turbo",
    ".idea",
    ".vscode",
}

COMMON_ROOT_DIRS = ["src", "app", "lib", "pkg", "internal", "cmd", "crates", "server", "client", "tests", "docs"]

PRESET_METADATA: dict[str, dict[str, Any]] = {
    "maintainability": {
        "label": "Maintainability / Refactor",
        "objective": "Reduce ownership concentration and maintainability hotspots one queued slice at a time while keeping configured validation commands green.",
        "focus_hint": "R1 - First maintainability / refactor slice",
        "max_rounds": 200,
    },
    "review-gated": {
        "label": "Review-Gated Delivery",
        "objective": "Execute one queued slice at a time, but gate each round through a written implementation plan review, code review, and full validation before the next unattended round advances.",
        "focus_hint": "RG1 - First review-gated delivery slice",
        "max_rounds": 120,
    },
    "quality-gate": {
        "label": "Quality-Gate Recovery",
        "objective": "Recover configured validation gates to green, close the most justified warning/error hotspots, and keep the gates green while the queue advances.",
        "focus_hint": "Q1 - Recover the first configured gate",
        "max_rounds": 80,
    },
    "bugfix-backlog": {
        "label": "Bugfix / Backlog",
        "objective": "Execute the highest-priority queued bugfix or backlog slice one round at a time, validate it with the configured commands, and avoid unrelated churn.",
        "focus_hint": "B1 - Highest-priority queued bug or backlog slice",
        "max_rounds": 120,
    },
}

PRESET_LANES: dict[str, list[dict[str, str]]] = {
    "review-gated": [
        {
            "id": "rg1-reviewed-slice",
            "label": "RG1 - First review-gated delivery slice",
            "focus_hint": "RG1 - First review-gated delivery slice",
        },
        {
            "id": "rg2-reviewed-followup",
            "label": "RG2 - Next review-gated delivery slice",
            "focus_hint": "RG2 - Next review-gated delivery slice",
        },
        {
            "id": "rg3-reviewed-checkpoint",
            "label": "RG3 - Checkpoint after first review-gated batch",
            "focus_hint": "RG3 - Checkpoint after first review-gated batch",
        },
    ],
    "bugfix-backlog": [
        {
            "id": "b1-backlog-slice",
            "label": "B1 - Highest-priority queued bug or backlog slice",
            "focus_hint": "B1 - Highest-priority queued bug or backlog slice",
        },
        {
            "id": "b2-backlog-slice",
            "label": "B2 - Next queued bug or backlog slice",
            "focus_hint": "B2 - Next queued bug or backlog slice",
        },
        {
            "id": "b3-checkpoint",
            "label": "B3 - Checkpoint after first backlog batch",
            "focus_hint": "B3 - Checkpoint after first backlog batch",
        },
    ],
    "quality-gate": [
        {
            "id": "q1-gate-recovery",
            "label": "Q1 - Recover the first configured gate",
            "focus_hint": "Q1 - Recover the first configured gate",
        },
        {
            "id": "q2-gate-cleanup",
            "label": "Q2 - Finish remaining configured gate cleanup",
            "focus_hint": "Q2 - Finish remaining configured gate cleanup",
        },
        {
            "id": "q3-checkpoint",
            "label": "Q3 - Checkpoint after quality-gate recovery",
            "focus_hint": "Q3 - Checkpoint after quality-gate recovery",
        },
    ],
    "maintainability": [
        {
            "id": "m1-hotspot-slice",
            "label": "R1 - First maintainability / refactor slice",
            "focus_hint": "R1 - First maintainability / refactor slice",
        },
        {
            "id": "m2-followup-slice",
            "label": "R2 - Follow-up maintainability / refactor slice",
            "focus_hint": "R2 - Follow-up maintainability / refactor slice",
        },
        {
            "id": "m3-checkpoint",
            "label": "R3 - Checkpoint after first refactor batch",
            "focus_hint": "R3 - Checkpoint after first refactor batch",
        },
    ],
}


class ScaffoldError(RuntimeError):
    pass


@dataclass
class DetectionResult:
    repo_root: Path
    repo_name: str
    lint_command: str = ""
    typecheck_command: str = ""
    full_test_command: str = ""
    build_command: str = ""
    vulture_command: str = ""
    targeted_test_prefixes: list[str] = field(default_factory=list)
    command_sources: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    root_dirs: list[str] = field(default_factory=list)
    source_entrypoints: list[str] = field(default_factory=list)
    test_entrypoints: list[str] = field(default_factory=list)


@dataclass
class ExistingScaffoldState:
    version: str = ""
    has_existing_scaffold: bool = False
    needs_auto_upgrade: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SeedArtifact:
    kind: str
    source_path: Path
    destination_path: Path
    repo_relative_path: str
    content: str


def clean_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_repo_path(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def run_git(repo_root: Path, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and process.returncode != 0:
        combined = "\n".join(part for part in (process.stdout, process.stderr) if part.strip())
        raise ScaffoldError(f"git {' '.join(args)} failed: {combined}")
    return process


def resolve_git_root(target_repo: Path) -> Path:
    process = subprocess.run(
        ["git", "-C", str(target_repo), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if process.returncode != 0:
        combined = "\n".join(part for part in (process.stdout, process.stderr) if part.strip())
        raise ScaffoldError(
            "Target path is not inside a Git repository. Initialize Git first or choose a repo root.\n" + combined
        )
    return Path(process.stdout.strip()).resolve()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def package_declares_dependencies(repo_root: Path) -> bool:
    package_json = repo_root / "package.json"
    if not package_json.exists():
        return False
    package = json.loads(read_text(package_json))
    for key in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
        "bundledDependencies",
    ):
        value = package.get(key)
        if isinstance(value, dict) and value:
            return True
        if isinstance(value, list) and value:
            return True
    return False


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def parse_semver(version_text: str) -> tuple[int, int, int]:
    normalized = clean_string(version_text)
    if not normalized:
        return (0, 0, 0)
    if not re.fullmatch(r"\d+(?:\.\d+){0,2}", normalized):
        raise ScaffoldError(f"Unsupported scaffold version format: {version_text}")
    parts = [int(part) for part in normalized.split(".")]
    while len(parts) < 3:
        parts.append(0)
    return (parts[0], parts[1], parts[2])


def compare_semver(left: str, right: str) -> int:
    left_parts = parse_semver(left)
    right_parts = parse_semver(right)
    if left_parts < right_parts:
        return -1
    if left_parts > right_parts:
        return 1
    return 0


def detect_existing_scaffold_state(repo_root: Path, *, auto_upgrade_enabled: bool) -> ExistingScaffoldState:
    version_marker_path = repo_root / SCAFFOLD_VERSION_MARKER
    autopilot_path = repo_root / "automation" / "autopilot.py"
    warnings: list[str] = []

    if not version_marker_path.exists():
        if autopilot_path.exists():
            warnings.append(
                "Existing autopilot scaffold has no version marker; treating it as scaffold_version=0.0.0 for auto-upgrade."
            )
            return ExistingScaffoldState(
                version="0.0.0",
                has_existing_scaffold=True,
                needs_auto_upgrade=auto_upgrade_enabled,
                warnings=warnings,
            )
        return ExistingScaffoldState()

    try:
        payload = json.loads(read_text(version_marker_path))
    except JSONDecodeError:
        warnings.append(
            "Existing autopilot scaffold version marker is unreadable; treating it as scaffold_version=0.0.0 for auto-upgrade."
        )
        return ExistingScaffoldState(
            version="0.0.0",
            has_existing_scaffold=True,
            needs_auto_upgrade=auto_upgrade_enabled,
            warnings=warnings,
        )

    version_text = clean_string(payload.get("scaffold_version"))
    if not version_text:
        warnings.append(
            "Existing autopilot scaffold version marker is missing scaffold_version; treating it as scaffold_version=0.0.0 for auto-upgrade."
        )
        version_text = "0.0.0"

    if compare_semver(version_text, SCAFFOLD_VERSION) > 0:
        raise ScaffoldError(
            f"Target repo already has scaffold version {version_text}, which is newer than this skill's {SCAFFOLD_VERSION}. "
            "Refusing automatic downgrade; use --force only if you really want to replace it."
        )

    return ExistingScaffoldState(
        version=version_text,
        has_existing_scaffold=True,
        needs_auto_upgrade=auto_upgrade_enabled and compare_semver(version_text, SCAFFOLD_VERSION) < 0,
        warnings=warnings,
    )


def render_tokens(template_text: str, tokens: dict[str, str]) -> str:
    rendered = template_text
    for token_name, token_value in tokens.items():
        rendered = rendered.replace(f"[[{token_name}]]", token_value)
    return rendered


def json_token(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def resolve_seed_artifact(repo_root: Path, args: argparse.Namespace) -> SeedArtifact | None:
    seed_plan = clean_string(getattr(args, "seed_plan", ""))
    seed_spec = clean_string(getattr(args, "seed_spec", ""))
    if seed_plan and seed_spec:
        raise ScaffoldError("Use either --seed-plan or --seed-spec, not both.")
    if not seed_plan and not seed_spec:
        return None

    kind = "plan" if seed_plan else "spec"
    source_path = Path(seed_plan or seed_spec).expanduser().resolve()
    if not source_path.exists() or not source_path.is_file():
        raise ScaffoldError(f"Seed {kind} file not found: {source_path}")

    destination_path = SEED_PLAN_DESTINATION if kind == "plan" else SEED_SPEC_DESTINATION
    return SeedArtifact(
        kind=kind,
        source_path=source_path,
        destination_path=destination_path,
        repo_relative_path=destination_path.as_posix(),
        content=read_text(source_path),
    )


def build_seeded_queue_override(seed: SeedArtifact) -> str:
    return f"""## Seeded Queue Override

### [NEXT] Execute the next approved {seed.kind} slice

- **Seed source**: `{seed.repo_relative_path}`
- **Queue authority**: follow the approved seed {seed.kind} before generic preset backlog text.
- **Scope rule**: choose the first unchecked, numbered, or clearly next actionable item from the seed and execute exactly that slice.
- **Completion rule**: update this roadmap and the seed progress notes so the next round can identify the next seed slice without re-planning.
- **Do not** replace the seed with a broader backlog unless the seed is complete.
"""


def write_seed_artifact(repo_root: Path, seed: SeedArtifact, *, force: bool) -> str:
    header = (
        f"# Autopilot Seed {seed.kind.title()}\n\n"
        f"> Copied from: `{seed.source_path}`\n"
        f"> Scaffold version: `{SCAFFOLD_VERSION}`\n\n"
        "This file is the approved execution source for seeded unattended rounds. Keep progress notes here or in lane roadmaps.\n\n"
        "---\n\n"
    )
    return write_if_changed(repo_root / seed.destination_path, header + seed.content.rstrip() + "\n", force=force, on_conflict="overwrite")


def apply_seed_to_generated_docs(repo_root: Path, seed: SeedArtifact, *, force: bool) -> dict[str, str]:
    results: dict[str, str] = {}
    results[seed.repo_relative_path] = write_seed_artifact(repo_root, seed, force=force)

    master_plan_path = repo_root / "docs" / "status" / "autopilot-master-plan.md"
    if master_plan_path.exists():
        marker = "<!-- autopilot-seed-source -->"
        master_text = read_text(master_plan_path)
        seed_section = (
            f"\n## Seeded Execution Source\n\n"
            f"{marker}\n"
            f"- Seed {seed.kind}: `{seed.repo_relative_path}`\n"
            "- Treat the seed as the approved implementation source before generic preset language.\n"
            "- Keep unattended rounds bounded to one seed slice at a time.\n"
        )
        if marker not in master_text:
            results[normalize_repo_path(master_plan_path, repo_root)] = write_if_changed(
                master_plan_path,
                master_text.rstrip() + seed_section + "\n",
                force=force,
                on_conflict="overwrite",
            )

    seeded_override = build_seeded_queue_override(seed)
    for roadmap_path in sorted((repo_root / "docs" / "status" / "lanes").glob("*/autopilot-round-roadmap.md")):
        roadmap_text = read_text(roadmap_path)
        if "## Seeded Queue Override" in roadmap_text:
            continue
        lines = roadmap_text.splitlines()
        insert_at = 1 if lines and lines[0].startswith("# ") else 0
        next_text = "\n".join([*lines[:insert_at], "", seeded_override.rstrip(), "", *lines[insert_at:]]) + "\n"
        results[normalize_repo_path(roadmap_path, repo_root)] = write_if_changed(
            roadmap_path,
            next_text,
            force=force,
            on_conflict="overwrite",
        )

    return results


def build_preset_lanes(preset: str) -> list[dict[str, str]]:
    lanes: list[dict[str, str]] = []
    for lane in PRESET_LANES[preset]:
        lane_id = lane["id"]
        lane_root = f"docs/status/lanes/{lane_id}"
        lanes.append(
            {
                **lane,
                "phase_doc_prefix": f"{lane_root}/autopilot-phase-",
                "starting_phase_doc": f"{lane_root}/autopilot-phase-0.md",
                "roadmap_path": f"{lane_root}/autopilot-round-roadmap.md",
                "prompt_template": "automation/round-prompt.md",
                "commit_prefix": "autopilot",
            }
        )
    return lanes


def first_non_empty(options: list[tuple[str, str]]) -> tuple[str, str]:
    for value, source in options:
        if clean_string(value):
            return value, source
    return "", ""


def discover_make_targets(path: Path) -> set[str]:
    if not path.exists():
        return set()
    targets: set[str] = set()
    for line in read_text(path).splitlines():
        if line.startswith("\t") or line.startswith(" "):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*:", line)
        if match:
            targets.add(match.group(1))
    return targets


def discover_just_targets(path: Path) -> set[str]:
    if not path.exists():
        return set()
    targets: set[str] = set()
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*:", stripped)
        if match:
            targets.add(match.group(1))
    return targets


def path_has_token(path: Path, token: str) -> bool:
    return token in read_text(path)


def package_script_command(scripts: dict[str, Any], script_name: str) -> str:
    if script_name in scripts:
        return f"npm run {script_name}"
    return ""


def discover_vulture_from_requirements(repo_root: Path) -> tuple[str, str]:
    requirement_files = [
        repo_root / "requirements.txt",
        repo_root / "requirements-dev.txt",
        repo_root / "dev-requirements.txt",
    ]
    for path in requirement_files:
        if not path.exists():
            continue
        raw_text = read_text(path)
        if re.search(r"(?im)^\s*vulture(?:[<>=~! ]|$)", raw_text):
            return "python -m vulture .", path.name
    return "", ""


def detect_commands(repo_root: Path) -> DetectionResult:
    result = DetectionResult(repo_root=repo_root, repo_name=repo_root.name)

    package_json = repo_root / "package.json"
    if package_json.exists():
        try:
            package = json.loads(read_text(package_json))
        except json.JSONDecodeError as exc:
            raise ScaffoldError(f"Could not parse {package_json}: {exc}") from exc
        scripts = package.get("scripts") or {}
        if isinstance(scripts, dict):
            value, source = first_non_empty(
                [
                    ("npm run lint" if "lint" in scripts else "", "package.json:scripts.lint"),
                    ("npm run eslint" if "eslint" in scripts else "", "package.json:scripts.eslint"),
                ]
            )
            result.lint_command = value
            if source:
                result.command_sources["lint_command"] = source

            value, source = first_non_empty(
                [
                    ("npm run typecheck" if "typecheck" in scripts else "", "package.json:scripts.typecheck"),
                    ("npm run check-types" if "check-types" in scripts else "", "package.json:scripts.check-types"),
                    ("npm run tsc" if "tsc" in scripts else "", "package.json:scripts.tsc"),
                ]
            )
            result.typecheck_command = value
            if source:
                result.command_sources["typecheck_command"] = source

            if "test" in scripts:
                result.full_test_command = "npm test"
                result.command_sources["full_test_command"] = "package.json:scripts.test"
                result.targeted_test_prefixes = ["npm test --", "npm run test --"]

            value, source = first_non_empty(
                [
                    ("npm run build" if "build" in scripts else "", "package.json:scripts.build"),
                    ("npm run compile" if "compile" in scripts else "", "package.json:scripts.compile"),
                ]
            )
            result.build_command = value
            if source:
                result.command_sources["build_command"] = source

            value, source = first_non_empty(
                [
                    (package_script_command(scripts, "vulture"), "package.json:scripts.vulture"),
                    (package_script_command(scripts, "deadcode"), "package.json:scripts.deadcode"),
                ]
            )
            result.vulture_command = value
            if source:
                result.command_sources["vulture_command"] = source

    pyproject_toml = repo_root / "pyproject.toml"
    if pyproject_toml.exists():
        raw_text = read_text(pyproject_toml)
        pyproject = tomllib.loads(raw_text)
        tool = pyproject.get("tool") if isinstance(pyproject, dict) else {}

        if not result.lint_command and ("ruff" in raw_text or isinstance(tool, dict) and "ruff" in tool):
            result.lint_command = "ruff check ."
            result.command_sources["lint_command"] = "pyproject.toml:tool.ruff"

        if not result.typecheck_command and ("mypy" in raw_text or isinstance(tool, dict) and "mypy" in tool):
            result.typecheck_command = "python -m mypy ."
            result.command_sources["typecheck_command"] = "pyproject.toml:tool.mypy"

        if not result.full_test_command and ("pytest" in raw_text or (repo_root / "tests").exists()):
            result.full_test_command = "pytest"
            result.command_sources["full_test_command"] = "pyproject.toml / tests/"
            result.targeted_test_prefixes = ["pytest ", "python -m pytest "]

        if not result.vulture_command and ("vulture" in raw_text or isinstance(tool, dict) and "vulture" in tool):
            result.vulture_command = "python -m vulture ."
            result.command_sources["vulture_command"] = "pyproject.toml:tool.vulture"

    if not result.vulture_command:
        value, source = discover_vulture_from_requirements(repo_root)
        result.vulture_command = value
        if source:
            result.command_sources["vulture_command"] = source

    cargo_toml = repo_root / "Cargo.toml"
    if cargo_toml.exists():
        if not result.lint_command:
            result.lint_command = "cargo clippy --all-targets --all-features -- -D warnings"
            result.command_sources["lint_command"] = "Cargo.toml"
        if not result.typecheck_command:
            result.typecheck_command = "cargo check"
            result.command_sources["typecheck_command"] = "Cargo.toml"
        if not result.full_test_command:
            result.full_test_command = "cargo test"
            result.command_sources["full_test_command"] = "Cargo.toml"
            result.targeted_test_prefixes = ["cargo test "]
        if not result.build_command:
            result.build_command = "cargo build"
            result.command_sources["build_command"] = "Cargo.toml"

    go_mod = repo_root / "go.mod"
    if go_mod.exists():
        if not result.full_test_command:
            result.full_test_command = "go test ./..."
            result.command_sources["full_test_command"] = "go.mod"
            result.targeted_test_prefixes = ["go test "]
        if not result.build_command:
            result.build_command = "go build ./..."
            result.command_sources["build_command"] = "go.mod"

    make_targets = discover_make_targets(repo_root / "Makefile")
    if make_targets:
        if not result.lint_command and "lint" in make_targets:
            result.lint_command = "make lint"
            result.command_sources["lint_command"] = "Makefile:lint"
        if not result.typecheck_command and "typecheck" in make_targets:
            result.typecheck_command = "make typecheck"
            result.command_sources["typecheck_command"] = "Makefile:typecheck"
        if not result.full_test_command and "test" in make_targets:
            result.full_test_command = "make test"
            result.command_sources["full_test_command"] = "Makefile:test"
        if not result.build_command and "build" in make_targets:
            result.build_command = "make build"
            result.command_sources["build_command"] = "Makefile:build"

    just_targets = discover_just_targets(repo_root / "justfile")
    if just_targets:
        if not result.lint_command and "lint" in just_targets:
            result.lint_command = "just lint"
            result.command_sources["lint_command"] = "justfile:lint"
        if not result.typecheck_command and "typecheck" in just_targets:
            result.typecheck_command = "just typecheck"
            result.command_sources["typecheck_command"] = "justfile:typecheck"
        if not result.full_test_command and "test" in just_targets:
            result.full_test_command = "just test"
            result.command_sources["full_test_command"] = "justfile:test"
        if not result.build_command and "build" in just_targets:
            result.build_command = "just build"
            result.command_sources["build_command"] = "justfile:build"

    root_dirs = []
    for name in COMMON_ROOT_DIRS:
        path = repo_root / name
        if path.exists():
            root_dirs.append(f"{name}/" if path.is_dir() else name)
    result.root_dirs = root_dirs

    source_candidates: list[tuple[int, str]] = []
    test_candidates: list[tuple[int, str]] = []
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(repo_root).parts
        relative_path = "/".join(relative_parts)
        if any(part in SKIP_DIRECTORIES for part in relative_parts):
            continue
        if relative_path.startswith("automation/runtime/"):
            continue
        if path.suffix.lower() not in ALLOWED_SOURCE_SUFFIXES:
            continue
        try:
            line_count = len(read_text(path).splitlines())
        except UnicodeDecodeError:
            continue
        rel_path = normalize_repo_path(path, repo_root)
        bucket = test_candidates if any(part == "tests" for part in relative_parts) else source_candidates
        bucket.append((line_count, rel_path))

    source_candidates.sort(reverse=True)
    test_candidates.sort(reverse=True)
    result.source_entrypoints = [path for _, path in source_candidates[:5]]
    result.test_entrypoints = [path for _, path in test_candidates[:3]]

    if not any([result.lint_command, result.typecheck_command, result.full_test_command, result.build_command]):
        result.warnings.append(
            "No standard lint/typecheck/test/build commands were inferred. Re-run with explicit --*-command overrides."
        )

    return result


def build_path_list(repo_root: Path, detection: DetectionResult) -> list[str]:
    paths: list[str] = []
    for root_dir in detection.root_dirs:
        paths.append(root_dir)
    for manifest in ["package.json", "package-lock.json", "pyproject.toml", "Cargo.toml", "go.mod", "Makefile", "justfile"]:
        if (repo_root / manifest).exists():
            paths.append(manifest)
    return paths


def markdown_bullets(items: list[str]) -> str:
    if not items:
        return "- `README.md`"
    return "\n".join(f"- `{item}`" for item in items)


def build_entrypoints(detection: DetectionResult, preset: str) -> list[str]:
    items: list[str] = []
    for candidate in ["AGENTS.md", "README.md", "docs/"]:
        candidate_path = detection.repo_root / candidate
        if candidate_path.exists():
            items.append(candidate if not candidate.endswith("/") else candidate)

    items.extend(detection.root_dirs[:4])

    if preset == "quality-gate":
        items.extend(detection.test_entrypoints[:2])
        items.extend(detection.source_entrypoints[:3])
    elif preset == "bugfix-backlog":
        items.extend(detection.source_entrypoints[:3])
        items.extend(detection.test_entrypoints[:1])
    else:
        items.extend(detection.source_entrypoints[:5])

    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = item.rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(item)
    return deduped[:8]


def build_validation_bullets(detection: DetectionResult) -> str:
    rows = [
        ("Lint", detection.lint_command, detection.command_sources.get("lint_command", "not inferred")),
        ("Typecheck", detection.typecheck_command, detection.command_sources.get("typecheck_command", "not inferred")),
        ("Full test", detection.full_test_command, detection.command_sources.get("full_test_command", "not inferred")),
        ("Build", detection.build_command, detection.command_sources.get("build_command", "not inferred")),
        ("Vulture", detection.vulture_command, detection.command_sources.get("vulture_command", "not inferred")),
    ]
    lines = []
    for label, command, source in rows:
        if command:
            lines.append(f"- {label}: `{command}` (source: `{source}`)")
        else:
            lines.append(f"- {label}: not inferred")
    return "\n".join(lines)


def build_review_command_paths(preset: str) -> list[str]:
    if preset != "review-gated":
        return []
    return [
        "automation/opencode-review.sh",
        "automation/Invoke-OpencodeReview.ps1",
        ".opencode/commands/review-plan.md",
        ".opencode/commands/review-code.md",
    ]


def build_prerequisite_paths(repo_root: Path, preset: str) -> list[str]:
    paths: list[str] = []
    if package_declares_dependencies(repo_root):
        paths.append("node_modules")
    paths.extend(build_review_command_paths(preset))
    deduped: list[str] = []
    seen: set[str] = set()
    for path in paths:
        normalized = path.replace("\\", "/").rstrip("/")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def apply_cli_overrides(detection: DetectionResult, args: argparse.Namespace) -> DetectionResult:
    updated = replace(
        detection,
        command_sources=dict(detection.command_sources),
        warnings=list(detection.warnings),
        targeted_test_prefixes=list(detection.targeted_test_prefixes),
    )

    command_flags = {
        "lint_command": "lint_command",
        "typecheck_command": "typecheck_command",
        "full_test_command": "full_test_command",
        "build_command": "build_command",
        "vulture_command": "vulture_command",
    }
    for arg_name, field_name in command_flags.items():
        value = clean_string(getattr(args, arg_name))
        if not value:
            continue
        setattr(updated, field_name, value)
        updated.command_sources[field_name] = "CLI override"

    if any([updated.lint_command, updated.typecheck_command, updated.full_test_command, updated.build_command]):
        updated.warnings = [
            warning
            for warning in updated.warnings
            if "No standard lint/typecheck/test/build commands were inferred" not in warning
        ]

    return updated


def write_if_changed(path: Path, content: str, *, force: bool, on_conflict: str = "error") -> str:
    if path.exists():
        existing = read_text(path)
        if existing == content:
            return "unchanged"
        if not force and on_conflict == "preserve":
            return "preserved"
        if not force and on_conflict != "overwrite":
            raise ScaffoldError(f"Refusing to overwrite existing file without --force: {path}")
    write_text(path, content)
    return "written"


def sync_executable_mode(source_path: Path, destination_path: Path) -> None:
    if source_path.suffix.lower() != ".sh" and not (source_path.stat().st_mode & 0o111):
        return
    current_mode = destination_path.stat().st_mode
    destination_path.chmod(current_mode | 0o755)


def render_template_tree(
    source_root: Path,
    destination_root: Path,
    tokens: dict[str, str],
    *,
    force: bool,
    on_conflict: str = "error",
) -> dict[str, str]:
    results: dict[str, str] = {}
    for source_path in sorted(source_root.rglob("*")):
        if not source_path.is_file():
            continue
        if "__pycache__" in source_path.parts or source_path.suffix == ".pyc":
            continue
        relative_path = source_path.relative_to(source_root)
        destination_path = destination_root / relative_path
        rendered = render_tokens(read_text(source_path), tokens)
        status = write_if_changed(destination_path, rendered, force=force, on_conflict=on_conflict)
        results[normalize_repo_path(destination_path, destination_root)] = status
        if status == "written":
            sync_executable_mode(source_path, destination_path)
    return results


def render_preset_templates(
    preset_root: Path,
    destination_root: Path,
    tokens: dict[str, str],
    *,
    force: bool,
    auto_upgrade: bool,
) -> dict[str, str]:
    if not auto_upgrade:
        return render_template_tree(
            preset_root,
            destination_root,
            tokens,
            force=force,
            on_conflict="error",
        )

    result_maps: list[dict[str, str]] = []
    for source_path in sorted(preset_root.iterdir(), key=lambda path: path.name):
        if source_path.name == "__pycache__":
            continue
        destination_path = destination_root / source_path.name
        if source_path.is_dir():
            on_conflict = "preserve" if source_path.name == "docs" else "overwrite"
            result_maps.append(
                render_template_tree(
                    source_path,
                    destination_path,
                    tokens,
                    force=force,
                    on_conflict=on_conflict,
                )
            )
            continue

        rendered = render_tokens(read_text(source_path), tokens)
        on_conflict = "overwrite"
        status = write_if_changed(destination_path, rendered, force=force, on_conflict=on_conflict)
        result_maps.append({normalize_repo_path(destination_path, destination_root): status})
    return merge_render_results(*result_maps)


def merge_render_results(*result_maps: dict[str, str]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for result_map in result_maps:
        merged.update(result_map)
    return merged


def ensure_gitignore_entries(repo_root: Path, entries: list[str], *, force: bool) -> str:
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.exists():
        write_text(gitignore_path, "\n".join(entries) + "\n")
        return "written"

    existing = read_text(gitignore_path)
    lines = existing.splitlines()
    missing_entries = [entry for entry in entries if not any(line.strip() == entry for line in lines)]
    if not missing_entries:
        return "unchanged"

    suffix = "" if existing.endswith("\n") or not existing else "\n"
    new_content = existing + suffix + "\n".join(missing_entries) + "\n"
    write_text(gitignore_path, new_content)
    return "written"


def default_tokens(detection: DetectionResult, preset: str) -> dict[str, str]:
    metadata = PRESET_METADATA[preset]
    lanes = build_preset_lanes(preset)
    path_list = build_path_list(detection.repo_root, detection)
    entrypoints = build_entrypoints(detection, preset)
    prerequisite_paths = build_prerequisite_paths(detection.repo_root, preset)
    review_enabled = preset == "review-gated"

    lint_command = detection.lint_command
    typecheck_command = detection.typecheck_command
    full_test_command = detection.full_test_command
    build_command = detection.build_command
    vulture_command = detection.vulture_command

    validation_commands = [command for command in [lint_command, typecheck_command, full_test_command, build_command] if command]
    validation_requirement = "Run every configured validation command below on successful rounds." if validation_commands else "No validation command was inferred; do not guess. Add explicit commands before running unattended rounds."

    tokens = {
        "PRESET_LABEL": metadata["label"],
        "OBJECTIVE": metadata["objective"],
        "OBJECTIVE_JSON": json.dumps(metadata["objective"], ensure_ascii=False),
        "FOCUS_HINT": metadata["focus_hint"],
        "FOCUS_HINT_JSON": json.dumps(metadata["focus_hint"], ensure_ascii=False),
        "REPO_NAME": detection.repo_name,
        "ENTRYPOINT_BULLETS": markdown_bullets(entrypoints),
        "VALIDATION_BULLETS": build_validation_bullets(detection),
        "VALIDATION_REQUIREMENT": validation_requirement,
        "LINT_COMMAND": lint_command,
        "LINT_COMMAND_JSON": json.dumps(lint_command, ensure_ascii=False),
        "TYPECHECK_COMMAND": typecheck_command,
        "TYPECHECK_COMMAND_JSON": json.dumps(typecheck_command, ensure_ascii=False),
        "FULL_TEST_COMMAND": full_test_command,
        "FULL_TEST_COMMAND_JSON": json.dumps(full_test_command, ensure_ascii=False),
        "BUILD_COMMAND": build_command,
        "BUILD_COMMAND_JSON": json.dumps(build_command, ensure_ascii=False),
        "VULTURE_COMMAND": vulture_command,
        "VULTURE_COMMAND_JSON": json.dumps(vulture_command, ensure_ascii=False),
        "TARGETED_TEST_REQUIRED_JSON": "true" if bool(detection.targeted_test_prefixes) else "false",
        "TARGETED_TEST_PREFIXES_JSON": json_token(detection.targeted_test_prefixes),
        "TARGETED_TEST_REQUIRED_PATHS_JSON": json_token(path_list),
        "FULL_TEST_REQUIRED_PATHS_JSON": json_token(path_list),
        "BUILD_REQUIRED_PATHS_JSON": json_token(path_list),
        "FULL_TEST_CADENCE_ROUNDS": "1" if full_test_command else "0",
        "MAX_ROUNDS": str(metadata["max_rounds"]),
        "MAX_CONSECUTIVE_FAILURES": "3",
        "ALLOWED_BRANCH_PREFIXES_JSON": json_token(["autopilot/", "automation/", "quality/", "bugfix/"]),
        "COMMIT_PREFIX_JSON": json.dumps("autopilot", ensure_ascii=False),
        "LANES_JSON": json_token(lanes),
        "NEXT_PHASE_NUMBER": "1",
        "PROMPT_TEMPLATE_JSON": json.dumps("automation/round-prompt.md", ensure_ascii=False),
        "RESULT_SCHEMA_JSON": json.dumps("automation/round-result.schema.json", ensure_ascii=False),
        "DEPLOY_AFTER_BUILD_JSON": "false",
        "DEPLOY_POLICY_JSON": json.dumps("never", ensure_ascii=False),
        "DEPLOY_REQUIRED_PATHS_JSON": "[]",
        "DEPLOY_VERIFY_PATH_JSON": json.dumps("", ensure_ascii=False),
        "COMMAND_BUDGET_POLICY_JSON": json.dumps("warn", ensure_ascii=False),
        "RUNNER_KIND_JSON": json.dumps("codex", ensure_ascii=False),
        "RUNNER_COMMAND_JSON": json.dumps("", ensure_ascii=False),
        "RUNNER_MODEL_JSON": json.dumps("", ensure_ascii=False),
        "RUNNER_EXTRA_ARGS_JSON": "[]",
        "RUNNER_ADDITIONAL_DIRS_JSON": "[]",
        "BUILD_VERIFY_PATH_JSON": json.dumps("", ensure_ascii=False),
        "PLAN_REVIEW_COMMAND_JSON": json.dumps(
            "Use Invoke-OpencodeReview.ps1 on Windows or opencode-review.sh on macOS/Linux for plan review.",
            ensure_ascii=False,
        )
        if review_enabled
        else json.dumps("", ensure_ascii=False),
        "CODE_REVIEW_COMMAND_JSON": json.dumps(
            "Use Invoke-OpencodeReview.ps1 on Windows or opencode-review.sh on macOS/Linux for code review.",
            ensure_ascii=False,
        )
        if review_enabled
        else json.dumps("", ensure_ascii=False),
        "REVIEW_POLL_SECONDS_JSON": "60" if review_enabled else "0",
        "REVIEW_TIMEOUT_SECONDS_JSON": "1800" if review_enabled else "0",
        "PREREQUISITE_PATHS_JSON": json_token(prerequisite_paths),
        "SCAFFOLD_NAME_JSON": json.dumps(SCAFFOLD_NAME, ensure_ascii=False),
        "SCAFFOLD_VERSION_JSON": json.dumps(SCAFFOLD_VERSION, ensure_ascii=False),
    }
    return tokens


def normalize_cli_path_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    paths: list[str] = []
    for value in values:
        for part in str(value).split(","):
            normalized = part.strip().replace("\\", "/")
            if normalized:
                paths.append(normalized)
    return paths


def override_tokens(tokens: dict[str, str], args: argparse.Namespace) -> dict[str, str]:
    overrides = dict(tokens)

    if clean_string(args.objective):
        overrides["OBJECTIVE"] = clean_string(args.objective)
        overrides["OBJECTIVE_JSON"] = json.dumps(clean_string(args.objective), ensure_ascii=False)

    command_flags = {
        "lint_command": "LINT_COMMAND",
        "typecheck_command": "TYPECHECK_COMMAND",
        "full_test_command": "FULL_TEST_COMMAND",
        "build_command": "BUILD_COMMAND",
        "vulture_command": "VULTURE_COMMAND",
    }
    for arg_name, token_name in command_flags.items():
        value = clean_string(getattr(args, arg_name))
        if value:
            overrides[token_name] = value
            overrides[f"{token_name}_JSON"] = json.dumps(value, ensure_ascii=False)

    if clean_string(args.runner_model):
        overrides["RUNNER_MODEL_JSON"] = json.dumps(clean_string(args.runner_model), ensure_ascii=False)

    deploy_policy = clean_string(args.deploy_policy).lower()
    if deploy_policy:
        overrides["DEPLOY_POLICY_JSON"] = json.dumps(deploy_policy, ensure_ascii=False)
        overrides["DEPLOY_AFTER_BUILD_JSON"] = "true" if deploy_policy == "always" else "false"

    deploy_verify_path = clean_string(args.deploy_verify_path)
    if deploy_verify_path:
        overrides["DEPLOY_VERIFY_PATH_JSON"] = json.dumps(deploy_verify_path, ensure_ascii=False)
        overrides["BUILD_VERIFY_PATH_JSON"] = json.dumps(deploy_verify_path, ensure_ascii=False)

    deploy_required_paths = normalize_cli_path_list(args.deploy_required_paths)
    if deploy_required_paths:
        overrides["DEPLOY_REQUIRED_PATHS_JSON"] = json_token(deploy_required_paths)

    return overrides


def scaffold_repo(args: argparse.Namespace) -> int:
    target_repo = Path(args.target_repo).expanduser().resolve()
    repo_root = resolve_git_root(target_repo)
    detection = apply_cli_overrides(detect_commands(repo_root), args)
    tokens = override_tokens(default_tokens(detection, args.preset), args)
    existing_scaffold = detect_existing_scaffold_state(repo_root, auto_upgrade_enabled=not args.no_auto_upgrade)
    detection.warnings.extend(existing_scaffold.warnings)
    seed_artifact = resolve_seed_artifact(repo_root, args)

    common_root = COMMON_TEMPLATES_ROOT
    preset_root = PRESET_TEMPLATES_ROOT / args.preset
    if not preset_root.exists():
        raise ScaffoldError(f"Preset template directory not found: {preset_root}")

    common_conflict_policy = "overwrite" if existing_scaffold.needs_auto_upgrade else "error"
    common_results = render_template_tree(
        common_root,
        repo_root,
        tokens,
        force=args.force,
        on_conflict=common_conflict_policy,
    )
    preset_results = render_preset_templates(
        preset_root,
        repo_root,
        tokens,
        force=args.force,
        auto_upgrade=existing_scaffold.needs_auto_upgrade,
    )
    gitignore_entries = [
        "automation/runtime/",
        "automation/**/__pycache__/",
        "automation/**/*.pyc",
    ]
    if args.preset == "review-gated":
        gitignore_entries.extend(
            [
                "!.opencode/",
                "!.opencode/commands/",
                "!.opencode/commands/review-plan.md",
                "!.opencode/commands/review-code.md",
            ]
        )
    seed_results = apply_seed_to_generated_docs(repo_root, seed_artifact, force=args.force) if seed_artifact else {}
    gitignore_result = ensure_gitignore_entries(
        repo_root,
        gitignore_entries,
        force=args.force,
    )

    print(f"[scaffold] target repo: {repo_root}")
    print(f"[scaffold] preset: {args.preset} ({PRESET_METADATA[args.preset]['label']})")
    print(f"[scaffold] scaffold version: {SCAFFOLD_VERSION}")
    print(f"[scaffold] scaffold source: {SKILL_ROOT}")
    if seed_artifact:
        print(f"[scaffold] seeded {seed_artifact.kind}: {seed_artifact.source_path} -> {seed_artifact.repo_relative_path}")
    if existing_scaffold.needs_auto_upgrade:
        print(
            "[scaffold] auto-upgrade: "
            f"detected scaffold_version={existing_scaffold.version}; refreshed common assets plus preset automation files, and preserved existing queue docs."
        )
    print("[scaffold] inferred validation commands:")
    print(build_validation_bullets(detection))
    for warning in detection.warnings:
        print(f"[scaffold] warning: {warning}")

    current_branch = run_git(repo_root, ["branch", "--show-current"], check=False).stdout.strip()
    allowed_prefixes = ["autopilot/", "automation/", "quality/", "bugfix/"]
    if current_branch and not any(current_branch.startswith(prefix) for prefix in allowed_prefixes):
        print(
            "[scaffold] warning: current branch "
            f"'{current_branch}' does not match autopilot branch prefixes. Create a dedicated worktree/branch before doctor/start."
        )

    written_count = sum(
        1
        for status in [*common_results.values(), *preset_results.values(), *seed_results.values(), gitignore_result]
        if status == "written"
    )
    unchanged_count = sum(
        1
        for status in [*common_results.values(), *preset_results.values(), *seed_results.values(), gitignore_result]
        if status == "unchanged"
    )
    print(f"[scaffold] files written: {written_count}, unchanged: {unchanged_count}")

    if args.print_next_steps:
        print("[scaffold] next commands:")
        print("  # 1) Commit scaffold, then create/switch to a dedicated autopilot branch or worktree.")
        print("  git switch -c autopilot/<topic>")
        print("  # 2) If the operator asked for continuous unattended work, do not stop after printing commands.")
        print("  #    Launch a durable runner, then verify health on the exact state file before reporting success.")
        print("  python automation/autopilot.py version")
        print("  python automation/autopilot.py doctor --profile windows")
        print("  python automation/autopilot.py health --state-path automation/runtime/autopilot-state.json")
        print("  python automation/autopilot.py start --profile windows --dry-run --single-round")
        print("  python automation/autopilot.py bootstrap-and-daemonize --profile windows")
        print("  # Verify immediately after daemonizing.")
        print("  python automation/autopilot.py health --state-path automation/runtime/autopilot-state.json")
        print(
            "  python automation/autopilot.py watch --runtime-path automation/runtime --state-path automation/runtime/autopilot-state.json --tail 80 --prefix-format short"
        )
        print("  python3 ./automation/autopilot.py doctor --profile mac")
        print("  python3 ./automation/autopilot.py health --state-path automation/runtime/autopilot-state.json")
        print("  python3 ./automation/autopilot.py start --profile mac --dry-run --single-round")
        print("  python3 ./automation/autopilot.py bootstrap-and-daemonize --profile mac")
        print("  # Verify immediately after daemonizing.")
        print("  python3 ./automation/autopilot.py health --state-path automation/runtime/autopilot-state.json")
        print(
            "  python3 ./automation/autopilot.py watch --runtime-path automation/runtime --state-path automation/runtime/autopilot-state.json --tail 80 --prefix-format short"
        )
        print("  bash ./automation/start-autopilot.sh -- --profile mac --dry-run --single-round")
        print("[scaffold] remote mac rollout template:")
        print("  git push")
        print("  ssh mac 'cd /Volumes/SDD2T/obsidian-vault-write/custom-project/<repo> && git fetch --all --prune'")
        print("  ssh mac 'cd /Volumes/SDD2T/obsidian-vault-write/custom-project/<repo> && git worktree add ../<repo>-autopilot autopilot/<topic>'")
        print("  ssh mac 'cd /Volumes/SDD2T/obsidian-vault-write/custom-project/<repo>-autopilot && python3 ./automation/autopilot.py doctor --profile mac'")
        print("  ssh mac 'cd /Volumes/SDD2T/obsidian-vault-write/custom-project/<repo>-autopilot && python3 ./automation/autopilot.py bootstrap-and-daemonize --profile mac'")
        print("  ssh mac 'cd /Volumes/SDD2T/obsidian-vault-write/custom-project/<repo>-autopilot && bash ./automation/start-autopilot.sh --background -- --profile mac'")
        print("  # Verify Mac-side health immediately after remote daemonizing.")
        print("  ssh mac 'cd /Volumes/SDD2T/obsidian-vault-write/custom-project/<repo>-autopilot && python3 ./automation/autopilot.py health --state-path automation/runtime/autopilot-state.json'")
        print(
            "  ssh mac 'cd \"/Volumes/SDD2T/obsidian-vault-write/custom-project/<repo>-autopilot\" && python3 -u ./automation/autopilot.py watch --runtime-path automation/runtime --state-path automation/runtime/autopilot-state.json --tail 80 --prefix-format short'"
        )

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scaffold a repo-local Codex autopilot into a target repository.")
    parser.add_argument("--target-repo", required=True, help="Path to the target repository root or a path inside it.")
    parser.add_argument(
        "--preset",
        required=True,
        choices=sorted(PRESET_METADATA.keys()),
        help="Preset to install.",
    )
    parser.add_argument("--objective", help="Override the preset objective text.")
    parser.add_argument("--lint-command", help="Override the inferred lint command.")
    parser.add_argument("--typecheck-command", help="Override the inferred typecheck command.")
    parser.add_argument("--full-test-command", help="Override the inferred full test command.")
    parser.add_argument("--build-command", help="Override the inferred build command.")
    parser.add_argument("--vulture-command", help="Override the inferred Vulture dead-code command.")
    parser.add_argument("--seed-plan", help="Approved implementation plan to copy into docs/status and use as the seeded queue authority.")
    parser.add_argument("--seed-spec", help="Approved spec to copy into docs/status and use as the seeded queue authority.")
    parser.add_argument(
        "--deploy-policy",
        choices=["never", "always", "targeted"],
        help="Set when successful rounds must deploy after build. Prefer targeted over always for most repos.",
    )
    parser.add_argument("--deploy-verify-path", help="Path to an artifact used to verify deployed build IDs.")
    parser.add_argument(
        "--deploy-required-paths",
        nargs="+",
        help="Repo-relative files or directories that require deploy when --deploy-policy targeted is used.",
    )
    parser.add_argument("--runner-model", help="Optional Codex model override to place into config.")
    parser.add_argument(
        "--no-auto-upgrade",
        action="store_true",
        help="Disable automatic refresh of common scaffold files when an older deployed scaffold version is detected.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated files.")
    parser.add_argument("--print-next-steps", action="store_true", default=True, help="Print suggested doctor/dry-run commands.")
    parser.add_argument("--no-print-next-steps", dest="print_next_steps", action="store_false")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return scaffold_repo(args)
    except ScaffoldError as exc:
        print(f"[scaffold] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
