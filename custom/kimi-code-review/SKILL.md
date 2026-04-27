---
name: kimi-code-review
description: Enable external AI agents and automated systems to invoke Kimi Code CLI for code review, quality analysis, and automated auditing. Use when (1) another agent or CI pipeline needs to delegate code review to Kimi Code CLI programmatically, (2) an external system wants to leverage Kimi Code CLI review capabilities via shell or ACP, (3) setting up automated code review workflows that invoke Kimi as a subprocess, or (4) bridging Kimi Code CLI into other agent frameworks that support shell or MCP tool invocation.
---

# Kimi Code Review

This skill enables other agents to invoke Kimi Code CLI for code review tasks through shell execution or ACP protocol.

## Prerequisites

- Kimi Code CLI (`kimi`) must be installed and available on the system PATH.
- The calling environment must have shell execution capabilities.

## Quick Start

For a single file review, run:

```bash
python scripts/review.py --file src/app.ts --type security
```

For project-wide review:

```bash
kimi --print --yolo --work-dir . \
  -p "Perform a comprehensive code review. Focus on bugs, security, and performance."
```

## Invocation Methods

### Method 1: Direct Shell (Recommended for One-Off Reviews)

Use `kimi --print --yolo` for fully automated, non-interactive review:

```bash
kimi --print --yolo \
  --work-dir <project-root> \
  -p "<review-instructions>"
```

Flags explained:
- `--print`: Non-interactive mode; outputs final response to stdout
- `--yolo`: Auto-approve all tool uses (required for automation)
- `--work-dir`: Project root for context resolution
- `--add-dir`: Include extra directories (repeatable)
- `--model`: Override default model

Pass code via stdin for snippets:

```bash
echo '<code>' | kimi --print --yolo --input-format text -p "Review this code"
```

### Method 2: Helper Script

Use `scripts/review.py` for a convenient wrapper with built-in prompt templates:

```bash
# POSIX (macOS / Linux / WSL / Git Bash)
python scripts/review.py \
  --file <path> \
  --type [general|security|performance|architecture|style] \
  [--work-dir <dir>] \
  [--model <model>] \
  [--timeout <seconds>]

# PowerShell (Windows)
python scripts\review.py `
  --file <path> `
  --type security `
  --work-dir <dir> `
  --timeout 300
```

Review project instead of single file (omit `--file` and `--code`):

```bash
python scripts/review.py --work-dir . --type general
```

> **Note on `--file` behavior**: this script reads the file and inlines its full contents into the prompt. For large, generated, or minified files this can waste context window or exceed limits. For large files or whole-repo reviews, prefer Method 1 (direct shell) so Kimi reads the file from disk itself.

> **Cross-platform stderr**: Kimi prints MCP connection logs and internal step markers to stderr. The wrapper filters noisy internal structures so you get clean output on both PowerShell and bash/zsh. If you need full debug logs, use Method 1 directly.

### Method 3: ACP Server (Recommended for Persistent Integration)

Start Kimi Code CLI as an ACP server for other agents to connect over stdio or wire:

```bash
# Foreground (testing)
kimi acp

# Background — POSIX (macOS / Linux)
nohup kimi acp > /tmp/kimi-acp.log 2>&1 &

# Background — PowerShell (Windows)
$proc = Start-Process -FilePath "kimi" -ArgumentList "acp" -PassThru -WindowStyle Hidden
# Stop later: Stop-Process -Id $proc.Id
```

Other agents can then dispatch review tasks via the Agent Communication Protocol. See Kimi Code CLI docs for ACP protocol details and connection options.

> **Platform note**: On macOS, `kimi acp` may print an `authlib.jose` deprecation warning and exit if run without stdio attached. Use `nohup` or `launchd` for persistent background operation. On Windows, use `Start-Process` or run inside WSL.

## Prompt Templates

Use these templates as starting points for custom prompts.

### General Code Review

```
Perform a thorough code review. Identify bugs, logic errors, edge cases,
code smells, and maintainability issues. Provide specific line-by-line
feedback and actionable fixes. Rate each issue: CRITICAL / WARNING / SUGGESTION.
```

### Security Audit

```
Perform a security audit. Identify: injection vulnerabilities,
authentication/authorization flaws, sensitive data exposure,
insecure dependencies, missing input validation, and cryptographic misuses.
Provide severity ratings and concrete remediation steps with code examples.
```

### Performance Analysis

```
Analyze for performance bottlenecks: unnecessary allocations, inefficient
algorithms, blocking operations, N+1 queries, and scalability concerns.
Provide Big-O analysis where applicable and suggest optimized alternatives.
```

### Architecture Review

```
Review architecture and design patterns. Assess: separation of concerns,
testability, extensibility, coupling, and adherence to language idioms.
Suggest structural improvements and refactoring opportunities.
```

### Style Review

```
Review code style, naming conventions, documentation quality, and consistency.
Suggest improvements for readability and maintainability.
```

## Output Processing

Kimi Code CLI in `--print` mode outputs markdown to stdout.

Parse the output for downstream automation:
- Severity markers: `CRITICAL`, `WARNING`, `SUGGESTION` (or emoji equivalents)
- Code blocks: contain suggested fixes
- File references: often formatted as `file.ts:line` or backtick paths

Example pipeline to extract critical issues:

```bash
# POSIX
kimi --print --yolo -p "Review src/ for security issues" | grep -i "CRITICAL"

# PowerShell
kimi --print --yolo -p "Review src/ for security issues" | Select-String -Pattern "CRITICAL" -CaseSensitive:$false
```

### Timeouts

Project-wide reviews or large files may take longer on slower machines. The wrapper defaults to **300 seconds**; override with `--timeout`:

```bash
# Large project — allow 10 minutes
python scripts/review.py --work-dir . --type architecture --timeout 600
```

## Best Practices

1. Always set `--work-dir` to the project root so Kimi resolves imports, configs, and dependencies correctly.
2. For large codebases, review module-by-module rather than all-at-once to stay within context limits.
3. Include specific focus areas in the prompt to reduce noise and improve relevance.
4. Use `--add-dir` to include related packages or shared libraries outside `--work-dir`.
5. Combine review types in a single prompt when context allows (e.g., "security and performance").
6. **Cross-platform**: Use `pathlib.Path` (already used by the wrapper) for path handling so `/` and `\` separators work correctly on both Windows and macOS/Linux.
7. **Timeouts**: macOS and lower-powered machines may need `--timeout 600` or more for project-wide reviews.
8. **Stderr noise**: If using the wrapper, noisy Kimi internal logs are filtered. If you need raw stderr for debugging, use Method 1 (direct shell) directly.
