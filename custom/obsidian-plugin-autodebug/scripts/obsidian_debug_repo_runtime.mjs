import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';

const SUPPORTED_PACKAGE_MANAGERS = ['npm', 'pnpm', 'yarn', 'bun'];
const COREPACK_MANAGERS = new Set(['pnpm', 'yarn']);
const IMPORTANT_SCRIPTS = ['build', 'dev', 'test', 'lint'];
const LOCKFILE_DEFINITIONS = [
  { name: 'package-lock.json', manager: 'npm', evidence: 'lockfile' },
  { name: 'npm-shrinkwrap.json', manager: 'npm', evidence: 'lockfile' },
  { name: 'pnpm-lock.yaml', manager: 'pnpm', evidence: 'lockfile' },
  { name: 'pnpm-workspace.yaml', manager: 'pnpm', evidence: 'workspace' },
  { name: 'yarn.lock', manager: 'yarn', evidence: 'lockfile' },
  { name: 'bun.lockb', manager: 'bun', evidence: 'lockfile' },
  { name: 'bun.lock', manager: 'bun', evidence: 'lockfile' },
];

export async function readJsonFileOrNull(filePath) {
  try {
    return JSON.parse((await fs.readFile(filePath, 'utf8')).replace(/^\uFEFF/, ''));
  } catch {
    return null;
  }
}

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

function sanitizeVersionText(text) {
  return String(text ?? '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line.length > 0) ?? '';
}

function probeTool(command, timeoutMs = 5000) {
  return new Promise((resolve) => {
    const child = spawn(command, ['--version'], {
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    let settled = false;
    const timeout = setTimeout(() => {
      if (settled) {
        return;
      }
      settled = true;
      child.kill();
      resolve({
        name: command,
        available: false,
        version: null,
        detail: `${command} timed out while reporting --version`,
      });
    }, timeoutMs);

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    child.on('error', (error) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timeout);
      resolve({
        name: command,
        available: false,
        version: null,
        detail: error.message,
      });
    });
    child.on('close', (code) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timeout);
      const version = sanitizeVersionText(stdout) || sanitizeVersionText(stderr) || null;
      resolve({
        name: command,
        available: code === 0,
        version,
        detail: code === 0
          ? version ? `${command} ${version}` : `${command} is available`
          : sanitizeVersionText(stderr) || sanitizeVersionText(stdout) || `${command} exited with code ${code}`,
      });
    });
  });
}

function parsePackageManagerField(value) {
  if (typeof value !== 'string' || value.trim().length === 0) {
    return null;
  }

  const raw = value.trim();
  const separatorIndex = raw.lastIndexOf('@');
  if (separatorIndex <= 0 || separatorIndex === raw.length - 1) {
    return {
      raw,
      name: raw,
      version: null,
      supported: SUPPORTED_PACKAGE_MANAGERS.includes(raw),
      valid: false,
    };
  }

  const name = raw.slice(0, separatorIndex);
  const version = raw.slice(separatorIndex + 1);
  return {
    raw,
    name,
    version,
    supported: SUPPORTED_PACKAGE_MANAGERS.includes(name),
    valid: true,
  };
}

function collectScripts(packageJson) {
  const scripts = packageJson?.scripts && typeof packageJson.scripts === 'object' && !Array.isArray(packageJson.scripts)
    ? packageJson.scripts
    : {};
  const names = Object.entries(scripts)
    .filter(([, value]) => typeof value === 'string' && value.trim().length > 0)
    .map(([name]) => name)
    .sort();
  const important = Object.fromEntries(IMPORTANT_SCRIPTS.map((name) => [
    name,
    {
      exists: names.includes(name),
      body: typeof scripts[name] === 'string' ? scripts[name] : null,
    },
  ]));

  return {
    names,
    important,
    scriptBodies: Object.fromEntries(names.map((name) => [name, scripts[name]])),
  };
}

function addEvidence(scores, reasons, manager, weight, detail) {
  scores.set(manager, (scores.get(manager) ?? 0) + weight);
  reasons.set(manager, [...(reasons.get(manager) ?? []), detail]);
}

function inferPackageManager({ packageManagerField, lockfiles }) {
  const scores = new Map();
  const reasons = new Map();

  if (packageManagerField?.supported) {
    addEvidence(
      scores,
      reasons,
      packageManagerField.name,
      6,
      packageManagerField.version
        ? `package.json packageManager=${packageManagerField.name}@${packageManagerField.version}`
        : `package.json packageManager=${packageManagerField.name}`,
    );
  }

  for (const lockfile of lockfiles) {
    addEvidence(
      scores,
      reasons,
      lockfile.manager,
      lockfile.evidence === 'workspace' ? 2 : 4,
      `${lockfile.name} (${lockfile.manager})`,
    );
  }

  const ranked = [...scores.entries()].sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]));
  if (ranked.length === 0) {
    return {
      manager: 'npm',
      confidence: 'low',
      reasons: ['No packageManager field or package-manager lockfile was found; falling back to npm because it ships with Node.'],
      conflicts: [],
      source: 'fallback',
      weak: true,
    };
  }

  const [manager, score] = ranked[0];
  const secondScore = ranked[1]?.[1] ?? 0;
  const conflicts = ranked.filter(([name, value]) => name !== manager && value > 0 && value >= score - 1).map(([name]) => name);
  let confidence = 'medium';
  if (score >= 8 && secondScore <= 4) {
    confidence = 'high';
  } else if (score <= 4 || conflicts.length > 0) {
    confidence = 'low';
  }

  return {
    manager,
    confidence,
    reasons: reasons.get(manager) ?? [],
    conflicts,
    source: packageManagerField?.name === manager ? 'packageManager-field' : 'lockfile',
    weak: confidence === 'low',
  };
}

function resolveCommandPrefix(manager, tools) {
  if (!manager) {
    return {
      available: false,
      via: 'missing',
      command: [],
      detail: 'No package manager was inferred.',
    };
  }

  if (tools[manager]?.available) {
    return {
      available: true,
      via: 'direct',
      command: [manager],
      detail: tools[manager].detail,
    };
  }

  if (COREPACK_MANAGERS.has(manager) && tools.corepack?.available) {
    return {
      available: true,
      via: 'corepack',
      command: ['corepack', manager],
      detail: `${manager} is not on PATH, but ${tools.corepack.detail} can launch it.`,
    };
  }

  const remediation = COREPACK_MANAGERS.has(manager)
    ? `Install ${manager} or enable Corepack for this Node runtime.`
    : `Install ${manager} before relying on inferred script execution.`;
  return {
    available: false,
    via: 'missing',
    command: [],
    detail: `${manager} is not available in PATH. ${remediation}`,
  };
}

export function buildRunCommand(manager, scriptName, tools) {
  const prefix = resolveCommandPrefix(manager, tools);
  if (!prefix.available) {
    return {
      available: false,
      via: prefix.via,
      command: [],
      rendered: '',
      detail: prefix.detail,
    };
  }

  return {
    available: true,
    via: prefix.via,
    command: [...prefix.command, 'run', scriptName],
    rendered: formatCommandTokens([...prefix.command, 'run', scriptName]),
    detail: prefix.detail,
  };
}

export function formatCommandTokens(tokens = []) {
  return tokens
    .map((token) => (/\s/.test(token) ? JSON.stringify(token) : token))
    .join(' ')
    .trim();
}

export async function detectRepoRuntime({ repoDir, probeTools = true } = {}) {
  const resolvedRepoDir = path.resolve(repoDir ?? process.cwd());
  const packageJsonPath = path.join(resolvedRepoDir, 'package.json');
  const packageJson = await readJsonFileOrNull(packageJsonPath);
  const packageManagerField = parsePackageManagerField(packageJson?.packageManager);
  const scripts = collectScripts(packageJson);
  const lockfiles = [];

  for (const definition of LOCKFILE_DEFINITIONS) {
    const lockfilePath = path.join(resolvedRepoDir, definition.name);
    if (await exists(lockfilePath)) {
      lockfiles.push({
        ...definition,
        path: lockfilePath,
      });
    }
  }

  const tools = {
    node: {
      name: 'node',
      available: true,
      version: process.versions.node,
      detail: `node ${process.versions.node}`,
    },
    corepack: {
      name: 'corepack',
      available: false,
      version: null,
      detail: 'corepack was not probed',
    },
    npm: {
      name: 'npm',
      available: false,
      version: null,
      detail: 'npm was not probed',
    },
    pnpm: {
      name: 'pnpm',
      available: false,
      version: null,
      detail: 'pnpm was not probed',
    },
    yarn: {
      name: 'yarn',
      available: false,
      version: null,
      detail: 'yarn was not probed',
    },
    bun: {
      name: 'bun',
      available: false,
      version: null,
      detail: 'bun was not probed',
    },
  };

  if (probeTools) {
    const [corepack, npm, pnpm, yarn, bun] = await Promise.all([
      probeTool('corepack'),
      probeTool('npm'),
      probeTool('pnpm'),
      probeTool('yarn'),
      probeTool('bun'),
    ]);
    tools.corepack = corepack;
    tools.npm = npm;
    tools.pnpm = pnpm;
    tools.yarn = yarn;
    tools.bun = bun;
  }

  const inference = inferPackageManager({ packageManagerField, lockfiles });
  const commands = Object.fromEntries(IMPORTANT_SCRIPTS.map((scriptName) => {
    const script = scripts.important[scriptName];
    if (!script?.exists) {
      return [scriptName, {
        script: scriptName,
        exists: false,
        available: false,
        command: [],
        rendered: '',
        detail: `package.json scripts.${scriptName} is not defined`,
      }];
    }

    const command = buildRunCommand(inference.manager, scriptName, tools);
    return [scriptName, {
      script: scriptName,
      exists: true,
      body: script.body,
      ...command,
    }];
  }));

  const inferredManager = inference.manager;
  const corepackRelevant = COREPACK_MANAGERS.has(inferredManager);
  const managerAvailable = Boolean(tools[inferredManager]?.available);
  const corepackReady = managerAvailable || (corepackRelevant && Boolean(tools.corepack?.available));

  return {
    repoDir: resolvedRepoDir,
    packageJsonPath,
    packageJson,
    packageManagerField,
    lockfiles,
    scripts,
    tools,
    inference,
    commands,
    runtime: {
      inferredManager,
      corepackRelevant,
      managerAvailable,
      corepackReady,
    },
  };
}
