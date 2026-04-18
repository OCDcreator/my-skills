import fs from 'node:fs/promises';
import path from 'node:path';

const HOT_RELOAD_PLUGIN_PATTERN = /\bhot[-_ ]?reload\b/i;
const WATCH_SCRIPT_PATTERNS = [
  { pattern: /\b--watch\b/i, reason: 'uses --watch' },
  { pattern: /(?:^|\s)-w(?:\s|$)/i, reason: 'uses -w watch flag' },
  { pattern: /\bwatch\b/i, reason: 'mentions watch' },
  { pattern: /hot[-_ ]?reload/i, reason: 'mentions Hot Reload' },
  { pattern: /\b(?:vite|esbuild|rollup|tsup|webpack|parcel|nodemon)\b/i, reason: 'uses watch-capable tooling' },
];

function uniqueStrings(values = []) {
  return [...new Set(values.map((value) => String(value ?? '').trim()).filter((value) => value.length > 0))];
}

function scriptEntries(repoRuntime) {
  const bodies = repoRuntime?.scripts?.scriptBodies;
  if (!bodies || typeof bodies !== 'object' || Array.isArray(bodies)) {
    return [];
  }

  return Object.entries(bodies)
    .filter(([, body]) => typeof body === 'string' && body.trim().length > 0);
}

async function readJsonFileOrNull(filePath) {
  try {
    return JSON.parse((await fs.readFile(filePath, 'utf8')).replace(/^\uFEFF/, ''));
  } catch {
    return null;
  }
}

async function lstatOrNull(filePath) {
  try {
    return await fs.lstat(filePath);
  } catch {
    return null;
  }
}

async function readDirectoryEntries(dirPath) {
  try {
    return await fs.readdir(dirPath, { withFileTypes: true });
  } catch {
    return [];
  }
}

function pluginIdFromEntry(entry) {
  if (typeof entry === 'string') {
    return entry.trim();
  }

  if (entry && typeof entry === 'object') {
    return String(entry.id ?? '').trim();
  }

  return '';
}

function watchScriptReasons(name, body) {
  const reasons = [];
  if (/\bwatch\b/i.test(name) || /hot[-_ ]?reload/i.test(name)) {
    reasons.push(`script name ${name}`);
  }

  for (const { pattern, reason } of WATCH_SCRIPT_PATTERNS) {
    if (pattern.test(body)) {
      reasons.push(reason);
    }
  }

  return [...new Set(reasons)];
}

async function detectSymlinkedVaultEntries(testVaultPluginDir) {
  if (!testVaultPluginDir) {
    return [];
  }

  const resolvedPluginDir = path.resolve(testVaultPluginDir);
  const candidates = [
    resolvedPluginDir,
    path.join(resolvedPluginDir, 'main.js'),
    path.join(resolvedPluginDir, 'manifest.json'),
    path.join(resolvedPluginDir, 'styles.css'),
  ];
  const entries = [];

  for (const candidate of candidates) {
    const stat = await lstatOrNull(candidate);
    if (!stat?.isSymbolicLink()) {
      continue;
    }

    let target = null;
    try {
      target = await fs.readlink(candidate);
    } catch {
      target = null;
    }

    entries.push({
      path: candidate,
      target,
    });
  }

  return entries;
}

function deriveVaultConfigDir(testVaultPluginDir) {
  const pluginDir = String(testVaultPluginDir ?? '').trim();
  if (!pluginDir) {
    return null;
  }

  const resolvedPluginDir = path.resolve(pluginDir);
  const pluginsDir = path.dirname(resolvedPluginDir);
  const configDir = path.dirname(pluginsDir);

  if (path.basename(pluginsDir) !== 'plugins' || path.basename(configDir) !== '.obsidian') {
    return null;
  }

  return configDir;
}

async function readFilesystemVaultSignals(testVaultPluginDir) {
  const configDir = deriveVaultConfigDir(testVaultPluginDir);
  if (!configDir) {
    return {
      configDir: null,
      installedIds: [],
      enabledIds: [],
    };
  }

  const pluginsDir = path.join(configDir, 'plugins');
  const dirEntries = await readDirectoryEntries(pluginsDir);
  const installedIds = dirEntries
    .filter((entry) => entry.isDirectory() || entry.isSymbolicLink())
    .map((entry) => entry.name);
  const enabledRaw = await readJsonFileOrNull(path.join(configDir, 'community-plugins.json'));
  const enabledIds = Array.isArray(enabledRaw)
    ? enabledRaw.map((entry) => String(entry ?? '').trim()).filter((entry) => entry.length > 0)
    : [];

  return {
    configDir,
    installedIds,
    enabledIds,
  };
}

export function normalizeHotReloadMode(value, fallback = 'controlled') {
  const normalized = String(value ?? '').trim().toLowerCase();
  return ['controlled', 'coexist'].includes(normalized) ? normalized : fallback;
}

export function matchesHotReloadPluginId(value) {
  const normalized = String(value ?? '').trim();
  if (!normalized) {
    return false;
  }

  return HOT_RELOAD_PLUGIN_PATTERN.test(normalized.replaceAll('.', ' '));
}

export async function detectHotReloadContext({
  repoRuntime = null,
  testVaultPluginDir = '',
  installedPlugins = [],
  enabledPlugins = [],
} = {}) {
  const watchScripts = scriptEntries(repoRuntime)
    .map(([name, body]) => ({
      name,
      body,
      reasons: watchScriptReasons(name, body),
    }))
    .filter((entry) => entry.reasons.length > 0);
  const symlinkedEntries = await detectSymlinkedVaultEntries(testVaultPluginDir);
  const filesystemVaultSignals = await readFilesystemVaultSignals(testVaultPluginDir);
  const installedIds = uniqueStrings([
    ...installedPlugins.map(pluginIdFromEntry),
    ...filesystemVaultSignals.installedIds,
  ]);
  const enabledIds = uniqueStrings([
    ...enabledPlugins.map(pluginIdFromEntry),
    ...filesystemVaultSignals.enabledIds,
  ]);
  const hotReloadInstalledIds = installedIds.filter(matchesHotReloadPluginId);
  const hotReloadEnabledIds = enabledIds.filter(matchesHotReloadPluginId);
  const likelyActive = hotReloadEnabledIds.length > 0 || (symlinkedEntries.length > 0 && watchScripts.length > 0);
  const likelyPresent = likelyActive || hotReloadInstalledIds.length > 0 || watchScripts.length > 0 || symlinkedEntries.length > 0;

  return {
    presence: likelyActive ? 'likely-active' : likelyPresent ? 'possible' : 'none',
    likelyPresent,
    likelyActive,
    likelyInfluencesLogs: likelyActive,
    recommendedSettleMs: likelyActive ? 1500 : likelyPresent ? 1000 : 0,
    repo: {
      watchScripts,
      symlinkedEntries,
    },
    vault: {
      configDir: filesystemVaultSignals.configDir,
      installedIds,
      enabledIds,
      hotReloadInstalledIds,
      hotReloadEnabledIds,
      dataSources: {
        filesystem: Boolean(filesystemVaultSignals.configDir),
        cli: installedPlugins.length > 0 || enabledPlugins.length > 0,
      },
    },
  };
}

export function buildHotReloadGuidance(context, { settleMs } = {}) {
  const recommendedSettleMs = Math.max(0, Number(settleMs ?? context?.recommendedSettleMs ?? 0) || 0);
  const controlledFlags = [
    '--hot-reload-mode',
    'controlled',
    ...(recommendedSettleMs > 0 ? ['--hot-reload-settle-ms', String(recommendedSettleMs)] : []),
  ];
  const coexistFlags = [
    '--hot-reload-mode',
    'coexist',
    ...(recommendedSettleMs > 0 ? ['--hot-reload-settle-ms', String(recommendedSettleMs)] : []),
  ];
  const controlledFlagText = controlledFlags.join(' ');
  const coexistFlagText = coexistFlags.join(' ');

  if (context?.likelyActive) {
    const signals = [];
    if ((context.vault?.hotReloadEnabledIds ?? []).length > 0) {
      signals.push(`vault enables ${context.vault.hotReloadEnabledIds.join(', ')}`);
    }
    if ((context.repo?.symlinkedEntries ?? []).length > 0) {
      signals.push('test vault plugin files are symlinked');
    }
    if ((context.repo?.watchScripts ?? []).length > 0) {
      signals.push(`repo scripts look watch-capable (${context.repo.watchScripts.map((entry) => entry.name).join(', ')})`);
    }

    return {
      recommendedSettleMs,
      controlledFlags,
      coexistFlags,
      detail: `Hot Reload is likely active because ${signals.join('; ')}. Use ${controlledFlagText} when you need deterministic reload timing, or ${coexistFlagText} when you intentionally let background Hot Reload drive startup.`,
    };
  }

  if (context?.likelyPresent) {
    const signals = [];
    if ((context.vault?.hotReloadInstalledIds ?? []).length > 0) {
      signals.push(`vault contains ${context.vault.hotReloadInstalledIds.join(', ')}`);
    }
    if ((context.repo?.watchScripts ?? []).length > 0) {
      signals.push(`repo scripts expose watch-style tooling (${context.repo.watchScripts.map((entry) => entry.name).join(', ')})`);
    }
    if ((context.repo?.symlinkedEntries ?? []).length > 0) {
      signals.push('test vault plugin files are symlinked into the repo');
    }

    return {
      recommendedSettleMs,
      controlledFlags,
      coexistFlags,
      detail: `Hot Reload may be present because ${signals.join('; ')}. Prefer ${controlledFlagText} for deterministic trace ordering, and switch to ${coexistFlagText} only when you want to keep a background reload helper in the loop.`,
    };
  }

  return {
    recommendedSettleMs,
    controlledFlags,
    coexistFlags,
    detail: `No strong Hot Reload signal was detected. Keep the default ${controlledFlagText}, and only use ${coexistFlagText} when the target vault is intentionally running a background reload helper.`,
  };
}
