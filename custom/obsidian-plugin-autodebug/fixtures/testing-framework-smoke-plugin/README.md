# Testing Framework Smoke Plugin Fixture

This fixture demonstrates a repo-owned `obsidian-testing-framework` lane without hard-coding machine-local paths:

- `npm run test:obsidian` points at `autodebug/ci/obsidian-testing-framework.config.mjs`.
- `autodebug/ci/debug-job.sample.json` gives generated CI templates a portable dry-run job path.
- The dependency stays intentionally uninstalled in this mirrored fixture so doctor can distinguish declared modules from runnable repo-owned adapter wiring.
