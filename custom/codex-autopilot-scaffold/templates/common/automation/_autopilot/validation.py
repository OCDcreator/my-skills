from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


SCHEMA_REQUIRED_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
    "null": (type(None),),
}


@dataclass(frozen=True)
class ValidationSupport:
    clean_string: Callable[..., str]
    resolve_repo_path: Callable[..., Path]
    run_git: Callable[..., Any]
    info: Callable[..., None]


def validate_schema_value(name: str, value: Any, property_schema: dict[str, Any]) -> str | None:
    allowed_types = property_schema.get("type")
    if allowed_types:
        type_names = [allowed_types] if isinstance(allowed_types, str) else list(allowed_types)
        allowed_python_types = tuple(
            python_type
            for type_name in type_names
            for python_type in SCHEMA_REQUIRED_TYPES.get(type_name, ())
        )
        if allowed_python_types and not isinstance(value, allowed_python_types):
            return f"{name} has invalid type."

    enum_values = property_schema.get("enum")
    if enum_values and value not in enum_values:
        return f"{name} must be one of: {', '.join(map(str, enum_values))}."

    min_length = property_schema.get("minLength")
    if isinstance(min_length, int) and isinstance(value, str) and len(value) < min_length:
        return f"{name} must be at least {min_length} characters."

    if property_schema.get("type") == "array" and isinstance(value, list):
        item_schema = property_schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                item_error = validate_schema_value(f"{name}[{index}]", item, item_schema)
                if item_error:
                    return item_error

    return None


def validate_result_shape(result: Any, schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(result, dict):
        return ["Agent output must be a JSON object."]

    required_fields = schema.get("required", [])
    for field_name in required_fields:
        if field_name not in result:
            errors.append(f"Agent output is missing required field '{field_name}'.")

    if schema.get("additionalProperties") is False:
        allowed_fields = set((schema.get("properties") or {}).keys())
        for field_name in result.keys():
            if field_name not in allowed_fields:
                errors.append(f"Agent output includes unexpected field '{field_name}'.")

    for field_name, property_schema in (schema.get("properties") or {}).items():
        if field_name not in result:
            continue
        field_error = validate_schema_value(field_name, result[field_name], property_schema)
        if field_error:
            errors.append(field_error)

    return errors


def get_commit_files(commit_sha: str, *, run_git: Callable[..., Any]) -> list[str]:
    output = run_git(["diff-tree", "--no-commit-id", "--name-only", "-r", commit_sha]).stdout
    if not output:
        return []
    return [line for line in output.splitlines() if line.strip()]


def normalize_repo_file_path(file_path: str) -> str:
    return file_path.replace("\\", "/").strip()


def path_matches_any(file_path: str, configured_paths: list[str]) -> bool:
    normalized = normalize_repo_file_path(file_path)
    for configured_path in configured_paths:
        candidate = normalize_repo_file_path(str(configured_path))
        if not candidate:
            continue
        if candidate.endswith("/"):
            if normalized.startswith(candidate):
                return True
            continue
        if normalized == candidate or normalized.startswith(f"{candidate}/"):
            return True
    return False


def test_targeted_tests_required(files: list[str], config: dict[str, Any]) -> bool:
    configured_paths = list(config.get("targeted_test_required_paths", []))
    if configured_paths:
        return any(path_matches_any(file_path, configured_paths) for file_path in files)

    for file_path in files:
        normalized = normalize_repo_file_path(file_path)
        if normalized.startswith(("src/", "app/", "lib/", "pkg/", "internal/", "cmd/", "crates/", "tests/")):
            return True
        if normalized in {"package.json", "package-lock.json", "pyproject.toml", "Cargo.toml", "go.mod", "Makefile", "justfile"}:
            return True
    return False


def test_build_required(files: list[str], config: dict[str, Any], *, clean_string: Callable[..., str]) -> bool:
    if not clean_string(config.get("build_command")):
        return False

    configured_paths = list(config.get("build_required_paths", []))
    if configured_paths:
        return any(path_matches_any(file_path, configured_paths) for file_path in files)

    for file_path in files:
        normalized = normalize_repo_file_path(file_path)
        if normalized.startswith(("src/", "app/", "lib/", "pkg/", "internal/", "cmd/", "crates/", "assets/", "scripts/")):
            return True
        if normalized in {
            "package.json",
            "package-lock.json",
            "pyproject.toml",
            "Cargo.toml",
            "go.mod",
            "Makefile",
            "justfile",
            "manifest.json",
        }:
            return True
        if normalized.endswith((".ts", ".tsx", ".js", ".mjs", ".cjs", ".css", ".py", ".rs", ".go")) and not normalized.startswith(
            ("tests/", "docs/", "automation/")
        ):
            return True
    return False


def test_full_test_required(files: list[str], attempt_number: int, config: dict[str, Any]) -> bool:
    configured_paths = list(config.get("full_test_required_paths", []))
    cadence_rounds = int(config.get("full_test_cadence_rounds", 0) or 0)
    if cadence_rounds > 0 and attempt_number > 0 and attempt_number % cadence_rounds == 0:
        return True
    return any(path_matches_any(file_path, configured_paths) for file_path in files)


def test_deploy_required(files: list[str], config: dict[str, Any], *, clean_string: Callable[..., str]) -> bool:
    deploy_policy = clean_string(config.get("deploy_policy")).lower()
    configured_paths = list(config.get("deploy_required_paths", []))
    if deploy_policy == "always":
        return True
    if deploy_policy == "targeted":
        return any(path_matches_any(file_path, configured_paths) for file_path in files)
    return bool(config.get("deploy_after_build"))


def count_command_occurrences(commands_run: list[str], needle: str) -> int:
    return sum(str(command).count(needle) for command in commands_run)


def test_command_budget_exceeded(commands_run: list[str], config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    max_git_status = int(config.get("max_git_status_per_round", 0) or 0)
    max_git_diff_stat = int(config.get("max_git_diff_stat_per_round", 0) or 0)

    git_status_count = count_command_occurrences(commands_run, "git status --short")
    git_diff_stat_count = count_command_occurrences(commands_run, "git diff --stat")

    if max_git_status > 0 and git_status_count > max_git_status:
        errors.append(
            f"commands_run used 'git status --short' {git_status_count} times, exceeding limit {max_git_status}."
        )
    if max_git_diff_stat > 0 and git_diff_stat_count > max_git_diff_stat:
        errors.append(
            f"commands_run used 'git diff --stat' {git_diff_stat_count} times, exceeding limit {max_git_diff_stat}."
        )
    return errors


def handle_command_budget_findings(commands_run: list[str], config: dict[str, Any], *, support: ValidationSupport) -> list[str]:
    findings = test_command_budget_exceeded(commands_run, config)
    if not findings:
        return []

    policy = support.clean_string(config.get("command_budget_policy")).lower() or "warn"
    if policy in {"hard", "fail", "error"}:
        return findings

    for finding in findings:
        support.info(f"Command budget warning: {finding}")
    return []


def command_matches_full_test(command: str, full_test_command: str, *, clean_string: Callable[..., str]) -> bool:
    return clean_string(command) == clean_string(full_test_command)


def command_matches_targeted_test(
    command: str,
    targeted_prefixes: list[str],
    *,
    clean_string: Callable[..., str],
) -> bool:
    normalized_command = clean_string(command)
    if not normalized_command:
        return False
    return any(normalized_command.startswith(clean_string(prefix)) for prefix in targeted_prefixes if clean_string(prefix))


def tests_run_include_exact(tests_run: list[str], command: str, *, clean_string: Callable[..., str]) -> bool:
    normalized_command = clean_string(command)
    if not normalized_command:
        return True
    return any(clean_string(test_command) == normalized_command for test_command in tests_run)


def test_runs_include_targeted_tests(
    tests_run: list[str],
    config: dict[str, Any],
    *,
    clean_string: Callable[..., str],
) -> bool:
    targeted_prefixes = [str(prefix) for prefix in config.get("targeted_test_prefixes", [])]
    return any(command_matches_targeted_test(str(command), targeted_prefixes, clean_string=clean_string) for command in tests_run)


def test_runs_include_full_test(
    tests_run: list[str],
    config: dict[str, Any],
    *,
    clean_string: Callable[..., str],
) -> bool:
    full_test_command = clean_string(config.get("full_test_command"))
    if not full_test_command:
        return True
    return any(command_matches_full_test(str(command), full_test_command, clean_string=clean_string) for command in tests_run)


def test_deployed_build_id(verify_path: str, build_id: str) -> bool:
    deployed_artifact_path = Path(verify_path)
    if not deployed_artifact_path.exists():
        return False
    return build_id in deployed_artifact_path.read_text(encoding="utf-8", errors="replace")


def validate_round_result(
    *,
    attempt_number: int,
    result: dict[str, Any],
    schema: dict[str, Any],
    phase_doc_relative_path: str,
    expected_lane_id: str,
    config: dict[str, Any],
    ending_head: str,
    working_tree_dirty: bool,
    support: ValidationSupport,
) -> str | None:
    validation_errors = validate_result_shape(result, schema)

    if validation_errors:
        return " ".join(validation_errors)

    clean_string = support.clean_string
    status = clean_string(result.get("status"))
    reported_lane_id = clean_string(result.get("lane_id"))
    if reported_lane_id != expected_lane_id:
        validation_errors.append(
            f"Result lane_id '{reported_lane_id}' does not match active lane '{expected_lane_id}'."
        )

    if status == "success":
        phase_doc_path_from_result = clean_string(result.get("phase_doc_path"))
        if not phase_doc_path_from_result:
            validation_errors.append("success result is missing phase_doc_path.")
        elif phase_doc_path_from_result != phase_doc_relative_path:
            validation_errors.append(
                f"success result phase_doc_path '{phase_doc_path_from_result}' does not match expected '{phase_doc_relative_path}'."
            )
        elif not support.resolve_repo_path(phase_doc_path_from_result).exists():
            validation_errors.append(f"phase doc '{phase_doc_path_from_result}' does not exist.")

        commit_sha = clean_string(result.get("commit_sha"))
        if not commit_sha:
            validation_errors.append("success result is missing commit_sha.")

        commit_message = clean_string(result.get("commit_message"))
        if not commit_message:
            validation_errors.append("success result is missing commit_message.")

        plan_review_command = clean_string(config.get("plan_review_command"))
        if plan_review_command and not clean_string(result.get("plan_review_verdict")):
            validation_errors.append("success result is missing plan_review_verdict for a review-gated round.")

        code_review_command = clean_string(config.get("code_review_command"))
        if code_review_command and not clean_string(result.get("code_review_verdict")):
            validation_errors.append("success result is missing code_review_verdict for a review-gated round.")

        if bool(result.get("background_tasks_used")) and not bool(result.get("background_tasks_completed")):
            validation_errors.append(
                "background tasks were used but background_tasks_completed=false; "
                "do not treat the main pass exit as round completion."
            )

        if not bool(result.get("repo_visible_work_landed")):
            validation_errors.append(
                "repo_visible_work_landed=false; wait until implementation-owned repo-visible work has landed before success."
            )

        if not bool(result.get("final_artifacts_written")):
            validation_errors.append(
                "final_artifacts_written=false; wait until the final round output artifacts are written before success."
            )

        if commit_sha and ending_head != commit_sha:
            validation_errors.append(f"HEAD '{ending_head}' does not match commit_sha '{commit_sha}'.")

        if commit_sha:
            actual_commit_message = clean_string(support.run_git(["log", "-1", "--pretty=%s", commit_sha]).stdout)
            if actual_commit_message != commit_message:
                validation_errors.append(
                    f"Actual commit message '{actual_commit_message}' does not match reported '{commit_message}'."
                )

            commit_prefix = f"{clean_string(config.get('commit_prefix'))}:"
            if commit_prefix != ":" and not actual_commit_message.lower().startswith(commit_prefix.lower()):
                validation_errors.append(f"Commit message must start with '{commit_prefix}'.")

            validated_commit_files = get_commit_files(commit_sha, run_git=support.run_git)
            if test_build_required(validated_commit_files, config, clean_string=clean_string) and not bool(result.get("build_ran")):
                validation_errors.append("This round changed build-relevant files but reported build_ran=false.")

            tests_run = [str(command) for command in result.get("tests_run", [])]
            lint_command = clean_string(config.get("lint_command"))
            if lint_command and not tests_run_include_exact(tests_run, lint_command, clean_string=clean_string):
                validation_errors.append(f"This round did not report configured lint command '{lint_command}'.")

            typecheck_command = clean_string(config.get("typecheck_command"))
            if typecheck_command and not tests_run_include_exact(tests_run, typecheck_command, clean_string=clean_string):
                validation_errors.append(
                    f"This round did not report configured typecheck command '{typecheck_command}'."
                )

            if bool(config.get("targeted_test_required")) and test_targeted_tests_required(validated_commit_files, config):
                if not test_runs_include_targeted_tests(tests_run, config, clean_string=clean_string):
                    validation_errors.append("This round changed code/test files but did not report targeted tests.")

            if test_full_test_required(validated_commit_files, attempt_number, config):
                if not test_runs_include_full_test(tests_run, config, clean_string=clean_string):
                    validation_errors.append(
                        "This round required full test coverage but did not report the configured full test command."
                    )

            validation_errors.extend(
                handle_command_budget_findings(
                    [str(command) for command in result.get("commands_run", [])],
                    config,
                    support=support,
                )
            )

        build_id = clean_string(result.get("build_id"))
        if bool(result.get("build_ran")) and not build_id:
            validation_errors.append("build_ran=true requires a non-empty build_id.")

        validated_commit_files = get_commit_files(commit_sha, run_git=support.run_git) if commit_sha else []
        deploy_required = test_deploy_required(validated_commit_files, config, clean_string=clean_string)

        if bool(result.get("build_ran")) and deploy_required and not bool(result.get("deploy_ran")):
            validation_errors.append("This round required deployment after build but reported deploy_ran=false.")

        if bool(result.get("deploy_ran")) and not deploy_required:
            support.info("Result reported deployment for a non-deploy-required round; allowing it.")

        if bool(result.get("deploy_ran")) and not bool(result.get("deploy_verified")):
            validation_errors.append("deploy_ran=true requires deploy_verified=true.")

        deploy_verify_path = clean_string(config.get("deploy_verify_path"))
        if (
            bool(result.get("deploy_ran"))
            and build_id
            and deploy_verify_path
            and not test_deployed_build_id(deploy_verify_path, build_id)
        ):
            validation_errors.append(f"Deploy verification artifact does not contain BUILD_ID '{build_id}'.")

        if working_tree_dirty:
            validation_errors.append("Working tree is dirty after success commit.")

    elif status == "failure":
        blocking_reason = clean_string(result.get("blocking_reason"))
        if not blocking_reason:
            validation_errors.append("Agent reported failure without blocking_reason.")
        else:
            return " ".join(validation_errors + [blocking_reason]) if validation_errors else blocking_reason
    elif status == "goal_complete":
        if working_tree_dirty:
            validation_errors.append("goal_complete returned with a dirty working tree.")
        else:
            goal_commit_sha = clean_string(result.get("commit_sha"))
            if goal_commit_sha and goal_commit_sha != ending_head:
                validation_errors.append(
                    f"goal_complete reported commit_sha '{goal_commit_sha}' but HEAD is '{ending_head}'."
                )
    else:
        validation_errors.append(f"Unknown agent status '{status}'.")

    return " ".join(validation_errors) if validation_errors else None
