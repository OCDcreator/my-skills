# Adoption Checklist

Use this checklist when adding or improving debug logging in an Obsidian plugin repository.

## Explore First

- Read applicable `AGENTS.md` / project rules.
- Confirm plugin shape: `manifest.json`, `package.json`, entrypoint, build config.
- Search for existing logger, direct `console.*`, debug flags, settings UI, diagnostic report, `BUILD_ID`.
- Identify current version/build identity flow.
- Identify current settings persistence and migration patterns.
- Identify platform assumptions in paths and UI copy.
- Identify every module/scope that emits `info/debug`, especially polling/streaming/resize/progress paths.
- Identify whether high-frequency logs already have a shared throttle helper or only ad-hoc constants.

## Gap Analysis

Write a short comparison before editing:

- Keep: existing useful logger helpers, version labels, settings controls, report fields.
- Improve: noisy levels, missing report fields, missing buffer clear/export, missing module toggles, missing refresh-rate controls, platform handling.
- Remove or migrate: direct ad-hoc `console.log`, always-visible info spam, unbounded logs, secrets in logs.

## Implement

- Add or retrofit shared logger core.
- Replace scattered direct console calls with scoped logger calls, except build scripts or intentional CLI output.
- Add `always` level for startup identity only.
- Make `info/debug` quiet by default.
- Add a single module registry that drives logger `moduleKey`, settings toggles, and tests.
- Add per-module debug toggles for every subsystem that emits optional logs.
- Add bounded recent log buffer and `clearRecentLogs()`.
- Add duplicate payload suppression and high-frequency throttling helpers where needed.
- Add a settings-backed debug refresh interval for high-frequency logs; avoid hard-coded-only throttle intervals.
- Add diagnostic report builder with build/environment/settings/runtime/recent logs.
- Add copy diagnostics and export diagnostics actions.
- Add Windows/macOS platform path settings and console help.
- Add `BUILD_ID` to startup log and diagnostic report.
- Redact sensitive fields and truncate long payloads.

## Test

- Unit test logger level gating.
- Unit test global debug toggle + module toggle gating together.
- Unit test every module registry item has a persisted setting value and a rendered settings control.
- Unit test recent buffer limit and clear behavior.
- Unit test duplicate suppression if implemented.
- Unit test settings-backed refresh interval changes throttle behavior for high-frequency logs.
- Unit test diagnostic report includes version, `BUILD_ID`, platform, vault, recent logs.
- Unit test platform path key selection if the project has tests.
- Run the smallest relevant typecheck/build command.
- In Obsidian, verify startup first log line and settings page actions when runtime behavior changes.

## Document

- Update module docs if the repository has docs for `src/shared/logger.ts` or settings.
- Update `AGENTS.md` only if the project uses it for deployment/debug workflow rules.
- Document the default quiet policy and how users export diagnostics.

## Avoid

- Do not add background disk logging by default.
- Do not store unbounded logs in plugin data.
- Do not log full prompts, full model outputs, full file contents, tokens, secrets, or binary payloads.
- Do not merge macOS into a generic `unix` path key when Windows/macOS support is required.
- Do not make `info` always-visible in a user-facing plugin unless the project explicitly accepts noisy logs.
- Do not add new module scopes without adding them to the module registry, settings UI, and the mapping tests in the same change.
