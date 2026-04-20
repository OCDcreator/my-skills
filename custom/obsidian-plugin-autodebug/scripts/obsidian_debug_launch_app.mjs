#!/usr/bin/env node
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import {
  ensureParentDirectory,
  getNumberOption,
  getStringOption,
  hasHelpOption,
  nowIso,
  parseArgs,
  printHelpAndExit,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
if (hasHelpOption(options)) {
  printHelpAndExit(`
Usage: node scripts/obsidian_debug_launch_app.mjs [options]

Options:
  --mode <auto|cli|cdp>              Readiness probe to require. Defaults to auto.
  --obsidian-command <command>       Obsidian CLI/app command. Defaults to obsidian.
  --app-path <path>                  Optional desktop app/executable path.
  --vault-name <name>                Vault name to open or focus.
  --vault-path <path>                Vault/file path for obsidian://open?path=...
  --vault-uri <uri>                  Explicit obsidian:// URI to open.
  --cdp-host <host> --cdp-port <n>   CDP endpoint. Defaults to 127.0.0.1:9222.
  --target-title-contains <text>     Optional CDP target title filter.
  --wait-ms <n>                      Total wait after launch. Defaults to 20000.
  --poll-interval-ms <n>             Probe interval. Defaults to 1000.
  --output <path>                    Optional JSON launch report.
`);
}

const mode = getStringOption(options, 'mode', 'auto').trim().toLowerCase();
if (!['auto', 'cli', 'cdp'].includes(mode)) {
  throw new Error('--mode must be auto, cli, or cdp');
}

const obsidianCommand = getStringOption(options, 'obsidian-command', 'obsidian').trim() || 'obsidian';
const appPath = getStringOption(options, 'app-path', '').trim();
const vaultName = getStringOption(options, 'vault-name', '').trim();
const vaultPath = getStringOption(options, 'vault-path', '').trim();
const vaultUri = getStringOption(options, 'vault-uri', '').trim();
const cdpHost = getStringOption(options, 'cdp-host', '127.0.0.1').trim() || '127.0.0.1';
const cdpPort = getNumberOption(options, 'cdp-port', 9222);
const targetTitleContains = getStringOption(options, 'target-title-contains', '').trim();
const waitMs = Math.max(0, getNumberOption(options, 'wait-ms', 20000));
const pollIntervalMs = Math.max(100, getNumberOption(options, 'poll-interval-ms', 1000));
const outputPath = getStringOption(options, 'output', '').trim();
const startedAt = Date.now();

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function describeError(error) {
  return error?.message ? String(error.message) : String(error);
}

async function exists(filePath) {
  if (!filePath) {
    return false;
  }
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

function runProcess(command, args = [], timeoutMs = 5000) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
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
        resolve({ ok: false, exitCode: null, stdout, stderr, timedOut: true });
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
        resolve({ ok: false, exitCode: null, stdout, stderr: `${stderr}${describeError(error)}`, timedOut: false });
      }
    });
    child.on('close', (code) => {
      if (!settled) {
        settled = true;
        clearTimeout(timeout);
        resolve({ ok: code === 0, exitCode: code, stdout, stderr, timedOut: false });
      }
    });
  });
}

function spawnAndForget(command, args = [], { detached = true } = {}) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      detached,
      windowsHide: true,
      stdio: 'ignore',
    });
    let settled = false;
    const finish = (result) => {
      if (!settled) {
        settled = true;
        resolve(result);
      }
    };
    child.on('error', (error) => finish({ ok: false, detail: describeError(error), command, args }));
    if (detached) {
      child.once('spawn', () => {
        child.unref();
        finish({ ok: true, detail: 'spawned', command, args });
      });
      return;
    }
    child.on('close', (code) => finish({ ok: code === 0, exitCode: code, command, args }));
  });
}

function buildVaultScopedArgs(command, args = []) {
  return [
    ...(vaultName ? [`vault=${vaultName}`] : []),
    command,
    ...args,
  ];
}

function buildVaultUri() {
  if (vaultUri) {
    return vaultUri;
  }
  if (vaultName) {
    return `obsidian://open?vault=${encodeURIComponent(vaultName)}`;
  }
  if (vaultPath) {
    return `obsidian://open?path=${encodeURIComponent(path.resolve(vaultPath))}`;
  }
  return '';
}

async function defaultWindowsAppPath() {
  const candidates = [
    appPath,
    obsidianCommand.toLowerCase().endsWith('.com')
      ? `${obsidianCommand.slice(0, -4)}.exe`
      : '',
    obsidianCommand,
    'C:\\Program Files\\Obsidian\\Obsidian.exe',
    path.join(process.env.LOCALAPPDATA ?? '', 'Obsidian', 'Obsidian.exe'),
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (await exists(candidate)) {
      return candidate;
    }
  }
  return appPath || '';
}

async function defaultMacAppPath() {
  const candidates = [
    appPath,
    '/Applications/Obsidian.app',
    path.join(os.homedir(), 'Applications', 'Obsidian.app'),
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (await exists(candidate)) {
      return candidate;
    }
  }
  return appPath || '/Applications/Obsidian.app';
}

async function probeCli() {
  const result = await runProcess(obsidianCommand, buildVaultScopedArgs('help'), 7000);
  const text = `${result.stdout}\n${result.stderr}`;
  const hasDeveloperCommands = text.includes('Developer:') || text.includes('dev:console');
  return {
    ok: result.ok && hasDeveloperCommands,
    channel: 'cli',
    detail: result.ok
      ? hasDeveloperCommands
        ? 'Obsidian CLI is reachable with developer commands.'
        : 'Obsidian command responded, but developer commands were not visible.'
      : result.timedOut
        ? 'Obsidian CLI help timed out.'
        : `Obsidian CLI help failed: ${result.stderr.trim() || result.stdout.trim() || 'no output'}`,
    exitCode: result.exitCode,
    timedOut: result.timedOut,
  };
}

async function probeCdp() {
  try {
    const response = await fetch(`http://${cdpHost}:${cdpPort}/json/list`);
    if (!response.ok) {
      return {
        ok: false,
        channel: 'cdp',
        detail: `CDP endpoint returned HTTP ${response.status}.`,
      };
    }
    const targets = await response.json();
    const target = Array.isArray(targets)
      ? targets.find((entry) => {
          const title = String(entry?.title ?? '');
          const url = String(entry?.url ?? '');
          const titleMatches = !targetTitleContains || title.includes(targetTitleContains);
          return titleMatches && (url.includes('app://obsidian.md') || title.toLowerCase().includes('obsidian'));
        }) ?? targets[0]
      : null;
    return {
      ok: Boolean(target),
      channel: 'cdp',
      detail: target
        ? `CDP target is reachable: ${target.title || target.url || '(untitled target)'}`
        : 'CDP endpoint responded but no Obsidian target was found.',
      target: target
        ? {
            title: target.title ?? null,
            url: target.url ?? null,
          }
        : null,
    };
  } catch (error) {
    return {
      ok: false,
      channel: 'cdp',
      detail: `CDP probe failed: ${describeError(error)}`,
    };
  }
}

async function probeReadiness() {
  const probes = [];
  if (mode === 'cli' || mode === 'auto') {
    probes.push(await probeCli());
  }
  if (mode === 'cdp' || mode === 'auto') {
    probes.push(await probeCdp());
  }
  return {
    ok: probes.some((entry) => entry.ok),
    probes,
  };
}

async function launchWindows(uri) {
  const steps = [];
  const resolvedAppPath = await defaultWindowsAppPath();
  if (mode === 'cdp' && resolvedAppPath) {
    steps.push(await spawnAndForget(resolvedAppPath, [`--remote-debugging-port=${cdpPort}`]));
  }
  if (uri) {
    steps.push(await spawnAndForget('cmd', ['/c', 'start', '', uri], { detached: false }));
  } else if (resolvedAppPath) {
    steps.push(await spawnAndForget(resolvedAppPath, mode === 'cdp' ? [`--remote-debugging-port=${cdpPort}`] : []));
  } else {
    steps.push({ ok: false, detail: 'No Obsidian app path or vault URI was available to launch.' });
  }
  return steps;
}

async function launchMac(uri) {
  const steps = [];
  const resolvedAppPath = await defaultMacAppPath();
  const openArgs = [mode === 'cdp' ? '-na' : '-a', resolvedAppPath];
  if (mode === 'cdp') {
    openArgs.push('--args', `--remote-debugging-port=${cdpPort}`);
  }
  steps.push(await spawnAndForget('open', openArgs, { detached: false }));
  if (uri) {
    await sleep(500);
    steps.push(await spawnAndForget('open', [uri], { detached: false }));
  }
  return steps;
}

async function launchLinux(uri) {
  const steps = [];
  if (mode === 'cdp') {
    steps.push(await spawnAndForget(obsidianCommand, [`--remote-debugging-port=${cdpPort}`]));
  }
  if (uri) {
    steps.push(await spawnAndForget('xdg-open', [uri], { detached: false }));
  } else if (mode !== 'cdp') {
    steps.push(await spawnAndForget(obsidianCommand, []));
  }
  return steps;
}

async function launchApp() {
  const uri = buildVaultUri();
  if (process.platform === 'win32') {
    return launchWindows(uri);
  }
  if (process.platform === 'darwin') {
    return launchMac(uri);
  }
  return launchLinux(uri);
}

const initialReadiness = await probeReadiness();
let launchSteps = [];
let finalReadiness = initialReadiness;

if (!initialReadiness.ok) {
  launchSteps = await launchApp();
  const deadline = Date.now() + waitMs;
  while (Date.now() <= deadline) {
    await sleep(pollIntervalMs);
    finalReadiness = await probeReadiness();
    if (finalReadiness.ok) {
      break;
    }
  }
}

const report = {
  generatedAt: nowIso(),
  mode,
  platform: process.platform,
  launched: !initialReadiness.ok,
  ready: finalReadiness.ok,
  elapsedMs: Date.now() - startedAt,
  obsidianCommand,
  appPath: appPath || null,
  vaultName: vaultName || null,
  vaultPath: vaultPath || null,
  vaultUri: buildVaultUri() || null,
  cdp: {
    host: cdpHost,
    port: cdpPort,
    targetTitleContains: targetTitleContains || null,
  },
  initialReadiness,
  launchSteps,
  finalReadiness,
  recommendation: finalReadiness.ok
    ? 'Continue with build/deploy/reload/capture automation.'
    : 'Launch or focus Obsidian manually, confirm the target vault is open, or use a CDP restart helper when an already-running app lacks a debug port.',
};

if (outputPath) {
  const resolvedOutputPath = path.resolve(outputPath);
  await ensureParentDirectory(resolvedOutputPath);
  await fs.writeFile(resolvedOutputPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
}

console.log(JSON.stringify(report, null, 2));

if (!report.ready) {
  process.exitCode = 1;
}
