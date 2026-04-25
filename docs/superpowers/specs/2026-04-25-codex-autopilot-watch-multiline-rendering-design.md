# Codex Autopilot Watch Multiline Rendering Design

## Goal

Improve `custom/codex-autopilot-scaffold` watch readability by adding a watch-only multiline rendering layer that can:

- expand literal escaped newlines such as `\n` into visually separated lines,
- optionally soft-wrap long detail lines with hanging indentation under the existing watch prefix,
- preserve the existing runtime artifacts and runner behavior,
- keep a near-raw operator mode for users who still want the underlying `progress.log` semantics.

The change must stay entirely in the watch presentation layer. It must not require any remote runner upgrade, any progress-log format change, or any modification to target-repo product code.

## Current State

- The scaffold already writes one logical summary per `progress.log` line.
- Upstream event summarization already compacts most messages into single-line watch-friendly text.
- The current watch renderer prefixes each line and prints it as a single terminal line.
- The new human-summary view improves semantic readability, but it still renders each emitted detail as one printed line.
- If a message contains escaped newline text such as `\\n`, that content is currently normalized into spaces rather than displayed as multiple aligned lines.
- If a message is visually too wide for the terminal, line wrapping is left entirely to the terminal emulator, so continuation alignment is inconsistent and usually starts from column 0 rather than the content column.

This means the current watch output still loses an important readability opportunity: message structure and continuation alignment.

## Requirements

### 1. Watch-only scope

The feature must only change watch rendering behavior.

It must not change:

- `progress.log` file contents,
- `events.jsonl`,
- `runner-status.json`,
- controller progress emission,
- remote Mac runner behavior,
- health/status semantics outside of watch presentation.

### 2. Separate newline expansion from soft wrapping

The design must treat these as two distinct behaviors:

1. **Escaped newline expansion**
   - Convert literal escaped sequences such as `\\n` into actual visual line breaks during watch rendering.

2. **Soft wrapping**
   - Visually wrap long rendered lines to the available terminal width with hanging indentation aligned under the content area.

These are related but not the same thing, and operators should be able to control them independently.

### 3. Preserve a near-raw mode

`watch --view raw` should remain close to the underlying line-oriented `progress.log`.

That means:

- expanding literal escaped newlines is acceptable because it is exposing message structure already present in the log text,
- but synthetic soft wrapping should remain optional rather than silently forced in raw mode.

### 4. Improve default readability

The default watch experience should favor operator readability:

- `human` view should expand escaped newlines,
- `human` view should soft-wrap long lines by default,
- continuation lines should align under the message column rather than restarting at the left edge.

### 5. Keep compatibility with old logs

The feature must work with existing logs that only contain the current single-line summary format.

It must not assume:

- richer structured payloads,
- terminal width metadata from the runner,
- new progress channels,
- new JSON fields.

### 6. Avoid confusing prefix repetition

When a single logical watch detail becomes multiple visual lines, the watch output must not repeat the full prefix on every continuation line.

The target shape is:

```text
[a2-mcp-settings q2/3 r013 p002 active f0] [16:12:15] [codex] First line
                                                                 Second line
```

not:

```text
[a2-mcp-settings q2/3 r013 p002 active f0] [16:12:15] [codex] First line
[a2-mcp-settings q2/3 r013 p002 active f0] [16:12:15] [codex] Second line
```

## Proposed CLI Surface

Keep the existing `--view {human,raw}` and add two new watch-only options:

### `--multiline {off,escaped}`

- `off`
  - Render message text as a single logical line, preserving the current behavior.
- `escaped`
  - Expand escaped control sequences that should affect display layout:
    - `\\n` -> newline
    - optionally `\\t` -> spaces (normalized consistently)

Recommended defaults:

- `human`: `escaped`
- `raw`: `escaped`

### `--wrap {off,soft}`

- `off`
  - Emit each logical rendered line as-is; terminal width handling is left to the terminal.
- `soft`
  - Wrap long rendered lines to the detected terminal width and indent continuation lines to the message column.

Recommended defaults:

- `human`: `soft`
- `raw`: `off`

These options intentionally separate “show the message’s own line structure” from “apply watch-local formatting”.

## Rendering Model

### 1. Build the displayed message first

The existing watch layer already decides what text to render for:

- raw detail lines,
- human summary lines,
- failure summaries,
- runner/session markers.

That step should remain the same conceptually:

- raw view yields the current raw watch text,
- human view yields the semantic `category: message` string.

### 2. Post-process the displayed message in watch only

Introduce a small watch-local rendering pipeline:

1. take the chosen message text,
2. expand escaped multiline sequences when `--multiline escaped`,
3. split into logical display lines,
4. if `--wrap soft`, wrap each logical display line to the terminal width,
5. print the first visual line with the normal prefix,
6. print continuation lines with indentation equal to the rendered prefix width plus one separating space.

This keeps the new feature isolated from the existing semantic-extraction layer.

### 3. Prefix-aware hanging indent

The continuation indent should be calculated from the exact prefix string used for the current line:

- long prefix format:
  - `[lane=... queue=... round=... phase=... status=... failures=...]`
- short prefix format:
  - `[a2-mcp-settings q2/3 r013 p002 active f0]`

The renderer should print:

- first line: `"{prefix} {text_part_1}"`
- continuation lines: `"{' ' * (len(prefix) + 1)}{text_part_n}"`

This preserves attribution while making multiline output visually readable.

### 4. Timestamp/channel preservation in raw view

Raw view currently includes the original watch-emitted line content, for example:

```text
[15:49:23] [codex] Running command: ...
```

That content should remain part of the message body in raw mode.

If `--multiline escaped` is enabled and the raw message contains `\\n`, the expansion should occur within the message body after the watch prefix, not by generating a second watch prefix.

## Terminal Width Strategy

### Width source

Use a best-effort local terminal width query from the watch process, for example `shutil.get_terminal_size`.

### Fallback

If terminal width cannot be detected, use a conservative fallback width such as `100` or `120`.

### Wrap threshold

The effective content width should be:

- `terminal_width - len(prefix) - 1`

and should never drop below a safe minimum such as `20`.

### Non-goal

This is a rendering convenience only. The feature should not try to perfectly model every terminal’s Unicode width behavior or ANSI escape semantics.

## Escaped Sequence Policy

For the first implementation pass, only support the sequences that directly improve operator readability:

- `\\n` -> newline
- `\\t` -> normalized spaces

Do not attempt a full generic escape decoder. In particular, do not interpret arbitrary backslash sequences, ANSI escapes, or JSON-style unicode sequences unless they are already needed by real watch output.

## View Defaults

### Human view

Default behavior should be:

- `--view human`
- `--multiline escaped`
- `--wrap soft`

Rationale:

- the point of human view is readability,
- continuation alignment materially improves operator scanning,
- expanding `\\n` exposes useful structure from agent/command text.

### Raw view

Default behavior should be:

- `--view raw`
- `--multiline escaped`
- `--wrap off`

Rationale:

- raw view should still feel close to the literal log,
- escaped newline expansion is acceptable because it reveals explicit structure already encoded in the text,
- soft wrapping is useful but should be opt-in because it is a watch-local formatting choice rather than a log fact.

## Proposed Implementation Surfaces

### `templates/common/automation/_autopilot/cli_parser.py`

Add:

- `--multiline {off,escaped}`
- `--wrap {off,soft}`

with defaults chosen from the selected `--view`.

### `templates/common/automation/_autopilot/status_views.py`

Add watch-only helpers for:

- expanding escaped multiline text,
- wrapping a rendered message body to a target width,
- printing one logical rendered message as multiple visual lines with hanging indentation,
- preserving current raw/human message generation before the multiline/wrap layer is applied.

`print_watch_detail_lines(...)` should become the main integration point.

### `templates/common/automation/_autopilot/watch_runtime.py`

Thread the new watch arguments through to detail-line printing.

No controller or runtime-state logic changes should be required.

## Regression Coverage

Add scaffold-level tests that prove:

1. raw view with `multiline=escaped` expands `\\n` into continuation lines without repeating the prefix,
2. raw view with `wrap=off` leaves long single logical lines unwrapped by watch,
3. raw view with `wrap=soft` visually wraps long lines with hanging indentation,
4. human view defaults to readable multiline + wrapped output,
5. old single-line logs still render correctly,
6. continuation indentation respects both `--prefix-format short` and `--prefix-format long`.

## Non-Goals

This design does **not** aim to:

- change `progress.log` emission,
- rework health/status semantics,
- redesign the human semantic categorization rules,
- parse arbitrary ANSI/escape protocols,
- solve every terminal-width edge case,
- add a full TUI or ncurses layout layer.

## Risks and Mitigations

- **Risk: raw mode becomes too formatted**
  - Mitigation: keep soft wrapping opt-in in raw mode.

- **Risk: continuation alignment breaks for very narrow terminals**
  - Mitigation: enforce a minimum content width and fall back to unwrapped output if the available width is too small.

- **Risk: escaped sequence handling changes text unexpectedly**
  - Mitigation: only support `\\n` and `\\t` in the first pass, and scope the behavior to watch rendering only.

- **Risk: implementation tangles with semantic-summary logic**
  - Mitigation: keep multiline/wrap logic as a final rendering step after raw/human message selection.

## Success Criteria

- Operators can choose between near-raw and highly readable watch output without changing the underlying logs.
- A literal `\\n` in a watched detail message can display as a real aligned continuation line.
- Human view is easier to scan for long messages and long blocker text.
- Raw view remains trustworthy by default while still gaining useful escaped-newline rendering.
- Regression coverage proves multiline expansion and hanging-indent wrapping behavior in both prefix modes.
