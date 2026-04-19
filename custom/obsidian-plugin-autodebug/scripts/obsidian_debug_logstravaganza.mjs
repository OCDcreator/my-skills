import fs from 'node:fs/promises';
import path from 'node:path';
import { nowIso } from './obsidian_cdp_common.mjs';
import { deriveVaultRoot } from './obsidian_debug_command_templates.mjs';

const CONFIG_FILE_NAMES = ['data.json', 'config.json', 'settings.json'];
const NDJSON_EXTENSIONS = new Set(['.ndjson', '.jsonl']);
const DEFAULT_SEARCH_ROOTS = [
  '.obsidian',
  path.join('.obsidian', 'logs'),
  path.join('.obsidian', 'plugins', 'logstravaganza'),
  path.join('.obsidian', 'plugins', 'logstravaganza', 'logs'),
  'logs',
  path.join('logs', 'logstravaganza'),
];
const EXCLUDED_DIRECTORY_NAMES = new Set([
  '.git',
  '.trash',
  'node_modules',
]);

function stringValue(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function normalizeTimestamp(raw) {
  if (!raw) {
    return null;
  }

  const normalized = String(raw).trim().replace(/([+-]\d{2})(\d{2})$/, '$1:$2');
  const parsed = Date.parse(normalized);
  return Number.isFinite(parsed) ? parsed : null;
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

async function statOrNull(filePath) {
  try {
    return await fs.stat(filePath);
  } catch {
    return null;
  }
}

async function readTextOrNull(filePath) {
  if (!filePath) {
    return null;
  }

  try {
    return (await fs.readFile(filePath, 'utf8')).replace(/^\uFEFF/, '');
  } catch {
    return null;
  }
}

async function readJsonOrNull(filePath) {
  const text = await readTextOrNull(filePath);
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function uniquePaths(values = []) {
  const seen = new Set();
  const unique = [];
  for (const value of values) {
    const normalized = stringValue(value);
    if (!normalized) {
      continue;
    }
    const resolved = path.resolve(normalized);
    if (seen.has(resolved)) {
      continue;
    }
    seen.add(resolved);
    unique.push(resolved);
  }
  return unique;
}

function relativePath(baseDir, targetPath) {
  if (!baseDir || !targetPath) {
    return null;
  }

  const relative = path.relative(baseDir, targetPath);
  return relative && !relative.startsWith('..') && !path.isAbsolute(relative)
    ? relative.replaceAll('\\', '/')
    : null;
}

function collectPathHints(value, {
  vaultRoot,
  pluginDir,
  trail = [],
  results = [],
} = {}) {
  if (Array.isArray(value)) {
    value.forEach((entry, index) => collectPathHints(entry, {
      vaultRoot,
      pluginDir,
      trail: [...trail, String(index)],
      results,
    }));
    return results;
  }

  if (value && typeof value === 'object') {
    Object.entries(value).forEach(([key, entry]) => collectPathHints(entry, {
      vaultRoot,
      pluginDir,
      trail: [...trail, key],
      results,
    }));
    return results;
  }

  const raw = stringValue(value);
  if (!raw) {
    return results;
  }

  const joinedTrail = trail.join('.').toLowerCase();
  const looksLikePath = /[\\/]/.test(raw)
    || raw.startsWith('.')
    || NDJSON_EXTENSIONS.has(path.extname(raw).toLowerCase())
    || /(path|dir|file|output|target|log)/i.test(joinedTrail);
  if (!looksLikePath) {
    return results;
  }

  const candidates = [];
  if (path.isAbsolute(raw)) {
    candidates.push(path.resolve(raw));
  } else {
    if (vaultRoot) {
      candidates.push(path.resolve(vaultRoot, raw));
    }
    if (pluginDir) {
      candidates.push(path.resolve(pluginDir, raw));
    }
  }

  results.push(...candidates);
  return results;
}

async function collectNdjsonFiles(rootPath, {
  vaultRoot,
  maxDepth = 5,
  seenFiles,
} = {}) {
  const resolvedRoot = stringValue(rootPath);
  if (!resolvedRoot) {
    return [];
  }

  const rootStat = await statOrNull(resolvedRoot);
  if (!rootStat) {
    return [];
  }

  if (rootStat.isFile()) {
    return NDJSON_EXTENSIONS.has(path.extname(resolvedRoot).toLowerCase())
      ? [resolvedRoot]
      : [];
  }

  const discovered = [];
  const queue = [{ dir: resolvedRoot, depth: 0 }];
  while (queue.length > 0) {
    const current = queue.shift();
    let entries = [];
    try {
      entries = await fs.readdir(current.dir, { withFileTypes: true });
    } catch {
      continue;
    }

    for (const entry of entries) {
      const fullPath = path.join(current.dir, entry.name);
      if (entry.isDirectory()) {
        if (current.depth >= maxDepth || EXCLUDED_DIRECTORY_NAMES.has(entry.name.toLowerCase())) {
          continue;
        }
        queue.push({ dir: fullPath, depth: current.depth + 1 });
        continue;
      }

      if (!entry.isFile() || !NDJSON_EXTENSIONS.has(path.extname(entry.name).toLowerCase())) {
        continue;
      }

      const resolvedFile = path.resolve(fullPath);
      if (seenFiles.has(resolvedFile)) {
        continue;
      }

      seenFiles.add(resolvedFile);
      discovered.push(resolvedFile);
    }
  }

  return discovered.sort((left, right) => {
    const leftRelative = relativePath(vaultRoot, left) ?? left;
    const rightRelative = relativePath(vaultRoot, right) ?? right;
    return leftRelative.localeCompare(rightRelative);
  });
}

function firstString(values = []) {
  for (const value of values) {
    const normalized = stringValue(value);
    if (normalized) {
      return normalized;
    }
  }
  return '';
}

function normalizeEventRecord(record) {
  if (!record || typeof record !== 'object' || Array.isArray(record)) {
    return {
      timestamp: null,
      level: '',
      pluginId: '',
      channel: '',
      message: stringValue(record) || JSON.stringify(record),
    };
  }

  const timestamp = firstString([
    record.timestamp,
    record.time,
    record.ts,
    record.createdAt,
    record.date,
    record.at,
  ]);
  const level = firstString([
    record.level,
    record.severity,
    record.type,
    record.kind,
  ]);
  const pluginId = firstString([
    record.pluginId,
    record.plugin?.id,
    record.plugin?.pluginId,
  ]);
  const channel = firstString([
    record.channel,
    record.logger,
    typeof record.source === 'string' ? record.source : '',
    record.source?.channel,
  ]);
  const message = firstString([
    record.message,
    record.msg,
    record.text,
    record.content,
    record.summary,
    record.detail,
    record.event,
  ]) || JSON.stringify(record);

  return { timestamp, level, pluginId, channel, message };
}

async function inspectNdjsonFile(filePath, { vaultRoot } = {}) {
  const text = await readTextOrNull(filePath);
  const stat = await statOrNull(filePath);
  const lines = text
    ? text.split(/\r?\n/).map((line) => line.trim()).filter((line) => line.length > 0)
    : [];

  let parsedLineCount = 0;
  let invalidLineCount = 0;
  const levels = new Set();
  const pluginIds = new Set();
  let firstTimestamp = null;
  let lastTimestamp = null;

  for (const line of lines) {
    try {
      const parsed = JSON.parse(line);
      const normalized = normalizeEventRecord(parsed);
      parsedLineCount += 1;
      if (normalized.level) {
        levels.add(normalized.level);
      }
      if (normalized.pluginId) {
        pluginIds.add(normalized.pluginId);
      }
      const timestamp = normalizeTimestamp(normalized.timestamp);
      if (timestamp !== null) {
        firstTimestamp = firstTimestamp === null ? timestamp : Math.min(firstTimestamp, timestamp);
        lastTimestamp = lastTimestamp === null ? timestamp : Math.max(lastTimestamp, timestamp);
      }
    } catch {
      invalidLineCount += 1;
    }
  }

  return {
    path: path.resolve(filePath),
    relativePath: relativePath(vaultRoot, filePath),
    sizeBytes: stat?.size ?? 0,
    modifiedAt: stat?.mtime ? stat.mtime.toISOString() : null,
    lineCount: lines.length,
    parsedLineCount,
    invalidLineCount,
    firstTimestamp: firstTimestamp === null ? null : new Date(firstTimestamp).toISOString(),
    lastTimestamp: lastTimestamp === null ? null : new Date(lastTimestamp).toISOString(),
    levels: [...levels],
    pluginIds: [...pluginIds],
  };
}

function sortByTimestamp(entries = []) {
  return entries
    .map((entry, index) => ({ entry, index }))
    .sort((left, right) => {
      const leftTimestamp = normalizeTimestamp(left.entry.timestamp);
      const rightTimestamp = normalizeTimestamp(right.entry.timestamp);
      if (leftTimestamp !== null && rightTimestamp !== null && leftTimestamp !== rightTimestamp) {
        return leftTimestamp - rightTimestamp;
      }
      if (leftTimestamp !== null && rightTimestamp === null) {
        return -1;
      }
      if (leftTimestamp === null && rightTimestamp !== null) {
        return 1;
      }
      return left.index - right.index;
    })
    .map((entry) => entry.entry);
}

function buildCaptureDetail({
  vaultRoot,
  pluginDirExists,
  logFiles = [],
  lineCount = 0,
  invalidLineCount = 0,
} = {}) {
  if (logFiles.length > 0 && lineCount > 0) {
    const relative = logFiles
      .map((entry) => entry.relativePath ?? path.basename(entry.path))
      .join(', ');
    const invalidSuffix = invalidLineCount > 0 ? ` (${invalidLineCount} invalid line${invalidLineCount === 1 ? '' : 's'} skipped)` : '';
    return `Detected ${logFiles.length} Logstravaganza NDJSON file(s) with ${lineCount} parsed event line(s) at ${relative}${invalidSuffix}.`;
  }

  if (logFiles.length > 0) {
    return `Detected ${logFiles.length} Logstravaganza NDJSON file(s), but none produced parseable event lines.`;
  }

  if (pluginDirExists) {
    return 'Logstravaganza is present in the target vault, but no NDJSON log files were discovered yet.';
  }

  if (vaultRoot) {
    return 'No Logstravaganza plugin directory or NDJSON log files were discovered under the target vault root.';
  }

  return 'No target vault root was available for Logstravaganza discovery.';
}

export async function discoverLogstravaganzaCapture({
  testVaultPluginDir = '',
  vaultRoot = '',
  maxDepth = 5,
} = {}) {
  const resolvedTestVaultPluginDir = stringValue(testVaultPluginDir)
    ? path.resolve(testVaultPluginDir)
    : '';
  const resolvedVaultRoot = stringValue(vaultRoot)
    ? path.resolve(vaultRoot)
    : deriveVaultRoot(resolvedTestVaultPluginDir);
  const pluginDir = resolvedVaultRoot
    ? path.join(resolvedVaultRoot, '.obsidian', 'plugins', 'logstravaganza')
    : '';
  const pluginDirExists = await exists(pluginDir);
  const manifestPath = pluginDirExists && await exists(path.join(pluginDir, 'manifest.json'))
    ? path.join(pluginDir, 'manifest.json')
    : null;
  const configFiles = [];
  const candidatePaths = [];

  if (resolvedVaultRoot) {
    candidatePaths.push(...DEFAULT_SEARCH_ROOTS.map((entry) => path.join(resolvedVaultRoot, entry)));
  }
  if (pluginDir) {
    candidatePaths.push(pluginDir, path.join(pluginDir, 'logs'));
  }

  for (const configFileName of CONFIG_FILE_NAMES) {
    const candidate = pluginDir ? path.join(pluginDir, configFileName) : '';
    if (!candidate || !(await exists(candidate))) {
      continue;
    }

    const config = await readJsonOrNull(candidate);
    configFiles.push({
      path: candidate,
      relativePath: relativePath(resolvedVaultRoot, candidate),
      keys: config && typeof config === 'object' && !Array.isArray(config)
        ? Object.keys(config).sort()
        : [],
    });
    const hints = collectPathHints(config, {
      vaultRoot: resolvedVaultRoot,
      pluginDir,
    });
    candidatePaths.push(...hints);
  }

  const seenFiles = new Set();
  const discoveredFiles = [];
  for (const candidatePath of uniquePaths(candidatePaths)) {
    discoveredFiles.push(...await collectNdjsonFiles(candidatePath, {
      vaultRoot: resolvedVaultRoot,
      maxDepth,
      seenFiles,
    }));
  }

  const logFiles = [];
  for (const filePath of uniquePaths(discoveredFiles)) {
    logFiles.push(await inspectNdjsonFile(filePath, { vaultRoot: resolvedVaultRoot }));
  }

  const lineCount = logFiles.reduce((total, entry) => total + (entry.parsedLineCount ?? 0), 0);
  const invalidLineCount = logFiles.reduce((total, entry) => total + (entry.invalidLineCount ?? 0), 0);

  return {
    generatedAt: nowIso(),
    testVaultPluginDir: resolvedTestVaultPluginDir || null,
    vaultRoot: resolvedVaultRoot || null,
    pluginDir: pluginDirExists ? pluginDir : null,
    pluginDirExists,
    manifestPath,
    configFiles,
    candidatePaths: uniquePaths(candidatePaths).map((entry) => ({
      path: entry,
      relativePath: relativePath(resolvedVaultRoot, entry),
    })),
    logFiles,
    sourceCount: logFiles.length,
    lineCount,
    invalidLineCount,
    available: Boolean(resolvedVaultRoot),
    usable: lineCount > 0,
    detail: buildCaptureDetail({
      vaultRoot: resolvedVaultRoot,
      pluginDirExists,
      logFiles,
      lineCount,
      invalidLineCount,
    }),
  };
}

export async function ingestLogstravaganzaCapture(capture) {
  const normalizedCapture = capture && typeof capture === 'object' && !Array.isArray(capture)
    ? capture
    : {
        available: false,
        usable: false,
        detail: 'No Logstravaganza capture metadata was available.',
        logFiles: [],
        lineCount: 0,
        invalidLineCount: 0,
      };
  const vaultRoot = stringValue(normalizedCapture.vaultRoot);
  const lines = [];
  const sources = [];

  for (const file of normalizedCapture.logFiles ?? []) {
    const filePath = stringValue(file.path);
    if (!filePath) {
      continue;
    }

    const text = await readTextOrNull(filePath);
    const rawLines = text
      ? text.split(/\r?\n/)
      : [];
    let parsedLineCount = 0;
    let invalidLineCount = 0;

    rawLines.forEach((line, index) => {
      const trimmed = line.trim();
      if (!trimmed) {
        return;
      }

      try {
        const parsed = JSON.parse(trimmed);
        const normalized = normalizeEventRecord(parsed);
        const renderedText = `${normalized.timestamp ? `${normalized.timestamp} ` : ''}${normalized.message}`.trim();
        lines.push({
          filePath,
          lineNumber: index + 1,
          text: renderedText || trimmed,
          timestamp: normalized.timestamp || null,
          level: normalized.level || null,
          pluginId: normalized.pluginId || null,
          channel: normalized.channel || null,
          sourceLabel: file.relativePath ?? relativePath(vaultRoot, filePath) ?? path.basename(filePath),
          sourceKind: 'logstravaganza',
        });
        parsedLineCount += 1;
      } catch {
        invalidLineCount += 1;
      }
    });

    sources.push({
      path: filePath,
      relativePath: file.relativePath ?? relativePath(vaultRoot, filePath),
      parsedLineCount,
      invalidLineCount,
      lineCount: (file.lineCount ?? (parsedLineCount + invalidLineCount)),
      sizeBytes: file.sizeBytes ?? 0,
      modifiedAt: file.modifiedAt ?? null,
      firstTimestamp: file.firstTimestamp ?? null,
      lastTimestamp: file.lastTimestamp ?? null,
      levels: Array.isArray(file.levels) ? file.levels : [],
      pluginIds: Array.isArray(file.pluginIds) ? file.pluginIds : [],
    });
  }

  const sortedLines = sortByTimestamp(lines);
  const preview = sortedLines.slice(0, 20).map((entry) => ({
    text: entry.text,
    filePath: entry.filePath,
    lineNumber: entry.lineNumber,
    sourceLabel: entry.sourceLabel,
    timestamp: entry.timestamp,
    level: entry.level,
  }));

  return {
    available: Boolean(normalizedCapture.available),
    usable: sortedLines.length > 0,
    status: sortedLines.length > 0
      ? 'captured'
      : (normalizedCapture.logFiles?.length ?? 0) > 0
        ? 'invalid'
        : 'unavailable',
    detail: stringValue(normalizedCapture.detail)
      || buildCaptureDetail({
        vaultRoot,
        pluginDirExists: Boolean(normalizedCapture.pluginDirExists),
        logFiles: normalizedCapture.logFiles ?? [],
        lineCount: sortedLines.length,
        invalidLineCount: normalizedCapture.invalidLineCount ?? 0,
      }),
    lineCount: sortedLines.length,
    invalidLineCount: Number(normalizedCapture.invalidLineCount ?? 0),
    sourceCount: sources.length,
    lines: sortedLines,
    sources,
    preview,
  };
}
