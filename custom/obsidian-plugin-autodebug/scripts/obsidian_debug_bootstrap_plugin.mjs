import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import {
  ensureParentDirectory,
  getBooleanOption,
  getNumberOption,
  resolveObsidianCliCommand,
  getStringOption,
  hasHelpOption,
  nowIso,
  parseArgs,
  printHelpAndExit,
  withRefreshedWindowsPath,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
if (hasHelpOption(options)) {
  printHelpAndExit(`
Usage: node scripts/obsidian_debug_bootstrap_plugin.mjs --plugin-id <id> [options]

Required:
  --plugin-id <id>                    Plugin id to discover/enable.

Options:
  --obsidian-command <cmd>            Obsidian CLI command. Defaults to obsidian.
  --vault-name <name>                 Target vault name for CLI commands.
  --test-vault-plugin-dir <path>      Target vault plugin directory.
  --output <path>                     Bootstrap report JSON output.
  --allow-restart <true|false>        Allow restart fallback.
  --enable-plugin <true|false>        Enable after discovery.
  --skip-restrict-off true            Do not toggle restricted mode off.
`);
}

const pluginId = getStringOption(options, 'plugin-id', '').trim();
if (!pluginId) {
  throw new Error('--plugin-id is required');
}

const obsidianCommand = resolveObsidianCliCommand(
  getStringOption(options, 'obsidian-command', 'obsidian').trim() || 'obsidian',
);
const vaultName = getStringOption(options, 'vault-name', '').trim();
const testVaultPluginDir = getStringOption(options, 'test-vault-plugin-dir', '').trim();
const outputPath = getStringOption(options, 'output', '').trim();
const pollIntervalMs = Math.max(100, getNumberOption(options, 'poll-interval-ms', 1000));
const discoveryTimeoutMs = Math.max(0, getDurationMs('discovery-timeout-ms', 'discovery-timeout-seconds', 12000));
const reloadWaitMs = Math.max(0, getDurationMs('reload-wait-ms', 'reload-wait-seconds', 1500));
const restartWaitMs = Math.max(0, getDurationMs('restart-wait-ms', 'restart-wait-seconds', 8000));
const enableWaitMs = Math.max(0, getDurationMs('enable-wait-ms', 'enable-wait-seconds', 1000));
const allowRestart = getBooleanOption(options, 'allow-restart', true);
const enablePlugin = getBooleanOption(options, 'enable-plugin', true);
const skipRestrictOff = getBooleanOption(options, 'skip-restrict-off', false);

function getDurationMs(msKey, secondsKey, fallbackMs) {
  const msValue = getNumberOption(options, msKey, Number.NaN);
  if (Number.isFinite(msValue)) {
    return msValue;
  }

  const secondsValue = getNumberOption(options, secondsKey, Number.NaN);
  if (Number.isFinite(secondsValue)) {
    return secondsValue * 1000;
  }

  return fallbackMs;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function clipText(text, maxLength = 4000) {
  const normalized = String(text ?? '');
  if (normalized.length <= maxLength) {
    return normalized;
  }

  return `${normalized.slice(0, maxLength)}\n...[truncated ${normalized.length - maxLength} chars]`;
}

function pluginIdMatches(value) {
  return String(value ?? '').trim() === pluginId;
}

function parsePluginList(text) {
  try {
    const parsed = JSON.parse(String(text ?? '').replace(/^\uFEFF/, ''));
    if (Array.isArray(parsed)) {
      return {
        ok: true,
        plugins: parsed
          .map((entry) => ({
            id: typeof entry === 'string' ? entry : String(entry?.id ?? ''),
            version: typeof entry === 'object' && entry ? entry.version ?? null : null,
          }))
          .filter((entry) => entry.id.length > 0),
      };
    }
  } catch {
    // Fall back to line parsing below.
  }

  const plugins = String(text ?? '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.toLowerCase().startsWith('error:'))
    .map((line) => ({
      id: line.split(/\s+/)[0],
      version: null,
    }))
    .filter((entry) => entry.id.length > 0);

  return {
    ok: plugins.length > 0,
    plugins,
  };
}

function cliArgs(command, args = []) {
  const resolvedArgs = [];
  if (vaultName) {
    resolvedArgs.push(`vault=${vaultName}`);
  }
  resolvedArgs.push(command, ...args);
  return resolvedArgs;
}

function runCli(command, args = [], timeoutMs = 15000) {
  const resolvedArgs = cliArgs(command, args);
  const startedAt = nowIso();

  return new Promise((resolve) => {
    const child = spawn(obsidianCommand, resolvedArgs, {
      env: withRefreshedWindowsPath(),
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    let settled = false;
    const timeout = setTimeout(() => {
      if (!settled) {
        settled = true;
        child.kill();
        resolve({
          command,
          args: resolvedArgs,
          startedAt,
          finishedAt: nowIso(),
          ok: false,
          exitCode: null,
          timedOut: true,
          stdout: clipText(stdout),
          stderr: clipText(stderr),
          text: clipText(`${stdout}\n${stderr}`.trim()),
        });
      }
    }, timeoutMs);

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    child.on('error', (error) => {
      if (!settled) {
        settled = true;
        clearTimeout(timeout);
        resolve({
          command,
          args: resolvedArgs,
          startedAt,
          finishedAt: nowIso(),
          ok: false,
          exitCode: null,
          timedOut: false,
          stdout: clipText(stdout),
          stderr: clipText(`${stderr}${error.message}`),
          text: clipText(`${stdout}\n${stderr}${error.message}`.trim()),
        });
      }
    });
    child.on('close', (code) => {
      if (!settled) {
        settled = true;
        clearTimeout(timeout);
        resolve({
          command,
          args: resolvedArgs,
          startedAt,
          finishedAt: nowIso(),
          ok: code === 0,
          exitCode: code,
          timedOut: false,
          stdout: clipText(stdout),
          stderr: clipText(stderr),
          text: clipText(`${stdout}\n${stderr}`.trim()),
        });
      }
    });
  });
}

async function readVaultManifest() {
  if (!testVaultPluginDir) {
    return null;
  }

  try {
    const manifestPath = path.join(path.resolve(testVaultPluginDir), 'manifest.json');
    const manifest = JSON.parse((await fs.readFile(manifestPath, 'utf8')).replace(/^\uFEFF/, ''));
    return {
      path: manifestPath,
      id: manifest.id ?? null,
      version: manifest.version ?? null,
      matchesPluginId: manifest.id === pluginId,
    };
  } catch (error) {
    return {
      path: path.join(path.resolve(testVaultPluginDir), 'manifest.json'),
      error: error.message,
      matchesPluginId: false,
    };
  }
}

async function getPluginState(label) {
  const installedResult = await runCli('plugins', ['filter=community', 'versions', 'format=json']);
  const installed = parsePluginList(installedResult.stdout || installedResult.text);
  const enabledResult = await runCli('plugins:enabled', ['filter=community', 'versions', 'format=json']);
  const enabled = parsePluginList(enabledResult.stdout || enabledResult.text);
  const installedEntry = installed.plugins.find((entry) => pluginIdMatches(entry.id)) ?? null;
  const enabledEntry = enabled.plugins.find((entry) => pluginIdMatches(entry.id)) ?? null;

  return {
    label,
    checkedAt: nowIso(),
    discovered: Boolean(installedEntry),
    enabled: Boolean(enabledEntry),
    installedEntry,
    enabledEntry,
    installedParseOk: installed.ok,
    enabledParseOk: enabled.ok,
    installedCommand: installedResult,
    enabledCommand: enabledResult,
  };
}

async function pollForDiscovery(label, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastState = null;

  while (true) {
    lastState = await getPluginState(label);
    report.polls.push({
      label,
      checkedAt: lastState.checkedAt,
      discovered: lastState.discovered,
      enabled: lastState.enabled,
      installedParseOk: lastState.installedParseOk,
      enabledParseOk: lastState.enabledParseOk,
    });

    if (lastState.discovered || Date.now() >= deadline) {
      return lastState;
    }

    await sleep(pollIntervalMs);
  }
}

function addStep(name, result, detail, data = {}) {
  report.steps.push({
    name,
    status: result?.ok === false ? 'warn' : 'pass',
    detail,
    result: result
      ? {
          args: result.args,
          exitCode: result.exitCode,
          timedOut: result.timedOut,
          stdout: result.stdout,
          stderr: result.stderr,
        }
      : null,
    ...data,
  });
}

const report = {
  generatedAt: nowIso(),
  status: 'pending',
  pluginId,
  vaultName: vaultName || null,
  obsidianCommand,
  testVaultPluginDir: testVaultPluginDir ? path.resolve(testVaultPluginDir) : null,
  options: {
    pollIntervalMs,
    discoveryTimeoutMs,
    reloadWaitMs,
    restartWaitMs,
    enableWaitMs,
    allowRestart,
    enablePlugin,
    skipRestrictOff,
  },
  vaultManifest: await readVaultManifest(),
  steps: [],
  polls: [],
  initialState: null,
  finalState: null,
  actions: {
    restrictedModeDisabled: false,
    vaultReloaded: false,
    appRestarted: false,
    pluginEnabled: false,
  },
};

if (!skipRestrictOff) {
  const restrictResult = await runCli('plugins:restrict', ['off']);
  report.actions.restrictedModeDisabled = restrictResult.ok;
  addStep('plugins-restrict-off', restrictResult, 'Disable restricted mode so community plugins can load.');
}

report.initialState = await getPluginState('initial');
let state = report.initialState;

if (!state.discovered) {
  const reloadResult = await runCli('reload');
  report.actions.vaultReloaded = reloadResult.ok;
  addStep('vault-reload', reloadResult, 'Reload the target vault so Obsidian discovers newly copied community plugin files.');
  if (reloadWaitMs > 0) {
    await sleep(reloadWaitMs);
  }
  state = await pollForDiscovery('after-vault-reload', discoveryTimeoutMs);
}

if (!state.discovered && allowRestart) {
  const restartResult = await runCli('restart', [], 20000);
  report.actions.appRestarted = restartResult.ok;
  addStep('app-restart', restartResult, 'Restart Obsidian as a fallback when vault reload did not discover the plugin.');
  if (restartWaitMs > 0) {
    await sleep(restartWaitMs);
  }
  state = await pollForDiscovery('after-app-restart', discoveryTimeoutMs);
}

if (state.discovered && enablePlugin && !state.enabled) {
  const enableResult = await runCli('plugin:enable', [`id=${pluginId}`]);
  report.actions.pluginEnabled = enableResult.ok;
  addStep('plugin-enable', enableResult, 'Enable the discovered community plugin before reload/log capture.');
  if (enableWaitMs > 0) {
    await sleep(enableWaitMs);
  }
  state = await getPluginState('after-enable');
}

report.finalState = {
  label: state.label,
  checkedAt: state.checkedAt,
  discovered: state.discovered,
  enabled: state.enabled,
  installedEntry: state.installedEntry,
  enabledEntry: state.enabledEntry,
  installedParseOk: state.installedParseOk,
  enabledParseOk: state.enabledParseOk,
};
report.status = state.discovered && (!enablePlugin || state.enabled) ? 'pass' : 'fail';
report.detail = report.status === 'pass'
  ? `${pluginId} is discoverable${enablePlugin ? ' and enabled' : ''}.`
  : `${pluginId} was not discoverable${enablePlugin ? ' or could not be enabled' : ''} after bootstrap.`;

if (outputPath) {
  const resolvedOutputPath = path.resolve(outputPath);
  await ensureParentDirectory(resolvedOutputPath);
  await fs.writeFile(resolvedOutputPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
}

console.log(JSON.stringify(report, null, 2));

if (report.status !== 'pass') {
  process.exitCode = 1;
}
