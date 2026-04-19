module.exports = {
  default: class WdioObsidianServiceSmokePlugin {
    async onload() {
      console.log('[wdio-obsidian-service-smoke-plugin] onload');
    }

    onunload() {
      console.log('[wdio-obsidian-service-smoke-plugin] onunload');
    }
  },
};
