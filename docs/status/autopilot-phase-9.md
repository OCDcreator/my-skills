# Autopilot Phase 9: B9 Native macOS Smoke Host Validation

> **Status**: [DONE]
> **Attempt**: 9
> **Preset**: Checkpoint follow-up
> **Repository**: `my-skills`
> **Date**: 2026-04-18

## Scope

- Executed the queued `[NEXT]` slice: `B9 - Native macOS smoke host validation`.
- Used the real Mac Mini host at `192.168.31.215` with macOS `26.3.2`, Node.js `25.6.1`, Obsidian `1.12.7`, and the installed `obsidian` CLI.
- Synced the generic `custom/obsidian-plugin-autodebug` tooling to `~/tmp/obsidian-autodebug-b9` and ran native Bash/CDP smoke commands against the Mac `testvault`.
- Added a committed plugin-neutral native smoke fixture because the old synthetic `.tmp-skills` fixture copied files but was not a loadable Obsidian community plugin.
- Added a CDP reload assertion so `diagnosis.json` now fails when `reloadResult.loaded` is false instead of claiming success from deploy/screenshot/DOM alone.
- Documented the first-deploy nuance: after copying a brand-new plugin into a fresh vault, reload the vault or restart Obsidian once so Obsidian discovers the plugin before expecting reload assertions to pass.

## Changed Files

- `README.md`
- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs`
- `custom/obsidian-plugin-autodebug/fixtures/native-smoke-sample-plugin/manifest.json`
- `custom/obsidian-plugin-autodebug/fixtures/native-smoke-sample-plugin/package.json`
- `custom/obsidian-plugin-autodebug/fixtures/native-smoke-sample-plugin/dist/main.js`
- `custom/obsidian-plugin-autodebug/fixtures/native-smoke-sample-plugin/dist/manifest.json`
- `custom/obsidian-plugin-autodebug/fixtures/native-smoke-sample-plugin/dist/styles.css`
- `docs/status/autopilot-round-roadmap.md`
- `docs/status/autopilot-phase-9.md`

## Native macOS Smoke Results

- **Host preflight**: `ssh dht@192.168.31.215 "uname -a; sw_vers; command -v node; node -v; command -v obsidian; obsidian help"` confirmed macOS, Node.js, Obsidian app, and developer CLI commands.
- **CDP launch**: `bash custom/obsidian-plugin-autodebug/scripts/obsidian_mac_restart_cdp.sh /Applications/Obsidian.app 9222 25` started Obsidian with CDP; `/json/list` exposed the `testvault` page target.
- **Doctor/fix flow**: native doctor first reported the expected missing fresh fixture install, generated `doctor-fixes.sh`, then passed after the generated fix copied fixture artifacts into the test vault.
- **Fresh-plugin discovery**: after first deploy, `obsidian vault=testvault reload` / app restart made `native-smoke-sample-plugin` visible to Obsidian; this is now documented as a first-install requirement.
- **Bash job/cycle**: `obsidian_debug_job.mjs --platform bash --mode run` deployed the native fixture, reloaded it over CDP, captured CDP trace/screenshot/DOM, and generated HTML report output.
- **Reload evidence**: CDP trace contains `[native-smoke-sample] onload` and `plugin reload {"ok":true,"loaded":true}`; `diagnosis.json` reported 5/5 passing assertions including `plugin-reload-loaded`.
- **State matrix**: `obsidian_debug_state_matrix.mjs --platform bash --mode run` passed both `clean-state` and `restored-state`; each inner diagnosis reported 5/5 passing assertions including `plugin-reload-loaded`.

## Validation Results

- `node --check custom\obsidian-plugin-autodebug\scripts\obsidian_debug_analyze.mjs` — passed.
- `ssh dht@192.168.31.215 "bash custom/obsidian-plugin-autodebug/scripts/obsidian_mac_restart_cdp.sh /Applications/Obsidian.app 9222 25"` — passed.
- `ssh dht@192.168.31.215 "node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs --repo-dir custom/obsidian-plugin-autodebug/fixtures/native-smoke-sample-plugin --test-vault-plugin-dir /Volumes/SDD2T/obsidian-vault-write/testvault/.obsidian/plugins/native-smoke-sample-plugin --plugin-id native-smoke-sample-plugin --obsidian-command obsidian --platform bash --cdp-host 127.0.0.1 --cdp-port 9222 --cdp-target-title-contains testvault --fix --output .tmp-skills/autopilot-b9-macos/doctor-native-fixture.json"` — expected initial fail for missing fresh test-vault plugin directory; generated `doctor-fixes.sh`.
- `ssh dht@192.168.31.215 "bash .tmp-skills/autopilot-b9-macos/doctor-fixes.sh; node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs --repo-dir custom/obsidian-plugin-autodebug/fixtures/native-smoke-sample-plugin --test-vault-plugin-dir /Volumes/SDD2T/obsidian-vault-write/testvault/.obsidian/plugins/native-smoke-sample-plugin --plugin-id native-smoke-sample-plugin --obsidian-command obsidian --platform bash --cdp-host 127.0.0.1 --cdp-port 9222 --cdp-target-title-contains testvault --output .tmp-skills/autopilot-b9-macos/doctor-native-fixture-after-fix.json"` — passed.
- `ssh dht@192.168.31.215 "obsidian vault=testvault reload"` plus Obsidian CDP restart — passed; the fixture plugin became discoverable before reload assertions.
- `ssh dht@192.168.31.215 "node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job .tmp-skills/autopilot-b9-macos/b9-native-fixture-job.json --platform bash --mode run --output .tmp-skills/autopilot-b9-macos/job-native-fixture-run-after-reload.json"` — passed; `diagnosis.json` had 5/5 passing assertions and no blocking failures.
- `ssh dht@192.168.31.215 "node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_state_matrix.mjs --job .tmp-skills/autopilot-b9-macos/b9-native-fixture-matrix-job.json --state-plan .tmp-skills/autopilot-b7/b7-state-plan.json --vault-root /Volumes/SDD2T/obsidian-vault-write/testvault --plugin-id native-smoke-sample-plugin --platform bash --mode run --output-root .tmp-skills/autopilot-b9-macos/native-fixture-state-matrix --output .tmp-skills/autopilot-b9-macos/native-fixture-state-matrix.json"` — passed; `clean-state` and `restored-state` both exited 0.
- Local artifact pullback to `.tmp-skills/autopilot-b9-macos/` — passed; artifacts are gitignored and not committed.

## Remaining Risks

- The Mac `testvault` is a shared user test vault with `opencodian` and `obsidian-bookshelf` enabled, so native CDP traces include unrelated `opencodian` `session-sync-404` warning signatures. The native fixture assertions still pass with no blocking failures.
- A pristine hosted macOS CI runner with Node.js 20 may still lack `globalThis.WebSocket`; this phase validated the real Mac Mini with Node.js 25.6.1. Add a new queued slice if hosted CI compatibility must be guaranteed.
- First-time fixture installation needs one vault reload or app restart after the initial deploy so Obsidian discovers the new community plugin. Existing plugin development loops, where the plugin is already discovered, do not need that bootstrap step.

## Configured Validation Gaps

- Lint: blank in round metadata; not run.
- Typecheck: blank in round metadata; not run.
- Full test: blank in round metadata; not run.
- Build: blank in round metadata; not run.
- Vulture: blank in round metadata; not run.

## Vulture Findings

- Vulture was not configured for this round, so no dead-code observability command was run.

## Next Recommended Slice

- No mandatory next slice remains in the current roadmap.
- Optional future backlog: add a clean-vault/bootstrap runner and a WebSocket-runtime doctor check if hosted macOS CI or fresh-vault zero-touch smoke runs become required.
