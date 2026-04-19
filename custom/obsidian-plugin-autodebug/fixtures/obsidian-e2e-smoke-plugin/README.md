# Obsidian E2E Smoke Plugin Fixture

This fixture demonstrates a repo-owned Vitest-style `obsidian-e2e` lane:

- `npm run test:obsidian-e2e` points at `autodebug/ci/obsidian-e2e.vitest.config.mjs`.
- `autodebug/ci/debug-job.sample.json` keeps generated CI dry-runs portable.
- The mirrored dependency declarations stay intentionally uninstalled so doctor can report declared modules separately from the runnable repo-owned script lane.
