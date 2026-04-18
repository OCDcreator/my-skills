import path from 'node:path';
import {
  clearObsidianConsole,
  connectToCdp,
  getBooleanOption,
  getNumberOption,
  getStringOption,
  nowIso,
  parseArgs,
  setObsidianDebugFlags,
  writeTraceArtifacts,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
const host = getStringOption(options, 'host', '127.0.0.1');
const port = getNumberOption(options, 'port', 9222);
const targetUrl = getStringOption(options, 'target-url', 'app://obsidian.md/index.html');
const targetTitleContains = getStringOption(options, 'target-title-contains', '').trim();
const durationSeconds = getNumberOption(options, 'duration-seconds', 15);
const outputPath = getStringOption(options, 'output', path.resolve('.obsidian-debug/cdp-console-watch.log'));
const summaryPath = getStringOption(options, 'summary', `${outputPath}.summary.json`);
const enableDebug = getBooleanOption(options, 'enable-debug', false);
const clearConsole = getBooleanOption(options, 'clear-console', false);
const evalExpression = getStringOption(options, 'eval', '');

const lines = [];

function pushLine(kind, text) {
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

if (evalExpression) {
  const result = await session.evaluate(evalExpression);
  pushLine('control', `eval result ${JSON.stringify(result?.result?.value ?? null)}`);
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
    durationSeconds,
    outputPath,
    lineCount: lines.length,
  },
});

await session.close();
