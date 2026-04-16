#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
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

SCALLOWED_SOURCE_SUFFIXES = {
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
    targeted_test_prefixes: list[str] = field(default_factory=list)
    command_sources: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    root_dirs: list[str] = field(default_factory=list)
    source_entrypoints: list[str] = field(default_factory=list)
    test_entrypoints: list[str] = field(default_factory=list)


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


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def render_tokens(template_text: str, tokens: dict[str, str]) -> str:
    rendered = template_text
    for token_name, token_value in tokens.items():
        rendered = rendered.replace(f"[[{token_name}]]", token_value)
    return rendered


def json_token(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


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
        if path.suffix.lower() not in SCALLOWED_SOURCE_SUFFIXES:
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
    ]
    lines = []
    for label, command, source in rows:
        if command:
            lines.append(f"- {label}: `{command}` (source: `{source}`)")
        else:
            lines.append(f"- {label}: not inferred")
    return "\n".join(lines)


def write_if_changed(path: Path, content: str, *, force: bool) -> str:
    if path.exists():
        existing = read_text(path)
        if existing == content:
            return "unchanged"
        if not force:
            raise ScaffoldError(f"Refusing to overwrite existing file without --force: {path}")
    write_text(path, content)
    return "written"


def render_template_tree(
    source_root: Path,
    destination_root: Path,
    tokens: dict[str, str],
    *,
    force: bool,
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
        results[normalize_repo_path(destination_path, destination_root)] = write_if_changed(destination_path, rendered, force=force)
    return results


def ensure_runtime_gitignore(repo_root: Path, *, force: bool) -> str:
    gitignore_path = repo_root / ".gitignore"
    entry = "automation/runtime/"
    if not gitignore_path.exists():
        write_text(gitignore_path, entry + "\n")
        return "written"

    existing = read_text(gitignore_path)
    lines = existing.splitlines()
    if any(line.strip() == entry for line in lines):
        return "unchanged"

    suffix = "" if existing.endswith("\n") or not existing else "\n"
    new_content = existing + suffix + entry + "\n"
    write_text(gitignore_path, new_content)
    return "written"


def default_tokens(detection: DetectionResult, preset: str) -> dict[str, str]:
    metadata = PRESET_METADATA[preset]
    path_list = build_path_list(detection.repo_root, detection)
    entrypoints = build_entrypoints(detection, preset)

    lint_command = detection.lint_command
    typecheck_command = detection.typecheck_command
    full_test_command = detection.full_test_command
    build_command = detection.build_command

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
        "PHASE_DOC_PREFIX_JSON": json.dumps("docs/status/autopilot-phase-", ensure_ascii=False),
        "STARTING_PHASE_DOC_JSON": json.dumps("docs/status/autopilot-phase-0.md", ensure_ascii=False),
        "NEXT_PHASE_NUMBER": "1",
        "PROMPT_TEMPLATE_JSON": json.dumps("automation/round-prompt.md", ensure_ascii=False),
        "RESULT_SCHEMA_JSON": json.dumps("automation/round-result.schema.json", ensure_ascii=False),
        "DEPLOY_AFTER_BUILD_JSON": "false",
        "DEPLOY_POLICY_JSON": json.dumps("never", ensure_ascii=False),
        "DEPLOY_REQUIRED_PATHS_JSON": "[]",
        "RUNNER_KIND_JSON": json.dumps("codex", ensure_ascii=False),
        "RUNNER_COMMAND_JSON": json.dumps("", ensure_ascii=False),
        "RUNNER_MODEL_JSON": json.dumps("", ensure_ascii=False),
        "RUNNER_EXTRA_ARGS_JSON": "[]",
        "RUNNER_ADDITIONAL_DIRS_JSON": "[]",
        "BUILD_VERIFY_PATH_JSON": json.dumps("", ensure_ascii=False),
    }
    return tokens


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
    }
    for arg_name, token_name in command_flags.items():
        value = clean_string(getattr(args, arg_name))
        if value:
            overrides[token_name] = value
            overrides[f"{token_name}_JSON"] = json.dumps(value, ensure_ascii=False)

    if clean_string(args.runner_model):
        overrides["RUNNER_MODEL_JSON"] = json.dumps(clean_string(args.runner_model), ensure_ascii=False)

    return overrides


def scaffold_repo(args: argparse.Namespace) -> int:
    target_repo = Path(args.target_repo).expanduser().resolve()
    repo_root = resolve_git_root(target_repo)
    detection = detect_commands(repo_root)
    tokens = override_tokens(default_tokens(detection, args.preset), args)

    common_root = COMMON_TEMPLATES_ROOT
    preset_root = PRESET_TEMPLATES_ROOT / args.preset
    if not preset_root.exists():
        raise ScaffoldError(f"Preset template directory not found: {preset_root}")

    common_results = render_template_tree(common_root, repo_root, tokens, force=args.force)
    preset_results = render_template_tree(preset_root, repo_root, tokens, force=args.force)
    gitignore_result = ensure_runtime_gitignore(repo_root, force=args.force)

    print(f"[scaffold] target repo: {repo_root}")
    print(f"[scaffold] preset: {args.preset} ({PRESET_METADATA[args.preset]['label']})")
    print("[scaffold] inferred validation commands:")
    print(build_validation_bullets(detection))
    for warning in detection.warnings:
        print(f"[scaffold] warning: {warning}")

    written_count = sum(1 for status in [*common_results.values(), *preset_results.values(), gitignore_result] if status == "written")
    unchanged_count = sum(1 for status in [*common_results.values(), *preset_results.values(), gitignore_result] if status == "unchanged")
    print(f"[scaffold] files written: {written_count}, unchanged: {unchanged_count}")

    if args.print_next_steps:
        print("[scaffold] next commands:")
        print("  python automation/autopilot.py doctor --profile windows")
        print("  python automation/autopilot.py start --profile windows --dry-run --single-round")
        print("  python3 ./automation/autopilot.py doctor --profile mac")
        print("  python3 ./automation/autopilot.py start --profile mac --dry-run --single-round")

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
    parser.add_argument("--runner-model", help="Optional Codex model override to place into config.")
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
