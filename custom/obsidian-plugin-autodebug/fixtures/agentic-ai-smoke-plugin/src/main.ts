import { Plugin, requestUrl } from 'obsidian';

interface AgenticAiSmokeSettings {
  apiKey: string;
  enableNetworkRequests: boolean;
  privacyNoticeAccepted: boolean;
}

const DEFAULT_SETTINGS: AgenticAiSmokeSettings = {
  apiKey: '',
  enableNetworkRequests: false,
  privacyNoticeAccepted: false,
};

function redactDiagnostic(value: string) {
  return value
    .replace(/sk-[a-z0-9_-]{8,}/gi, '[REDACTED_API_KEY]')
    .replace(/Authorization:\s*Bearer\s+\S+/gi, 'Authorization: Bearer [REDACTED]');
}

export default class AgenticAiSmokePlugin extends Plugin {
  settings = DEFAULT_SETTINGS;

  async onload() {
    const storedKey = await this.app.secretStorage.get('agentic-ai-smoke-api-key');
    if (storedKey && this.settings.enableNetworkRequests && this.settings.privacyNoticeAccepted) {
      await requestUrl({
        url: 'https://api.openai.example.invalid/v1/models',
        headers: {
          Authorization: `Bearer ${storedKey}`,
        },
      });
    }

    console.debug(redactDiagnostic(`Authorization: Bearer ${storedKey ?? 'sk-fixture-secret'}`));
  }
}
