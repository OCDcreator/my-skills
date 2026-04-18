# Autopilot Round Roadmap

## Queue

### [DONE] B1 - Config-driven debug job spec and platform-neutral command adapters

- **Lane**: Bugfix / backlog
- **Goal**: Replace long ad-hoc cycle command templates with a generic job spec that describes build, deploy, reload, log watch, scenario, assertions, comparison, profile, report, and state handling.
- **Priority entrypoints**:
- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/scripts/`
- `custom/obsidian-plugin-autodebug/assertions/`
- `custom/obsidian-plugin-autodebug/rules/`
- **Constraints**:
  - Keep schemas and examples plugin-agnostic
  - Support Windows PowerShell and macOS/Linux Bash quoting without plugin-specific branches
  - Avoid unrelated cleanup
- **Acceptance**:
  - A generic job spec format and runner path exist or are measurably advanced
  - Existing direct-command workflows remain documented as fallback
  - At least one Windows-style and one Bash-style dry-run/example command is documented
  - The phase doc records scope, changed files, and validation results

### [DONE] B2 - Generic view-open strategy chain and selector discovery

- **Lane**: Bugfix / backlog
- **Goal**: Add plugin-neutral ways to open a plugin surface and discover likely root selectors, headings, settings surfaces, error banners, and empty states.
- **Constraints**:
  - Prefer declared plugin metadata first, then Obsidian commands/view types, then CDP DOM heuristics
  - Do not hard-code OpenCodian selectors except in example fixtures
- **Acceptance**:
  - The strategy chain is documented and testable with a synthetic or real plugin fixture
  - Discovery output is machine-readable for downstream assertions

### [NEXT] B3 - Rich generic assertions and performance budgets

- **Lane**: Bugfix / backlog
- **Goal**: Extend assertions beyond simple DOM/log checks to cover counts, visibility, text regex, attributes, computed styles, grouped log rules, and timing budgets.
- **Constraints**:
  - Keep assertion definitions declarative JSON
  - Preserve fail/warn/expected/flaky severities
- **Acceptance**:
  - Assertion failures are summarized in diagnosis and report outputs
  - Generic examples do not require a specific plugin

### [QUEUED] B4 - Baseline taxonomy, regression comparison, and retention

- **Lane**: Bugfix / backlog
- **Goal**: Classify baselines by platform, vault state, cold/warm mode, scenario, plugin id, and run label; compare against the closest matching baseline.
- **Constraints**:
  - Keep old diagnosis/comparison files readable
  - Avoid absolute local paths in committed examples
- **Acceptance**:
  - Baseline save/list/compare flows can select by tags
  - Retention rules protect recent useful artifacts and clean stale debug output

### [QUEUED] B5 - Screenshot diff and report artifact previews

- **Lane**: Bugfix / backlog
- **Goal**: Add screenshot comparison and richer HTML report sections for UI regressions that DOM checks miss.
- **Constraints**:
  - Prefer optional dependencies or pure Node fallback behavior
  - Reports should degrade gracefully when screenshots are missing
- **Acceptance**:
  - Pixel/region diff results are recorded in diagnosis or comparison output
  - HTML reports link screenshots, DOM snapshots, logs, and diffs

### [QUEUED] B6 - Executable playbooks, doctor --fix, and state matrices

- **Lane**: Bugfix / backlog
- **Goal**: Turn diagnostic playbooks into safe command templates and add doctor/fix plus clean-state/restored-state matrix helpers.
- **Constraints**:
  - Commands must be explicit, dry-run friendly, and never destructive by default
  - Local absolute paths belong in runtime profiles, not committed defaults
- **Acceptance**:
  - Playbooks can suggest runnable next steps with safety labels
  - Doctor reports missing CLI/CDP/build/deploy prerequisites with optional fixes

### [QUEUED] B7 - Cross-platform validation checkpoint

- **Lane**: Checkpoint
- **Goal**: Run or document Windows and macOS smoke tests for shipped automation slices and decide whether to continue the backlog lane.
- **Constraints**:
  - Do not add new feature work in this checkpoint
  - Record failures as follow-up queue items instead of silently widening scope
- **Acceptance**:
  - The phase doc captures shipped slices, smoke results, remaining risks, and the stop/continue recommendation

## Current state

- The current `[NEXT]` is `B3 - Rich generic assertions and performance budgets`.
- Successful rounds must keep the roadmap and phase docs aligned.
