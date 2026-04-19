import fs from 'node:fs/promises';
import path from 'node:path';
import { detectEcosystemSupport } from './obsidian_debug_ecosystem_support.mjs';
import {
  buildRunCommand,
  detectRepoRuntime,
  formatCommandTokens,
} from './obsidian_debug_repo_runtime.mjs';
import { detectTestingFrameworkSupport } from './obsidian_debug_testing_framework_support.mjs';

const COREPACK_MANAGERS = new Set(['pnpm', 'yarn']);
const REPO_LOCAL_EXTENSIONS = ['.json', '.js', '.mjs', '.cjs', '.ts', '.mts', '.cts'];
const REPO_LOCAL_PREFIXES = [
  'autodebug/',
  '.obsidian-debug/',
  'scripts/',
  'config/',
  'configs/',
  'e2e/',
  'test/',
  'tests/',
];
const FILE_ARG_HINTS = new Set(['--config', '--config-file', '--configfile', '--project', '--spec', '-c', 'run']);

function uniqueStrings(values) {
  return [...new Set(
    values
      .map((entry) => String(entry ?? '').trim())
      .filter((entry) => entry.length > 0),
  )];
}

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

function recommendedRunnerTokens(manager) {
  const normalized = String(manager ?? '').trim().toLowerCase();
  if (COREPACK_MANAGERS.has(normalized)) {
    return ['corepack', normalized, 'run'];
  }
  if (normalized === 'bun') {
    return ['bun', 'run'];
  }
  return ['npm', 'run'];
}

function previewScriptCommand(manager, scriptName) {
  const command = [...recommendedRunnerTokens(manager), scriptName];
  return {
    command,
    rendered: formatCommandTokens(command),
  };
}

function buildScriptCommand(runtimeSupport, scriptName) {
  const normalizedScript = String(scriptName ?? '').trim();
  const manager = runtimeSupport?.inference?.manager ?? 'npm';
  const preview = previewScriptCommand(manager, normalizedScript);

  if (!normalizedScript) {
    return {
      script: '',
      available: false,
      via: 'missing',
      command: [],
      rendered: '',
      previewCommand: [],
      previewRendered: '',
      detail: 'No package.json script was selected.',
    };
  }

  const runnable = buildRunCommand(manager, normalizedScript, runtimeSupport?.tools ?? {});
  return {
    script: normalizedScript,
    available: runnable.available,
    via: runnable.via,
    command: runnable.command,
    rendered: runnable.rendered,
    previewCommand: preview.command,
    previewRendered: preview.rendered,
    detail: runnable.available
      ? `Ready to run ${preview.rendered}.`
      : runnable.detail,
  };
}

function stripOuterQuotes(token) {
  const text = String(token ?? '').trim();
  if (text.length < 2) {
    return text;
  }

  const quote = text[0];
  return quote === text[text.length - 1] && ['"', '\'', '`'].includes(quote)
    ? text.slice(1, -1)
    : text;
}

function tokenizeCommand(commandText) {
  return String(commandText ?? '').match(/"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`|\S+/g) ?? [];
}

function looksLikeRepoOwnedPath(token, previousToken = '') {
  const normalized = stripOuterQuotes(token).replaceAll('\\', '/');
  if (!normalized || normalized.startsWith('-') || normalized.includes('{{') || normalized.includes('${')) {
    return false;
  }

  const lower = normalized.toLowerCase();
  const lowerPrevious = stripOuterQuotes(previousToken).toLowerCase();
  const hasExtension = REPO_LOCAL_EXTENSIONS.some((extension) => lower.endsWith(extension));
  const hasPrefix = REPO_LOCAL_PREFIXES.some((prefix) => lower.startsWith(prefix))
    || lower.startsWith('./')
    || lower.startsWith('../');
  const fileArgument = FILE_ARG_HINTS.has(lowerPrevious) && hasExtension;

  if (!hasExtension) {
    return false;
  }

  if (fileArgument) {
    return true;
  }

  return hasPrefix;
}

function resolveRepoRelativePath(repoDir, candidatePath) {
  const resolvedRepoDir = path.resolve(repoDir);
  const resolvedCandidate = path.resolve(resolvedRepoDir, candidatePath);
  const relativePath = path.relative(resolvedRepoDir, resolvedCandidate);
  if (!relativePath || relativePath === '.') {
    return null;
  }
  if (relativePath.startsWith('..') || path.isAbsolute(relativePath)) {
    return null;
  }

  return {
    path: resolvedCandidate,
    relativePath: relativePath.replaceAll(path.sep, '/'),
  };
}

async function collectRepoOwnedPaths(repoDir, scriptBody) {
  const tokens = tokenizeCommand(scriptBody);
  const findings = [];

  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index];
    const previousToken = tokens[index - 1] ?? '';
    if (!looksLikeRepoOwnedPath(token, previousToken)) {
      continue;
    }

    const resolved = resolveRepoRelativePath(repoDir, stripOuterQuotes(token));
    if (!resolved) {
      continue;
    }

    findings.push({
      ...resolved,
      exists: await exists(resolved.path),
    });
  }

  return findings.filter((entry, index, entries) => entries.findIndex((candidate) => candidate.relativePath === entry.relativePath) === index);
}

async function annotateScripts({ repoDir, runtimeSupport, scripts = [] }) {
  return Promise.all(scripts.map(async (script) => {
    const command = buildScriptCommand(runtimeSupport, script.name);
    const repoOwnedPaths = await collectRepoOwnedPaths(repoDir, script.body);
    const missingRepoOwnedPaths = repoOwnedPaths.filter((entry) => !entry.exists);
    const runnable = missingRepoOwnedPaths.length === 0;
    return {
      ...script,
      command,
      repoOwnedPaths,
      missingRepoOwnedPaths,
      runnable,
      runnableInThisCheckout: runnable && command.available,
    };
  }));
}

function summarizeRepoOwnedPaths(paths = []) {
  return paths.map((entry) => `\`${entry.relativePath}\``).join(', ');
}

function buildAdapterDetail({ label, tool, selectedScript }) {
  if (!selectedScript) {
    return tool?.available || tool?.declared
      ? `${label} is declared or installed, but no repo-owned package.json script wires it into CI yet.`
      : `No repo-owned ${label} script lane was detected.`;
  }

  if (selectedScript.missingRepoOwnedPaths.length > 0) {
    return `Found repo-owned ${label} script \`${selectedScript.name}\`, but it references missing repo-owned file(s): ${summarizeRepoOwnedPaths(selectedScript.missingRepoOwnedPaths)}.`;
  }

  if (selectedScript.repoOwnedPaths.length > 0) {
    return `Found repo-owned ${label} script \`${selectedScript.name}\` with adapter file(s): ${summarizeRepoOwnedPaths(selectedScript.repoOwnedPaths)}.`;
  }

  return `Found repo-owned ${label} script \`${selectedScript.name}\`.`;
}

async function buildAdapterLane({
  repoDir,
  runtimeSupport,
  key,
  id,
  label,
  tool,
  scripts = [],
}) {
  const annotatedScripts = await annotateScripts({
    repoDir,
    runtimeSupport,
    scripts,
  });
  const selectedScript = annotatedScripts[0] ?? null;
  const command = selectedScript?.command ?? buildScriptCommand(runtimeSupport, '');
  const repoOwnedPaths = selectedScript?.repoOwnedPaths ?? [];
  const missingRepoOwnedPaths = selectedScript?.missingRepoOwnedPaths ?? [];
  const runnable = Boolean(selectedScript) && missingRepoOwnedPaths.length === 0;

  return {
    key,
    id,
    label,
    tool,
    scripts: annotatedScripts,
    scriptName: selectedScript?.name ?? '',
    selectedScript,
    command,
    repoOwnedPaths,
    missingRepoOwnedPaths,
    runnable,
    runnableInThisCheckout: Boolean(selectedScript?.runnableInThisCheckout),
    status: runnable ? 'pass' : selectedScript ? 'warn' : 'info',
    detail: buildAdapterDetail({
      label,
      tool,
      selectedScript,
    }),
  };
}

export function getAdapterLane(adapterSupport, key) {
  return adapterSupport?.adapters?.[key] ?? null;
}

export function getAdapterScriptName(adapterSupport, key, { exclude = [] } = {}) {
  const excluded = new Set(uniqueStrings(exclude));
  const lane = getAdapterLane(adapterSupport, key);
  return lane?.runnable && lane.scriptName && !excluded.has(lane.scriptName)
    ? lane.scriptName
    : '';
}

export async function detectAdapterSupport({
  repoDir = process.cwd(),
  runtimeSupport,
  ecosystemSupport,
  testingFrameworkSupport,
} = {}) {
  const resolvedRepoDir = path.resolve(repoDir);
  const detectedRuntimeSupport = runtimeSupport ?? await detectRepoRuntime({ repoDir: resolvedRepoDir });
  const detectedEcosystemSupport = ecosystemSupport ?? await detectEcosystemSupport({ repoDir: resolvedRepoDir });
  const detectedTestingFrameworkSupport = testingFrameworkSupport ?? await detectTestingFrameworkSupport({ repoDir: resolvedRepoDir });
  const adapters = {
    obsidianE2E: await buildAdapterLane({
      repoDir: resolvedRepoDir,
      runtimeSupport: detectedRuntimeSupport,
      key: 'obsidianE2E',
      id: 'obsidian-e2e',
      label: 'obsidian-e2e',
      tool: detectedEcosystemSupport.tools.obsidianE2E,
      scripts: detectedEcosystemSupport.tools.obsidianE2E.scripts,
    }),
    testingFramework: await buildAdapterLane({
      repoDir: resolvedRepoDir,
      runtimeSupport: detectedRuntimeSupport,
      key: 'testingFramework',
      id: 'obsidian-testing-framework',
      label: 'obsidian-testing-framework',
      tool: detectedTestingFrameworkSupport,
      scripts: detectedTestingFrameworkSupport.scripts,
    }),
    wdioObsidianService: await buildAdapterLane({
      repoDir: resolvedRepoDir,
      runtimeSupport: detectedRuntimeSupport,
      key: 'wdioObsidianService',
      id: 'wdio-obsidian-service',
      label: 'wdio-obsidian-service',
      tool: detectedEcosystemSupport.tools.wdioObsidianService,
      scripts: detectedEcosystemSupport.tools.wdioObsidianService.scripts,
    }),
  };

  return {
    repoDir: resolvedRepoDir,
    packageManager: detectedRuntimeSupport?.inference?.manager ?? 'npm',
    adapters,
    orderedAdapterIds: [
      adapters.obsidianE2E.id,
      adapters.testingFramework.id,
      adapters.wdioObsidianService.id,
    ],
  };
}
