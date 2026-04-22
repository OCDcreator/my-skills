import { existsSync } from 'node:fs';
import fsp from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

export function parseArgs(argv) {
  const options = new Map();

  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) {
      continue;
    }

    const key = token.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith('--')) {
      options.set(key, true);
      continue;
    }

    options.set(key, next);
    index += 1;
  }

  return options;
}

export function getStringOption(options, key, fallback = '') {
  const value = options.get(key);
  return typeof value === 'string' && value.length > 0 ? value : fallback;
}

export function getNumberOption(options, key, fallback) {
  const raw = options.get(key);
  if (typeof raw !== 'string' || raw.length === 0) {
    return fallback;
  }

  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function getBooleanOption(options, key, fallback = false) {
  const raw = options.get(key);
  if (typeof raw === 'boolean') {
    return raw;
  }
  if (typeof raw === 'string') {
    if (raw === 'true' || raw === '1') {
      return true;
    }
    if (raw === 'false' || raw === '0') {
      return false;
    }
  }
  return fallback;
}

export function hasHelpOption(options) {
  return options.has('help') || options.has('h');
}

export function printHelpAndExit(text) {
  console.log(String(text).trim());
  process.exit(0);
}

export async function ensureParentDirectory(filePath) {
  await fsp.mkdir(path.dirname(filePath), { recursive: true });
}

export function formatRemoteObject(value) {
  if (!value || typeof value !== 'object') {
    return String(value);
  }

  if ('value' in value && value.value !== undefined) {
    return typeof value.value === 'string' ? value.value : JSON.stringify(value.value);
  }

  if (value.unserializableValue) {
    return String(value.unserializableValue);
  }

  if (value.description) {
    return String(value.description);
  }

  return value.type ?? '[unknown]';
}

export function nowIso() {
  return new Date().toISOString();
}

function splitPathEntries(value) {
  return String(value || '')
    .split(path.delimiter)
    .map((entry) => entry.trim())
    .filter(Boolean);
}

const mergedWindowsPathCache = new Map();

function getWindowsPowerShellPath() {
  return path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe');
}

function readWindowsPathScope(scope) {
  const powershellPath = getWindowsPowerShellPath();
  if (!existsSync(powershellPath)) {
    return '';
  }

  const result = spawnSync(
    powershellPath,
    [
      '-NoProfile',
      '-Command',
      `[Environment]::GetEnvironmentVariable('Path','${scope}')`,
    ],
    {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    },
  );

  if (result.error || result.status !== 0) {
    return '';
  }

  return typeof result.stdout === 'string' ? result.stdout.trim() : '';
}

function mergeWindowsPathEntries(baseEnv = process.env) {
  const pathKeys = Object.keys(baseEnv).filter((key) => key.toLowerCase() === 'path');
  const currentPath = pathKeys.length > 0 ? baseEnv[pathKeys[0]] : process.env.PATH ?? '';
  if (mergedWindowsPathCache.has(currentPath)) {
    return mergedWindowsPathCache.get(currentPath);
  }

  const entries = [
    ...splitPathEntries(currentPath),
    ...splitPathEntries(readWindowsPathScope('User')),
    ...splitPathEntries(readWindowsPathScope('Machine')),
  ];
  const seen = new Set();
  const merged = [];

  for (const entry of entries) {
    const normalized = path.normalize(entry).toLowerCase();
    if (seen.has(normalized)) {
      continue;
    }
    seen.add(normalized);
    merged.push(entry);
  }

  const mergedPath = merged.join(path.delimiter);
  mergedWindowsPathCache.set(currentPath, mergedPath);
  return mergedPath;
}

export function withRefreshedWindowsPath(baseEnv = process.env) {
  if (process.platform !== 'win32') {
    return baseEnv;
  }

  const mergedPath = mergeWindowsPathEntries(baseEnv);
  if (!mergedPath) {
    return baseEnv;
  }

  const env = { ...baseEnv };
  const pathKeys = Object.keys(env).filter((key) => key.toLowerCase() === 'path');
  if (pathKeys.length === 0) {
    env.PATH = mergedPath;
    return env;
  }

  for (const key of pathKeys) {
    env[key] = mergedPath;
  }

  return env;
}

export function resolveObsidianCliCommand(command, { platform = process.platform } = {}) {
  const trimmed = String(command || '').trim() || 'obsidian';
  if (platform !== 'win32') {
    return trimmed;
  }

  if (/\.exe$/i.test(trimmed)) {
    const comCandidate = trimmed.replace(/\.exe$/i, '.com');
    if (existsSync(comCandidate)) {
      return comCandidate;
    }
  }

  return trimmed;
}

export async function resolveTarget({
  host = '127.0.0.1',
  port = 9222,
  targetUrl = 'app://obsidian.md/index.html',
  targetTitleContains = '',
}) {
  const response = await fetch(`http://${host}:${port}/json/list`);
  if (!response.ok) {
    throw new Error(`Failed to query CDP targets: HTTP ${response.status}`);
  }

  const targets = await response.json();
  if (targetTitleContains) {
    const titled = targets.find(
      (item) =>
        item.url === targetUrl
        && typeof item.title === 'string'
        && item.title.includes(targetTitleContains)
        && item.webSocketDebuggerUrl,
    );
    if (titled) {
      return titled;
    }
  }

  const exact = targets.find((item) => item.url === targetUrl);
  if (exact?.webSocketDebuggerUrl) {
    return exact;
  }

  const fallback = targets.find(
    (item) => item.url?.startsWith('app://obsidian.md') && item.webSocketDebuggerUrl,
  );
  if (fallback) {
    return fallback;
  }

  throw new Error(`No Obsidian app target found for ${targetUrl}`);
}

export function hasGlobalWebSocket() {
  return typeof globalThis.WebSocket === 'function';
}

export function getWebSocketSupportDetail() {
  return hasGlobalWebSocket()
    ? `globalThis.WebSocket is available in Node.js ${process.versions.node}`
    : `globalThis.WebSocket is unavailable in Node.js ${process.versions.node}; CDP helpers need a runtime with built-in WebSocket support (Node.js 22+ recommended) or an explicit polyfill.`;
}

export function ensureGlobalWebSocket() {
  if (!hasGlobalWebSocket()) {
    throw new Error(getWebSocketSupportDetail());
  }

  return globalThis.WebSocket;
}

export async function connectToCdp({
  host = '127.0.0.1',
  port = 9222,
  targetUrl = 'app://obsidian.md/index.html',
  targetTitleContains = '',
  onLine,
}) {
  const target = await resolveTarget({ host, port, targetUrl, targetTitleContains });
  const WebSocketCtor = ensureGlobalWebSocket();
  const ws = new WebSocketCtor(target.webSocketDebuggerUrl);

  await new Promise((resolve, reject) => {
    ws.addEventListener('open', () => resolve(), { once: true });
    ws.addEventListener(
      'error',
      (event) => reject(event.error ?? new Error('CDP WebSocket open failed')),
      { once: true },
    );
  });

  let nextId = 1;
  const pending = new Map();

  ws.addEventListener('message', (event) => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const resolver = pending.get(message.id);
      if (!resolver) {
        return;
      }

      pending.delete(message.id);
      if (message.error) {
        resolver.reject(new Error(message.error.message ?? 'CDP request failed'));
        return;
      }

      resolver.resolve(message.result);
      return;
    }

    if (message.method === 'Runtime.consoleAPICalled') {
      const argsText = Array.isArray(message.params?.args)
        ? message.params.args.map(formatRemoteObject).join(' ')
        : '';
      onLine?.(`console.${message.params?.type ?? 'log'}`, argsText);
      return;
    }

    if (message.method === 'Log.entryAdded') {
      const entry = message.params?.entry;
      onLine?.(
        `log.${entry?.level ?? 'info'}`,
        `${entry?.source ?? 'unknown'} ${entry?.text ?? ''}`.trim(),
      );
      return;
    }

    if (message.method === 'Runtime.exceptionThrown') {
      const details = message.params?.exceptionDetails;
      onLine?.(
        'runtime.exception',
        details?.text ?? details?.exception?.description ?? 'Runtime exception',
      );
    }
  });

  function send(method, params = {}) {
    const id = nextId;
    nextId += 1;

    return new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async function evaluate(expression, { awaitPromise = true, returnByValue = true } = {}) {
    return send('Runtime.evaluate', {
      expression,
      awaitPromise,
      returnByValue,
    });
  }

  async function close() {
    await new Promise((resolve) => {
      ws.addEventListener('close', () => resolve(), { once: true });
      ws.close();
    });
  }

  await send('Runtime.enable');
  await send('Log.enable');
  await send('Page.enable');

  return {
    target,
    send,
    evaluate,
    close,
  };
}

export async function setObsidianDebugFlags(session) {
  return session.evaluate(`(() => {
    globalThis.__OPENCODIAN_DEBUG__ = true;
    globalThis.__OPENCODIAN_INLINE_SERIALIZED_DEBUG_ARGS__ = true;
    globalThis.localStorage?.setItem('opencodian:debug', 'true');
    return {
      debug: globalThis.__OPENCODIAN_DEBUG__ ?? null,
      inline: globalThis.__OPENCODIAN_INLINE_SERIALIZED_DEBUG_ARGS__ ?? null,
    };
  })()`);
}

export async function clearObsidianConsole(session) {
  return session.evaluate('globalThis.console.clear?.()');
}

export async function reloadPluginViaApp(session, pluginId, waitMs = 800) {
  return session.evaluate(`(async () => {
    const plugins = globalThis.app?.plugins;
    if (!plugins) {
      return { ok: false, reason: 'plugins-unavailable' };
    }
    await plugins.disablePlugin(${JSON.stringify(pluginId)});
    await new Promise((resolve) => setTimeout(resolve, ${Math.max(0, waitMs)}));
    await plugins.enablePlugin(${JSON.stringify(pluginId)});
    return {
      ok: true,
      loaded: Boolean(plugins.plugins?.[${JSON.stringify(pluginId)}]),
    };
  })()`);
}

export async function writeTraceArtifacts({ outputPath, summaryPath, lines, summary }) {
  await ensureParentDirectory(outputPath);
  await fs.writeFile(outputPath, `${lines.join('\n')}\n`, 'utf8');
  if (summaryPath) {
    await ensureParentDirectory(summaryPath);
    await fs.writeFile(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
  }
}
