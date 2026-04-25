# Codex Autopilot Watch Human-Multiline Rendering Design

## Goal

Improve `custom/codex-autopilot-scaffold` watch readability by adding **human-view-only** multiline alignment and soft wrapping.

This pass is intentionally narrow:

- only the `watch` presentation layer changes,
- only `--view human` gets multiline alignment,
- `--view raw` stays functionally unchanged.

The change must not require any runner upgrade, any `progress.log` format change, or any target-repo code change.

## Current State

- `progress.log` already contains one emitted summary per line.
- `watch` already supports `raw` and `human` views.
- `human` view improves semantic readability, but each rendered detail still prints as one terminal line.
- When a human summary is longer than the terminal width, the terminal emulator decides where the line wraps.
- Terminal-driven wrapping usually restarts at column 0 instead of aligning under the watch prefix content column.

That makes long human summaries harder to scan than they need to be.

## Scope

### In scope

- human-view hanging-indent rendering,
- human-view soft wrapping based on local terminal width,
- preservation of the existing prefix on the first line only,
- aligned continuation lines under the message content column,
- regression tests for human wrapping and raw non-regression.

### Out of scope

- any change to `raw` message semantics,
- any escaped-sequence decoding policy for raw command text,
- any new CLI flags for wrap or multiline modes,
- any `progress.log` emission change,
- any health/status/controller behavior change.

## Requirements

### 1. Watch-only behavior

The feature must only affect watcher output.

It must not change:

- `progress.log`,
- `events.jsonl`,
- `runner-status.json`,
- controller progress emission,
- remote Mac runtime behavior.

### 2. Human-view-only rendering

Only `view="human"` should receive the new multiline formatting behavior.

`view="raw"` must continue printing the current literal prefixed lines as it does today.

### 3. Prefix-aware hanging indent

When one human-rendered watch detail needs multiple visual lines, it should render as:

```text
[a2-mcp-settings q2/3 r013 p002 active f0] wait: Waiting on OpenCode implementation
                                              wrapper while the repair pass finishes
```

That means:

- first line uses the normal watch prefix,
- continuation lines use spaces equal to `len(prefix) + 1`,
- continuation lines must not repeat the full prefix.

### 4. Local terminal soft wrapping

The renderer should use the local watcher terminal width to decide when a human summary needs wrapping.

It should:

- use a best-effort width query such as `shutil.get_terminal_size`,
- fall back to a conservative default width when unavailable,
- compute available message width as `terminal_width - len(prefix) - 1`,
- enforce a small safe minimum content width.

### 5. Old logs stay compatible

The new renderer must work with existing watch input.

It must not assume:

- new structured payloads,
- new channels,
- new JSON fields,
- richer metadata from the runner.

## Rendering Model

### Step 1: Keep message selection unchanged

The current logic that decides the rendered human string should remain in place:

- raw view still prints the original watch detail line,
- human view still converts a raw progress line into a semantic summary like `docs: ...`, `wait: ...`, `impl: ...`, or `fail: ...`.

### Step 2: Add a final human-only layout pass

After the human summary string is chosen:

1. split it into logical lines if needed,
2. wrap each logical line to the available content width,
3. print the first wrapped segment as `"{prefix} {segment}"`,
4. print continuation segments as `"{' ' * (len(prefix) + 1)}{segment}"`.

This keeps the change isolated to the final display step.

## Proposed Implementation Surfaces

### `templates/common/automation/_autopilot/status_views.py`

Add a small stdlib-only helper that:

- detects terminal width,
- calculates available content width from the existing prefix,
- wraps human summary text with hanging indentation,
- leaves raw rendering untouched.

`print_watch_detail_lines(...)` remains the main integration point.

### `templates/common/automation/_autopilot/watch_runtime.py`

No logic change should be needed beyond continuing to pass `view="human"` / `view="raw"` into `print_watch_detail_lines(...)`.

### CLI

No new CLI flags in this pass.

## Regression Coverage

Add scaffold-level tests that prove:

1. human view wraps long human summaries into multiple aligned lines,
2. continuation lines align under the content column rather than repeating the prefix,
3. raw view keeps the current single-line literal behavior for the same input,
4. existing human semantic summary behavior still works.

## Risks and Mitigations

- **Risk: wrapping becomes inconsistent across terminals**
  - Mitigation: use a stdlib terminal-width query with a stable fallback width.

- **Risk: raw behavior changes accidentally**
  - Mitigation: keep the wrapping helper scoped to `view="human"` and add a raw non-regression test.

- **Risk: very narrow terminals produce ugly output**
  - Mitigation: enforce a minimum content width and fall back to coarse wrapping rather than breaking the prefix layout.

## Success Criteria

- Long human watch lines become easier to scan because continuation lines align under the message column.
- Raw view remains unchanged.
- The implementation stays entirely inside the watcher rendering layer.
- Regression coverage proves both the new human wrapping behavior and the preserved raw behavior.
