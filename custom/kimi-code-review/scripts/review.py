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
        file_path = args.file
        if args.work_dir and not os.path.isabs(file_path):
            file_path = os.path.join(args.work_dir, file_path)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
        except FileNotFoundError:
            print(f"Error: file not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
        ext = os.path.splitext(file_path)[1][1:] or "text"
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

    args = parser.parse_args()

    if not args.file and not args.code and not args.work_dir:
        parser.error("Must specify --file, --code, or --work-dir")

    cmd = build_command(args)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        print(
            "Error: 'kimi' command not found. "
            "Ensure Kimi Code CLI is installed and on PATH.",
            file=sys.stderr,
        )
        return 1
    except Exception as e:
        print(f"Error invoking Kimi Code CLI: {e}", file=sys.stderr)
        return 1

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
