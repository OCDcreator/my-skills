import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  ensureParentDirectory,
  getStringOption,
  hasHelpOption,
  parseArgs,
  printHelpAndExit,
} from './obsidian_cdp_common.mjs';

const DEPENDENCY_FIELDS = ['dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies'];
const SCAN_EXTENSIONS = new Set([
  '.js',
  '.mjs',
  '.cjs',
  '.ts',
  '.mts',
  '.cts',
  '.jsx',
  '.tsx',
  '.json',
  '.md',
  '.yaml',
  '.yml',
]);
const SKIP_DIRS = new Set([
  '.git',
  'node_modules',
  '.obsidian',
  '.obsidian-debug',
  '.cache',
  '.tmp',
]);

const SIGNAL_DEFINITIONS = [
  {
    id: 'mcp',
    label: 'MCP',
    packagePatterns: [/@modelcontextprotocol\//i, /\bmcp\b/i],
    scriptPatterns: [/\bmcp\b/i, /model[-:_ ]context[-:_ ]protocol/i],
    filePatterns: [/@modelcontextprotocol\//i, /\bmodel context protocol\b/i, /\bmcp(?:server|client|tool|transport)?\b/i],
    vaultPatterns: [/\bmcp\b/i, /model[-:_ ]context[-:_ ]protocol/i],
  },
  {
    id: 'rest',
    label: 'REST',
    packagePatterns: [/^axios$/i, /^got$/i, /^node-fetch$/i, /^undici$/i, /^superagent$/i],
    scriptPatterns: [/\bapi\b/i, /\brest\b/i, /\bhttp\b/i],
    filePatterns: [/\bfetch\s*\(/i, /\baxios\s*\(/i, /\bhttps?:\/\/[^\s'"`]+/i, /\b(app|router)\.(get|post|put|patch|delete)\s*\(/i],
    vaultPatterns: [/\bapi\b/i, /\brest\b/i, /\bhttp\b/i],
  },
  {
    id: 'devtools',
    label: 'DevTools',
    packagePatterns: [/^chrome-remote-interface$/i, /\bdevtools?\b/i],
    scriptPatterns: [/\bdevtools?\b/i, /\bcdp\b/i, /remote[-:_ ]debug/i],
    filePatterns: [/\bdevtools?\b/i, /\bchrome devtools protocol\b/i, /\bcdp\b/i, /--remote-debugging-port/i, /json\/list/i],
    vaultPatterns: [/\bdevtools?\b/i, /\bhot[-:_ ]reload\b/i, /\bcdp\b/i],
  },
  {
    id: 'aiPlugin',
    label: 'AI plugin',
    packagePatterns: [/^openai$/i, /^anthropic$/i, /^@anthropic-ai\//i, /^@google\/genai$/i, /^langchain/i, /\bllm\b/i],
    scriptPatterns: [/\bai\b/i, /\bllm\b/i, /\bprompt\b/i, /\bmodel\b/i],
    filePatterns: [/\bopenai\b/i, /\banthropic\b/i, /\bchat\.completions\b/i, /\bprompt\b/i, /\bembeddings?\b/i, /\bllm\b/i, /\bmodel\b/i],
    vaultPatterns: [/\bai\b/i, /\bllm\b/i, /\bagent\b/i, /\bmcp\b/i],
  },
];

function uniqueStrings(values) {
  return [...new Set(
    values
      .map((value) => String(value ?? '').trim())
      .filter((value) => value.length > 0),
  )];
}

function normalizePath(value) {
  return String(value ?? '').replaceAll('\\', '/');
}

function asRegex(pattern) {
  if (pattern instanceof RegExp) {
    return new RegExp(pattern.source, pattern.flags.includes('i') ? pattern.flags : `${pattern.flags}i`);
  }
  return new RegExp(String(pattern), 'i');
}

function toRelativePath(repoDir, filePath) {
  const relativePath = path.relative(repoDir, filePath);
  return normalizePath(relativePath.startsWith('..') ? filePath : relativePath);
}

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function readJsonIfExists(filePath) {
  try {
    return JSON.parse((await fs.readFile(filePath, 'utf8')).replace(/^\uFEFF/, ''));
  } catch {
    return null;
  }
}

function firstPatternHit(text, patterns) {
  for (const pattern of patterns) {
    const regex = asRegex(pattern);
    const match = regex.exec(text);
    if (match) {
      return {
        pattern: regex.toString(),
        index: match.index,
        match: String(match[0] ?? '').slice(0, 140),
      };
    }
  }
  return null;
}

function linePreview(text, index) {
  if (!Number.isFinite(index) || index < 0) {
    return { line: null, preview: null };
  }

  const source = String(text ?? '');
  let line = 1;
  let lineStart = 0;
  for (let cursor = 0; cursor < source.length && cursor < index; cursor += 1) {
    if (source[cursor] === '\n') {
      line += 1;
      lineStart = cursor + 1;
    }
  }

  let lineEnd = source.indexOf('\n', lineStart);
  if (lineEnd < 0) {
    lineEnd = source.length;
  }
  const preview = source.slice(lineStart, lineEnd).trim().slice(0, 220);
  return {
    line,
    preview: preview.length > 0 ? preview : null,
  };
}

function pushEvidence(store, signalId, evidence) {
  if (!store[signalId]) {
    store[signalId] = [];
  }

  const entry = {
    heuristic: true,
    ...evidence,
  };
  const dedupeKey = JSON.stringify([
    entry.kind ?? '',
    entry.source ?? '',
    entry.field ?? '',
    entry.name ?? '',
    entry.script ?? '',
    entry.pattern ?? '',
    entry.match ?? '',
    entry.line ?? '',
  ]);
  if (!store[signalId].some((candidate) => {
    const candidateKey = JSON.stringify([
      candidate.kind ?? '',
      candidate.source ?? '',
      candidate.field ?? '',
      candidate.name ?? '',
      candidate.script ?? '',
      candidate.pattern ?? '',
      candidate.match ?? '',
      candidate.line ?? '',
    ]);
    return candidateKey === dedupeKey;
  })) {
    store[signalId].push(entry);
  }
}

async function collectFiles(rootDir, { maxFiles = 240 } = {}) {
  const files = [];

  async function walk(currentDir) {
    if (files.length >= maxFiles) {
      return;
    }

    let entries = [];
    try {
      entries = await fs.readdir(currentDir, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      if (files.length >= maxFiles) {
        return;
      }

      const absolutePath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        if (SKIP_DIRS.has(entry.name)) {
          continue;
        }
        await walk(absolutePath);
        continue;
      }

      if (!entry.isFile()) {
        continue;
      }

      const extension = path.extname(entry.name).toLowerCase();
      if (!SCAN_EXTENSIONS.has(extension) && !['manifest.json', 'package.json'].includes(entry.name.toLowerCase())) {
        continue;
      }

      files.push(absolutePath);
    }
  }

  await walk(rootDir);
  return files;
}

function collectPackageEvidence(signalMap, packageJson, signalDefinition) {
  for (const field of DEPENDENCY_FIELDS) {
    const deps = packageJson?.[field];
    if (!deps || typeof deps !== 'object' || Array.isArray(deps)) {
      continue;
    }
    for (const [name, version] of Object.entries(deps)) {
      const hit = firstPatternHit(name, signalDefinition.packagePatterns);
      if (!hit) {
        continue;
      }
      pushEvidence(signalMap, signalDefinition.id, {
        kind: 'package-dependency',
        source: 'package.json',
        field,
        name,
        version: typeof version === 'string' ? version : null,
        pattern: hit.pattern,
        match: hit.match,
      });
    }
  }

  const scripts = packageJson?.scripts;
  if (scripts && typeof scripts === 'object' && !Array.isArray(scripts)) {
    for (const [name, body] of Object.entries(scripts)) {
      if (typeof body !== 'string' || body.trim().length === 0) {
        continue;
      }
      const scriptHit = firstPatternHit(`${name}\n${body}`, signalDefinition.scriptPatterns);
      if (!scriptHit) {
        continue;
      }
      pushEvidence(signalMap, signalDefinition.id, {
        kind: 'package-script',
        source: 'package.json',
        script: name,
        command: body.trim(),
        pattern: scriptHit.pattern,
        match: scriptHit.match,
      });
    }
  }
}

function confidenceForEvidence(evidence = []) {
  if (evidence.length === 0) {
    return 'none';
  }
  const kinds = new Set(evidence.map((entry) => entry.kind));
  if (kinds.size >= 2 || evidence.length >= 3) {
    return 'medium';
  }
  return 'low';
}

async function collectVaultSignals({
  testVaultPluginDir,
  signalMap,
  definitions,
  errors,
}) {
  const normalizedDir = String(testVaultPluginDir ?? '').trim();
  if (!normalizedDir) {
    return {
      scanned: false,
      exists: false,
      pluginCount: 0,
      pluginIds: [],
      detail: 'No test-vault plugin directory was provided; vault-side heuristics were skipped.',
    };
  }

  const resolvedDir = path.resolve(normalizedDir);
  if (!await exists(resolvedDir)) {
    return {
      scanned: true,
      exists: false,
      pluginCount: 0,
      pluginIds: [],
      detail: `Test-vault plugin directory was provided but does not exist: ${resolvedDir}`,
    };
  }

  let entries = [];
  try {
    entries = await fs.readdir(resolvedDir, { withFileTypes: true });
  } catch (error) {
    errors.push(`Failed to read test-vault plugin directory: ${error instanceof Error ? error.message : String(error)}`);
    return {
      scanned: true,
      exists: true,
      pluginCount: 0,
      pluginIds: [],
      detail: `Unable to read test-vault plugin directory: ${resolvedDir}`,
    };
  }

  const pluginIds = [];
  for (const entry of entries) {
    if (!entry.isDirectory()) {
      continue;
    }

    const pluginDir = path.join(resolvedDir, entry.name);
    const manifest = await readJsonIfExists(path.join(pluginDir, 'manifest.json'));
    const pluginId = String(manifest?.id ?? entry.name).trim();
    if (pluginId.length === 0) {
      continue;
    }
    pluginIds.push(pluginId);
    const pluginLabel = `${pluginId} (${normalizePath(path.relative(resolvedDir, pluginDir))})`;
    for (const definition of definitions) {
      const hit = firstPatternHit(pluginId, definition.vaultPatterns);
      if (hit) {
        pushEvidence(signalMap, definition.id, {
          kind: 'vault-plugin',
          source: normalizePath(path.join(path.basename(resolvedDir), entry.name, 'manifest.json')),
          name: pluginId,
          pattern: hit.pattern,
          match: hit.match,
          detail: `Matched plugin id ${pluginLabel}`,
        });
      }
    }
  }

  return {
    scanned: true,
    exists: true,
    pluginCount: pluginIds.length,
    pluginIds: uniqueStrings(pluginIds).sort((left, right) => left.localeCompare(right)),
    detail: pluginIds.length > 0
      ? `Scanned ${pluginIds.length} plugin directories from the provided test-vault plugin path.`
      : 'The provided test-vault plugin directory exists but no plugin directories were discovered.',
  };
}

export async function detectAgenticSupport({
  repoDir = process.cwd(),
  testVaultPluginDir = '',
  maxFiles = 240,
} = {}) {
  const resolvedRepoDir = path.resolve(repoDir);
  const packageJsonPath = path.join(resolvedRepoDir, 'package.json');
  const packageJson = await readJsonIfExists(packageJsonPath);
  const files = await collectFiles(resolvedRepoDir, { maxFiles });
  const signalEvidence = {};
  const errors = [];
  let filesRead = 0;

  for (const definition of SIGNAL_DEFINITIONS) {
    collectPackageEvidence(signalEvidence, packageJson, definition);
  }

  for (const filePath of files) {
    let text = '';
    try {
      const stat = await fs.stat(filePath);
      if (!stat.isFile() || stat.size > 512 * 1024) {
        continue;
      }
      text = await fs.readFile(filePath, 'utf8');
      filesRead += 1;
    } catch (error) {
      errors.push(`Skipped ${toRelativePath(resolvedRepoDir, filePath)}: ${error instanceof Error ? error.message : String(error)}`);
      continue;
    }

    for (const definition of SIGNAL_DEFINITIONS) {
      const hit = firstPatternHit(text, definition.filePatterns);
      if (!hit) {
        continue;
      }
      const preview = linePreview(text, hit.index);
      pushEvidence(signalEvidence, definition.id, {
        kind: 'file-pattern',
        source: toRelativePath(resolvedRepoDir, filePath),
        pattern: hit.pattern,
        match: hit.match,
        line: preview.line,
        preview: preview.preview,
      });
    }
  }

  const vault = await collectVaultSignals({
    testVaultPluginDir,
    signalMap: signalEvidence,
    definitions: SIGNAL_DEFINITIONS,
    errors,
  });

  const signals = Object.fromEntries(SIGNAL_DEFINITIONS.map((definition) => {
    const evidence = (signalEvidence[definition.id] ?? []).slice(0, 20);
    const present = evidence.length > 0;
    return [
      definition.id,
      {
        id: definition.id,
        label: definition.label,
        heuristic: true,
        present,
        confidence: confidenceForEvidence(evidence),
        detail: present
          ? `Heuristic ${definition.label} signal(s) detected from repo and optional vault context.`
          : `No heuristic ${definition.label} signals were detected in scanned files.`,
        evidence,
      },
    ];
  }));

  const detectedSignals = SIGNAL_DEFINITIONS
    .map((definition) => definition.id)
    .filter((id) => signals[id]?.present);
  const undetectedSignals = SIGNAL_DEFINITIONS
    .map((definition) => definition.id)
    .filter((id) => !signals[id]?.present);
  const heuristicHits = Object.values(signals).reduce((count, entry) => count + (entry.evidence?.length ?? 0), 0);

  return {
    generatedAt: new Date().toISOString(),
    heuristicsDisclaimer: 'Heuristic signals only; this output is not proof of runtime behavior, correctness, or production readiness.',
    repoDir: resolvedRepoDir,
    packageJsonPath,
    testVaultPluginDir: testVaultPluginDir ? path.resolve(testVaultPluginDir) : null,
    scan: {
      maxFiles,
      candidateFiles: files.length,
      filesRead,
      skippedDirectories: [...SKIP_DIRS],
      extensions: [...SCAN_EXTENSIONS],
    },
    vault,
    signals,
    summary: {
      detectedSignalCount: detectedSignals.length,
      detectedSignals,
      undetectedSignals,
      heuristicHits,
      warningCount: 0,
      errorCount: errors.length,
    },
    errors: errors.slice(0, 50),
  };
}

async function runCli() {
  const options = parseArgs(process.argv.slice(2));
  if (hasHelpOption(options)) {
    printHelpAndExit(`
Usage: node scripts/obsidian_debug_agentic_support.mjs [options]

Options:
  --repo-dir <path>                 Plugin repo directory. Defaults to cwd.
  --test-vault-plugin-dir <path>    Optional test-vault community plugin directory.
  --output <path>                   Optional JSON output path.
`);
  }

  const repoDir = path.resolve(getStringOption(options, 'repo-dir', process.cwd()));
  const testVaultPluginDir = getStringOption(options, 'test-vault-plugin-dir', '').trim();
  const outputPath = getStringOption(options, 'output', '').trim();
  const report = await detectAgenticSupport({
    repoDir,
    testVaultPluginDir,
  });

  if (outputPath) {
    const resolvedOutput = path.resolve(outputPath);
    await ensureParentDirectory(resolvedOutput);
    await fs.writeFile(resolvedOutput, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  }

  console.log(JSON.stringify(report, null, 2));
}

const isDirectRun = process.argv[1]
  && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
if (isDirectRun) {
  await runCli();
}
