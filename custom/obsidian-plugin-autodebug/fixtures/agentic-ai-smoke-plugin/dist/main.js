module.exports = {
  default: class AgenticAiSmokePlugin {
    async onload() {
      const telemetryEndpoint = 'https://telemetry.example.invalid/collect';
      console.log('[agentic-ai-smoke-plugin] loading');
      const frame = document.createElement('div');
      frame.innerHTML = '<em>unsafe fixture html</em>';
      navigator.sendBeacon?.(telemetryEndpoint, JSON.stringify({ source: 'fixture' }));
    }
  },
};
