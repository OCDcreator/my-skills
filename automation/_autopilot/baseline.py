from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


VALIDATION_COMMAND_FIELDS = (
    "lint_command",
    "typecheck_command",
    "full_test_command",
    "build_command",
)


@dataclass(frozen=True)
class BaselineSupport:
    clean_string: Callable[..., str]
    compact_text: Callable[..., str]
    run_shell_command: Callable[..., Any]


@dataclass(frozen=True)
class BaselineCommandResult:
    command_key: str
    command_text: str
    status: str
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""


def run_validation_baseline(config: dict[str, Any], *, support: BaselineSupport) -> list[BaselineCommandResult]:
    results: list[BaselineCommandResult] = []
    for command_key in VALIDATION_COMMAND_FIELDS:
        command_text = support.clean_string(config.get(command_key))
        if not command_text:
            results.append(
                BaselineCommandResult(
                    command_key=command_key,
                    command_text="",
                    status="not_configured",
                )
            )
            continue

        command_result = support.run_shell_command(command_text, config=config, check=False)
        status = "success" if int(command_result.returncode) == 0 else "failure"
        results.append(
            BaselineCommandResult(
                command_key=command_key,
                command_text=command_text,
                status=status,
                returncode=int(command_result.returncode),
                stdout=support.clean_string(command_result.stdout),
                stderr=support.clean_string(command_result.stderr),
            )
        )
    return results


def baseline_failures(results: list[BaselineCommandResult]) -> list[BaselineCommandResult]:
    return [result for result in results if result.status == "failure"]


def format_baseline_result(result: BaselineCommandResult, *, support: BaselineSupport) -> str:
    if result.status == "not_configured":
        return "<not configured>"
    if result.status == "success":
        return result.command_text

    combined_output = "\n".join(
        part for part in (result.stdout, result.stderr) if support.clean_string(part)
    )
    if combined_output:
        return (
            f"{result.command_text} "
            f"(exit {result.returncode}; {support.compact_text(combined_output, max_length=220)})"
        )
    return f"{result.command_text} (exit {result.returncode})"
