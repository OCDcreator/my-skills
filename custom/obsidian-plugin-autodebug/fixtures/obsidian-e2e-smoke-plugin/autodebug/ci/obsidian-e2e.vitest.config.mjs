export default {
  test: {
    name: 'obsidian-e2e-smoke',
    include: [],
    environment: 'node',
  },
  obsidianE2E: {
    pluginId: 'obsidian-e2e-smoke-plugin',
    vaultPath: 'test-vault',
  },
};
