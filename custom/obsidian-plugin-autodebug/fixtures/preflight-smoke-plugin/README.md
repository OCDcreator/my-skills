# Preflight Smoke Plugin Fixture

This fixture is intentionally configured with reusable pre-build gates:

- `npm run lint` runs `scripts/check-manifest-residue.mjs` to catch manifest template residue before a build.
- `npm run validate:plugin-entry` runs `scripts/validate-plugin-entry.mjs` to catch ReviewBot-style plugin-entry residue before a build.
- `npm run build` is a harmless placeholder that should only run after both preflight gates pass.

The committed `manifest.json` and `reviewbot-plugin-entry.json` intentionally contain `{{...}}` placeholders so validation commands can prove that manifest and submission-template residue is caught before generated CI templates reach the build step.
