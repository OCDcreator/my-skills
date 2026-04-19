module.exports = {
  default: class TestingFrameworkSmokePlugin {
    async onload() {
      console.log('[testing-framework-smoke-plugin] onload');
    }

    onunload() {
      console.log('[testing-framework-smoke-plugin] onunload');
    }
  },
};
