# Diagnostic Report Template

Use Markdown so users can paste reports into issues, chat, or email.

````md
# <Plugin Name> Diagnostic Report

Generated: <ISO timestamp>
Source: <settings-copy | settings-export | manual | startup>

## Build

Plugin name: <manifest.name>
Plugin ID: <manifest.id>
Manifest version: <manifest.version>
Display version: <DISPLAY_VERSION or unavailable>
Release codename: <codename or unavailable>
BUILD_ID: <BUILD_ID>

## Environment

Obsidian platform: <desktop/mobile/platform string>
Process platform: <win32/darwin/linux if available>
Vault name: <vault name>
Vault path: <vault path or unavailable>
Locale: <plugin/app locale if relevant>

## Debug Settings

Debug logging: <true/false>
Inline serialized debug args: <true/false>
Current platform log path: <path or not set>
Debug log paths: <redacted JSON or safe summary>

## Runtime

<Project-specific runtime status>

Examples:
- File watcher active: <true/false>
- Server health: <ok/fail>
- Managed process: <true/false>
- Cache entries: <number>
- Current mode: <mode>

## Optional Subsystem Diagnostics

<Only include project-specific snapshots that help troubleshooting.>

## Recent Logs

```text
<getRecentLogText() or "(no logs captured yet)">
```
````

## Rules

- Do include `BUILD_ID`.
- Do include manifest version and display version if they differ.
- Do include vault name and vault path when useful, but treat them as user-visible diagnostic data.
- Do not include API keys, tokens, passwords, bearer headers, or provider secrets.
- Do not include full file contents, full prompts, full model outputs, binary payloads, or large base64 blobs.
- Do include source labels so developers know whether the report came from copy, export, startup, or manual command.
