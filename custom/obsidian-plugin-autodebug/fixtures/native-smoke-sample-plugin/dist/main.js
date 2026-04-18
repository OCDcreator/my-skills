const obsidian = require('obsidian');

class NativeSmokeSamplePlugin extends obsidian.Plugin {
  async onload() {
    console.log('[native-smoke-sample] onload');
    this.addCommand({
      id: 'native-smoke-sample-ping',
      name: 'Native Smoke Sample Ping',
      callback: () => {
        console.log('[native-smoke-sample] command');
      },
    });
  }

  onunload() {
    console.log('[native-smoke-sample] onunload');
  }
}

module.exports = {
  default: NativeSmokeSamplePlugin,
};
