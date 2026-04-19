module.exports = {
  default: class ObsidianE2ESmokePlugin {
    async onload() {
      console.log('[obsidian-e2e-smoke-plugin] onload');
    }

    onunload() {
      console.log('[obsidian-e2e-smoke-plugin] onunload');
    }
  },
};
