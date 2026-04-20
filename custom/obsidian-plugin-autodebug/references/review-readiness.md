# Review Readiness (Optional Heuristics)

This guide is an optional pre-submit gate for plugin teams. It helps catch obvious issues before runtime smoke results are treated as release-ready.

Important boundary:

- These are compact heuristics, not official acceptance criteria.
- Final decisions still come from Obsidian's real review process.

## Heuristic Checklist

- Manifest basics: verify stable `id`, `name`, `version`, `minAppVersion`, and a clear description.
- Sample residue: remove placeholder sample-plugin text, commands, settings, and demo naming leftovers.
- Logging discipline: avoid noisy `console.log` in production paths unless debug-gated.
- DOM safety: avoid unsafe HTML insertion patterns unless fully sanitized.
- Network/privacy clarity: document external requests/telemetry behavior and provide user-facing controls where relevant.
- Secret handling: prefer Obsidian secret-storage APIs over plaintext settings for tokens/keys.

## Upstream References

- Obsidian self-critique checklist: <https://docs.obsidian.md/oo/plugin>
- Plugin guidelines: <https://docs.obsidian.md/Plugins/Releasing/Plugin+guidelines>
- Submit your plugin: <https://docs.obsidian.md/Plugins/Releasing/Submit+your+plugin>
- TypeScript API (requestUrl): <https://docs.obsidian.md/Reference/TypeScript+API/requestUrl>
- TypeScript API (SecretStorage): <https://docs.obsidian.md/Reference/TypeScript+API/SecretStorage>
- Official ESLint plugin: <https://github.com/obsidianmd/eslint-plugin>
- Developer docs source repo: <https://github.com/obsidianmd/obsidian-developer-docs>
