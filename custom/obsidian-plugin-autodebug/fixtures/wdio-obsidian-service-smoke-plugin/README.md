# WDIO Obsidian Service Smoke Plugin Fixture

This fixture demonstrates a repo-owned WebdriverIO-style `wdio-obsidian-service` lane:

- `npm run test:obsidian-wdio` points at `autodebug/ci/wdio.obsidian.conf.mjs`.
- `autodebug/ci/debug-job.sample.json` gives generated CI templates a portable dry-run job path.
- The mirrored dependency declarations stay intentionally uninstalled so doctor can explain the declared module and the runnable repo-owned script lane separately.
