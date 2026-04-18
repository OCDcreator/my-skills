import path from 'node:path';
import {
  clearObsidianConsole,
  connectToCdp,
  getBooleanOption,
  getNumberOption,
  getStringOption,
  nowIso,
  parseArgs,
  reloadPluginViaApp,
  setObsidianDebugFlags,
  writeTraceArtifacts,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
const pluginId = getStringOption(options, 'plugin-id');
if (!pluginId) {
  throw new Error('--plugin-id is required');
}

const host = getStringOption(options, 'host', '127.0.0.1');
const port = getNumberOption(options, 'port', 9222);
const targetUrl = getStringOption(options, 'target-url', 'app://obsidian.md/index.html');
const targetTitleContains = getStringOption(options, 'target-title-contains', '').trim();
const durationSeconds = getNumberOption(options, 'duration-seconds', 15);
const reloadDelayMs = getNumberOption(options, 'reload-delay-ms', 800);
const evalAfterReload = getStringOption(options, 'eval-after-reload', '');
const outputPath = getStringOption(options, 'output', path.resolve('.obsidian-debug/cdp-reload-trace.log'));
const summaryPath = getStringOption(options, 'summary', `${outputPath}.summary.json`);
const enableDebug = getBooleanOption(options, 'enable-debug', true);
const clearConsole = getBooleanOption(options, 'clear-console', true);
const skipReload = getBooleanOption(options, 'skip-reload', false);

const lines = [];
let recording = false;

function pushLine(kind, text) {
  if (!recording && !kind.startsWith('control')) {
    return;
  }

  const line = `${nowIso()} [${kind}] ${text}`;
  lines.push(line);
  console.log(line);
}

const session = await connectToCdp({
  host,
  port,
  targetUrl,
  targetTitleContains,
  onLine: pushLine,
});

pushLine('control', `connected to ${session.target.title} (${session.target.url})`);

if (enableDebug) {
  const result = await setObsidianDebugFlags(session);
  pushLine('control', `debug flags enabled ${JSON.stringify(result?.result?.value ?? {})}`);
}

if (clearConsole) {
  await clearObsidianConsole(session);
  pushLine('control', 'console cleared');
}

recording = true;

let reloadResult = null;
if (!skipReload) {
  reloadResult = await reloadPluginViaApp(session, pluginId, reloadDelayMs);
  pushLine('control', `plugin reload ${JSON.stringify(reloadResult?.result?.value ?? null)}`);
}

if (evalAfterReload) {
  const evalResult = await session.evaluate(evalAfterReload);
  pushLine('control', `eval-after-reload ${JSON.stringify(evalResult?.result?.value ?? null)}`);
}

await new Promise((resolve) => setTimeout(resolve, Math.max(0, durationSeconds) * 1000));

await writeTraceArtifacts({
  outputPath,
  summaryPath,
  lines,
  summary: {
    capturedAt: nowIso(),
    host,
    port,
    targetUrl,
    targetTitleContains,
    pluginId,
    durationSeconds,
    reloadDelayMs,
    evalAfterReload: evalAfterReload || null,
    outputPath,
    lineCount: lines.length,
    reloadResult: reloadResult?.result?.value ?? null,
  },
});

await session.close();
