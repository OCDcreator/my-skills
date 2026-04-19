import path from 'node:path';
import { detectEcosystemSupport } from './obsidian_debug_ecosystem_support.mjs';
import {
  buildRunCommand,
  detectRepoRuntime,
  formatCommandTokens,
} from './obsidian_debug_repo_runtime.mjs';

const COREPACK_MANAGERS = new Set(['pnpm', 'yarn']);

function uniqueStrings(values) {
  return [...new Set(
    values
      .map((entry) => String(entry ?? '').trim())
      .filter((entry) => entry.length > 0),
  )];
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

function getScriptBody(runtimeSupport, scriptName) {
  if (!scriptName) {
    return null;
  }

  const body = runtimeSupport?.scripts?.scriptBodies?.[scriptName];
  return typeof body === 'string' ? body : null;
}

function buildScriptCommand(runtimeSupport, scriptName) {
  const normalizedScript = String(scriptName ?? '').trim();
  const manager = runtimeSupport?.inference?.manager ?? 'npm';
  const body = getScriptBody(runtimeSupport, normalizedScript);
  if (!normalizedScript || body === null) {
    return {
      script: normalizedScript,
      exists: false,
      body: null,
      available: false,
      command: [],
      rendered: '',
      previewCommand: [],
      previewRendered: '',
      detail: normalizedScript
        ? `package.json scripts.${normalizedScript} is not defined.`
        : 'No package.json script was selected.',
    };
  }

  const runnable = buildRunCommand(manager, normalizedScript, runtimeSupport?.tools ?? {});
  const preview = previewScriptCommand(manager, normalizedScript);
  return {
    script: normalizedScript,
    exists: true,
    body,
    available: runnable.available,
    via: runnable.via,
    command: runnable.command,
    rendered: runnable.rendered,
    previewCommand: preview.command,
    previewRendered: preview.rendered,
    detail: runnable.available
      ? `Ready to run ${preview.rendered} before build/deploy.`
      : runnable.detail,
  };
}

function firstScriptName(scripts = []) {
  return scripts
    .map((entry) => entry?.name)
    .find((entry) => typeof entry === 'string' && entry.trim().length > 0) ?? '';
}

function chooseLintScript(runtimeSupport, ecosystemSupport) {
  if (runtimeSupport?.scripts?.important?.lint?.exists) {
    return 'lint';
  }

  return firstScriptName(ecosystemSupport?.tools?.eslintObsidianmd?.scripts);
}

function choosePluginEntryScript(ecosystemSupport) {
  return firstScriptName(ecosystemSupport?.scripts?.pluginEntryValidation?.scripts);
}

function buildLintGate(runtimeSupport, ecosystemSupport) {
  const scriptName = chooseLintScript(runtimeSupport, ecosystemSupport);
  const command = buildScriptCommand(runtimeSupport, scriptName);
  const eslintTool = ecosystemSupport?.tools?.eslintObsidianmd;
  const declaredOrInstalled = Boolean(eslintTool?.available || eslintTool?.declared);
  const remediationHints = uniqueStrings([
    command.exists
      ? 'Run the repo-owned lint script before build/deploy to catch manifest and generated-template issues early.'
      : '',
    command.exists && !declaredOrInstalled
      ? 'Install or wire eslint-plugin-obsidianmd only when the repository wants official Obsidian lint coverage.'
      : '',
    !command.exists && declaredOrInstalled
      ? 'Add or reuse a package.json lint script before build/deploy instead of inventing a parallel command.'
      : '',
    !command.exists && !declaredOrInstalled
      ? 'No lint preflight is required until the repository owns one.'
      : '',
    command.exists && !command.available
      ? command.detail
      : '',
  ]);

  return {
    id: 'lint',
    label: 'repo-owned lint',
    category: 'lint',
    phase: 'pre-build',
    present: command.exists,
    status: command.exists ? 'pass' : 'info',
    scriptName: command.exists ? command.script : '',
    scriptBody: command.body,
    command,
    remediationHints,
    detail: command.exists
      ? `Use ${command.previewRendered} as the first reusable pre-build gate.`
      : 'No repo-owned lint preflight script was detected.',
    tool: eslintTool,
  };
}

function buildPluginEntryGate(runtimeSupport, ecosystemSupport) {
  const scriptName = choosePluginEntryScript(ecosystemSupport);
  const command = buildScriptCommand(runtimeSupport, scriptName);
  const remediationHints = uniqueStrings([
    command.exists
      ? 'Run plugin-entry validation after lint and before build/deploy to catch ReviewBot-style manifest or submission residue early.'
      : '',
    command.exists && !command.available
      ? command.detail
      : '',
    !command.exists
      ? 'Keep plugin-entry validation optional; add a repo-owned package.json script only when the repository wants this ReviewBot-style gate.'
      : '',
  ]);

  return {
    id: 'plugin-entry-validation',
    label: 'plugin-entry validation',
    category: 'ci',
    phase: 'pre-build',
    present: command.exists,
    status: command.exists ? 'pass' : 'info',
    scriptName: command.exists ? command.script : '',
    scriptBody: command.body,
    command,
    remediationHints,
    detail: command.exists
      ? `Use ${command.previewRendered} as an optional ReviewBot-style pre-build gate.`
      : 'No repo-owned plugin-entry validation preflight script was detected.',
    probe: ecosystemSupport?.scripts?.pluginEntryValidation,
  };
}

export function getPreflightGate(preflightSupport, id) {
  return preflightSupport?.gates?.find((gate) => gate.id === id) ?? null;
}

export function getPreflightScriptName(preflightSupport, id, { exclude = [] } = {}) {
  const excluded = new Set(uniqueStrings(exclude));
  const scriptName = getPreflightGate(preflightSupport, id)?.scriptName ?? '';
  return scriptName && !excluded.has(scriptName) ? scriptName : '';
}

export async function detectPreflightSupport({
  repoDir = process.cwd(),
  runtimeSupport,
  ecosystemSupport,
} = {}) {
  const resolvedRepoDir = path.resolve(repoDir);
  const detectedRuntimeSupport = runtimeSupport ?? await detectRepoRuntime({ repoDir: resolvedRepoDir });
  const detectedEcosystemSupport = ecosystemSupport ?? await detectEcosystemSupport({ repoDir: resolvedRepoDir });
  const gates = [
    buildLintGate(detectedRuntimeSupport, detectedEcosystemSupport),
    buildPluginEntryGate(detectedRuntimeSupport, detectedEcosystemSupport),
  ];

  return {
    repoDir: resolvedRepoDir,
    packageManager: detectedRuntimeSupport?.inference?.manager ?? 'npm',
    gates,
    orderedGateIds: gates.map((gate) => gate.id),
    preBuildScriptNames: gates
      .map((gate) => gate.scriptName)
      .filter((scriptName, index, names) => scriptName && names.indexOf(scriptName) === index),
  };
}
