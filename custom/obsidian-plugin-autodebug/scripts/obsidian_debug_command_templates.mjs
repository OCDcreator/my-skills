import path from 'node:path';

const TEMPLATE_PATTERN = /\{\{(\w+)\}\}/g;

export function normalizePlatform(value = 'auto') {
  const normalized = String(value ?? '').trim().toLowerCase();
  if (!normalized || normalized === 'auto') {
    return process.platform === 'win32' ? 'windows' : 'bash';
  }
  if (['windows', 'powershell', 'pwsh', 'ps1'].includes(normalized)) {
    return 'windows';
  }
  if (['bash', 'macos', 'linux', 'darwin', 'sh'].includes(normalized)) {
    return 'bash';
  }
  throw new Error('Platform must be auto, windows, or bash');
}

export function quoteBash(value) {
  return `'${String(value).replaceAll("'", "'\\''")}'`;
}

export function quotePowerShell(value) {
  return `'${String(value).replaceAll("'", "''")}'`;
}

export function renderExplicitCommand({ executable, args = [], platform = 'auto' }) {
  const normalizedPlatform = normalizePlatform(platform);
  const quote = normalizedPlatform === 'windows' ? quotePowerShell : quoteBash;
  const renderedArgs = args.map((entry) => quote(entry));
  if (normalizedPlatform === 'windows') {
    return [`& ${quote(executable)}`, ...renderedArgs].join(' ').trim();
  }
  return [executable, ...args].map((entry) => quote(entry)).join(' ').trim();
}

function applyTemplate(value, variables, unresolved) {
  return String(value ?? '').replace(TEMPLATE_PATTERN, (_, key) => {
    const replacement = variables[key];
    if (replacement === undefined || replacement === null || String(replacement).trim().length === 0) {
      unresolved.add(key);
      return `{{${key}}}`;
    }
    return String(replacement);
  });
}

function pickPlatformVariant(template, platform) {
  if (!template || typeof template !== 'object' || Array.isArray(template)) {
    return template;
  }
  const variant = template[platform];
  if (!variant || typeof variant !== 'object' || Array.isArray(variant)) {
    return template;
  }
  const { windows, bash, ...base } = template;
  return {
    ...base,
    ...variant,
  };
}

export function resolveTemplateCommand(template, { variables = {}, platform = 'auto' } = {}) {
  const normalizedPlatform = normalizePlatform(platform);
  if (typeof template === 'string') {
    const unresolved = new Set();
    const rendered = applyTemplate(template, variables, unresolved).trim();
    return {
      id: null,
      label: 'Command',
      summary: '',
      safety: 'review',
      dryRunFriendly: false,
      destructive: false,
      platform: normalizedPlatform,
      executable: null,
      args: [],
      cwd: null,
      rendered,
      runnable: unresolved.size === 0 && rendered.length > 0,
      unresolvedPlaceholders: [...unresolved],
    };
  }

  const selected = pickPlatformVariant(template ?? {}, normalizedPlatform) ?? {};
  const platforms = Array.isArray(selected.platforms) ? selected.platforms : null;
  const unsupported = platforms ? !platforms.includes(normalizedPlatform) : false;
  const unresolved = new Set();
  const executable = applyTemplate(selected.executable ?? '', variables, unresolved).trim();
  const args = Array.isArray(selected.args)
    ? selected.args.map((entry) => applyTemplate(entry, variables, unresolved))
    : [];
  const cwd = selected.cwd
    ? applyTemplate(selected.cwd, variables, unresolved).trim()
    : '';
  const rendered = selected.rendered
    ? applyTemplate(selected.rendered, variables, unresolved).trim()
    : executable
      ? renderExplicitCommand({ executable, args, platform: normalizedPlatform })
      : '';

  return {
    id: selected.id ?? null,
    label: selected.label ?? selected.summary ?? selected.id ?? 'Command',
    summary: selected.summary ?? '',
    safety: selected.safety ?? 'review',
    dryRunFriendly: selected.dryRunFriendly === true,
    destructive: selected.destructive === true,
    platform: normalizedPlatform,
    executable: executable || null,
    args,
    cwd: cwd || null,
    rendered,
    runnable: !unsupported && unresolved.size === 0 && rendered.length > 0,
    unsupported,
    unresolvedPlaceholders: [...unresolved],
  };
}

export function buildCommandScript({ title, commands, platform = 'auto' }) {
  const normalizedPlatform = normalizePlatform(platform);
  const commentPrefix = '#';
  const lines = [];
  if (normalizedPlatform === 'bash') {
    lines.push('#!/usr/bin/env bash');
    lines.push('set -euo pipefail');
    lines.push('');
  }
  lines.push(`${commentPrefix} ${title}`);
  lines.push(`${commentPrefix} Generated for ${normalizedPlatform}`);
  lines.push('');

  for (const command of commands) {
    if (!command?.rendered) {
      continue;
    }
    lines.push(`${commentPrefix} [${command.safety ?? 'review'}] ${command.label ?? command.id ?? 'Command'}`);
    if (command.summary) {
      lines.push(`${commentPrefix} ${command.summary}`);
    }
    if (command.cwd) {
      lines.push(`${commentPrefix} cwd: ${command.cwd}`);
    }
    if (command.unresolvedPlaceholders?.length) {
      lines.push(`${commentPrefix} unresolved: ${command.unresolvedPlaceholders.join(', ')}`);
    }
    lines.push(command.rendered);
    lines.push('');
  }

  return `${lines.join('\n').trimEnd()}\n`;
}

export function scriptExtension(platform = 'auto') {
  return normalizePlatform(platform) === 'windows' ? 'ps1' : 'sh';
}

export function deriveVaultRoot(testVaultPluginDir) {
  if (!testVaultPluginDir) {
    return '';
  }

  const resolved = path.resolve(testVaultPluginDir);
  const marker = `${path.sep}.obsidian${path.sep}plugins${path.sep}`.toLowerCase();
  const index = resolved.toLowerCase().lastIndexOf(marker);
  if (index === -1) {
    return '';
  }
  return resolved.slice(0, index);
}
