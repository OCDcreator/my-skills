#!/usr/bin/env python3
"""
Kimi Code CLI Review Wrapper

Enables programmatic invocation of Kimi Code CLI for code review tasks.
Usage:
    python review.py --file src/app.ts --type security
    python review.py --code "function foo() {}" --type general
    python review.py --work-dir . --type architecture
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


REVIEW_PROMPTS = {
    "general": (
        "Perform a thorough code review. Identify bugs, logic errors, edge cases, "
        "code smells, and maintainability issues. Provide specific, actionable "
        "recommendations with line references where possible. "
        "Rate each finding: CRITICAL / WARNING / SUGGESTION."
    ),
    "security": (
        "Perform a security audit. Identify: injection vulnerabilities, "
        "authentication/authorization flaws, sensitive data exposure, "
        "insecure dependencies, missing input validation, and cryptographic misuses. "
        "Provide severity ratings and concrete remediation steps with code examples."
    ),
    "performance": (
        "Analyze for performance bottlenecks: unnecessary allocations, inefficient "
        "algorithms, blocking operations, N+1 queries, and scalability concerns. "
        "Provide Big-O analysis where applicable and suggest optimized alternatives."
    ),
    "architecture": (
        "Review architecture and design patterns. Assess separation of concerns, "
        "testability, extensibility, coupling, and adherence to language idioms. "
        "Suggest structural improvements and refactoring opportunities."
    ),
    "style": (
        "Review code style, naming conventions, documentation quality, and consistency. "
        "Suggest improvements for readability and maintainability."
    ),
}


def build_command(args: argparse.Namespace) -> list[str]:
    cmd = ["kimi", "--print", "--yolo"]

    if args.work_dir:
        cmd.extend(["--work-dir", args.work_dir])

    if args.model:
        cmd.extend(["--model", args.model])

    for d in args.add_dir or []:
        cmd.extend(["--add-dir", d])

    prompt = args.prompt or REVIEW_PROMPTS.get(args.type, REVIEW_PROMPTS["general"])

    if args.file:
        file_path = Path(args.file)
        if args.work_dir and not file_path.is_absolute():
            file_path = Path(args.work_dir) / file_path
        try:
            code = file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"Error: file not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
        ext = file_path.suffix[1:] or "text"
        prompt = (
            f"{prompt}\n\n"
            f"Review the following code from file `{file_path}`:\n\n"
            f"```{ext}\n{code}\n```"
        )
    elif args.code:
        prompt = (
            f"{prompt}\n\n"
            f"Review the following code:\n\n"
            f"```\n{args.code}\n```"
        )
    else:
        review_root = args.work_dir or "."
        prompt = (
            f"{prompt}\n\n"
            f"Review the codebase under `{review_root}`."
        )

    cmd.extend(["-p", prompt])
    return cmd


def run_kimi(cmd: list[str], timeout: int | None) -> int:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError:
        print(
            "Error: 'kimi' command not found. "
            "Ensure Kimi Code CLI is installed and on PATH.",
            file=sys.stderr,
        )
        return 1
    except subprocess.TimeoutExpired:
        print(
            f"Error: Kimi Code CLI timed out after {timeout}s. "
            "Consider increasing --timeout or reviewing a smaller scope.",
            file=sys.stderr,
        )
        return 1
    except Exception as e:
        print(f"Error invoking Kimi Code CLI: {e}", file=sys.stderr)
        return 1

    # Print stdout first (the actual review result)
    if result.stdout:
        print(result.stdout, end="")

    # Print stderr lines that are not just Kimi internal debug noise.
    # Kimi prints MCP connection logs, TurnBegin markers, etc. to stderr.
    # We filter out the noisiest internal structures to keep output clean
    # in both PowerShell (Windows) and bash/zsh (macOS/Linux).
    if result.stderr:
        noisy_prefixes = (
            "TurnBegin(",
            "StatusUpdate(",
            "MCPLoading",
            "StepBegin(",
            "ThinkPart(",
            "ToolCall(",
            "ToolResult(",
            "ToolCallPart(",
            "TextPart(",
            "TurnEnd()",
            "To resume this session:",
        )
        for line in result.stderr.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if any(stripped.startswith(p) for p in noisy_prefixes):
                continue
            # Keep genuine errors or concise status lines
            print(line, file=sys.stderr)

    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Invoke Kimi Code CLI for code review"
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--file", help="Path to file to review")
    input_group.add_argument("--code", help="Code string to review")
    parser.add_argument(
        "--type",
        choices=list(REVIEW_PROMPTS.keys()),
        default="general",
        help="Review type (default: general)",
    )
    parser.add_argument(
        "--prompt", help="Custom review prompt (overrides --type)"
    )
    parser.add_argument("--work-dir", help="Working directory / project root")
    parser.add_argument(
        "--add-dir", action="append", help="Additional directories to include"
    )
    parser.add_argument("--model", help="Model to use")
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds for the Kimi CLI call (default: 300)",
    )

    args = parser.parse_args()

    if not args.file and not args.code and not args.work_dir:
        parser.error("Must specify --file, --code, or --work-dir")

    cmd = build_command(args)
    return run_kimi(cmd, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
