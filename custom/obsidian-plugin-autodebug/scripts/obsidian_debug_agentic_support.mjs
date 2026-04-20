import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  ensureParentDirectory,
  getNumberOption,
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
    packagePatterns: [/@modelcontextprotocol\//i, /\bmcp\b/i, /vault[-_]?mcp/i, /claudesidian/i],
    scriptPatterns: [/\bmcp\b/i, /model[-:_ ]context[-:_ ]protocol/i, /tools\/list/i],
    filePatterns: [/@modelcontextprotocol\//i, /\bmodel context protocol\b/i, /\bmcp(?:server|client|tool|transport)?\b/i, /tools\/list/i],
    vaultPatterns: [/\bmcp\b/i, /model[-:_ ]context[-:_ ]protocol/i, /vault[-_]?mcp/i, /nexus/i, /claudesidian/i],
  },
  {
    id: 'rest',
    label: 'REST',
    packagePatterns: [/^axios$/i, /^got$/i, /^node-fetch$/i, /^undici$/i, /^superagent$/i, /obsidian[-_]?cli[-_]?rest/i],
    scriptPatterns: [/\bapi\b/i, /\brest\b/i, /\bhttp\b/i, /obsidian[-_]?cli[-_]?rest/i],
    filePatterns: [/\bfetch\s*\(/i, /\brequestUrl\s*\(/i, /\baxios\s*\(/i, /\bhttps?:\/\/[^\s'"`]+/i, /\b(app|router)\.(get|post|put|patch|delete)\s*\(/i, /obsidian[-_]?cli[-_]?rest/i],
    vaultPatterns: [/\bapi\b/i, /\brest\b/i, /\bhttp\b/i, /obsidian[-_]?cli[-_]?rest/i],
  },
  {
    id: 'devtools',
    label: 'DevTools',
    packagePatterns: [/^chrome-remote-interface$/i, /\bdevtools?\b/i, /chrome[-_]?devtools[-_]?mcp/i, /@playwright\/mcp/i],
    scriptPatterns: [/\bdevtools?\b/i, /\bcdp\b/i, /remote[-:_ ]debug/i, /chrome[-_]?devtools[-_]?mcp/i, /playwright[-_]?mcp/i],
    filePatterns: [/\bdevtools?\b/i, /\bchrome devtools protocol\b/i, /\bcdp\b/i, /--remote-debugging-port/i, /json\/list/i, /chrome[-_]?devtools[-_]?mcp/i, /playwright[-_]?mcp/i],
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

const AI_SAFETY_DEFINITIONS = [
  {
    id: 'secretStorage',
    label: 'SecretStorage',
    patterns: [/\bapp\.secretStorage\b/i, /\bsecretStorage\b/i, /\bSecretStorage\b/i, /\bSecretComponent\b/i],
  },
  {
    id: 'keyMaterial',
    label: 'Key/token material',
    patterns: [/\bapi[-_ ]?key\b/i, /\btoken\b/i, /\bAuthorization\b/i, /\bBearer\b/i, /\bsecret\b/i, /\bsk-[a-z0-9_-]{8,}/i],
  },
  {
    id: 'redaction',
    label: 'Redaction',
    patterns: [/\bredact(?:ed|ion)?\b/i, /\bsanitize(?:d|ForDiagnostics)?\b/i, /\bmask(?:Secret|Token|Key)?\b/i, /\bREDACTED\b/i],
  },
  {
    id: 'externalRequests',
    label: 'External requests',
    patterns: [/\brequestUrl\s*\(/i, /\bfetch\s*\(/i, /\bhttps?:\/\/(?!127\.0\.0\.1|localhost)[^\s'"`]+/i],
  },
  {
    id: 'settingsPrivacy',
    label: 'User-facing network/privacy settings',
    patterns: [/\bprivacy\b/i, /\bconsent\b/i, /\bsettings?\b/i, /\benable[A-Za-z]*(Network|Telemetry|Request)/i, /\buser[- ]visible\b/i],
  },
  {
    id: 'localPersistence',
    label: 'Local persistence',
    patterns: [/\blocalStorage\b/i, /\bsaveData\s*\(/i, /\bloadData\s*\(/i],
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

function pushPatternEvidence(store, definition, repoDir, filePath, text) {
  const hit = firstPatternHit(text, definition.patterns);
  if (!hit) {
    return;
  }

  const preview = linePreview(text, hit.index);
  pushEvidence(store, definition.id, {
    kind: 'file-pattern',
    source: toRelativePath(repoDir, filePath),
    pattern: hit.pattern,
    match: hit.match,
    line: preview.line,
    preview: preview.preview,
  });
}

function buildAiSafety(evidenceMap) {
  const checks = Object.fromEntries(AI_SAFETY_DEFINITIONS.map((definition) => {
    const evidence = (evidenceMap[definition.id] ?? []).slice(0, 20);
    return [
      definition.id,
      {
        id: definition.id,
        label: definition.label,
        heuristic: true,
        present: evidence.length > 0,
        confidence: confidenceForEvidence(evidence),
        evidence,
      },
    ];
  }));

  const keyRisk = checks.keyMaterial.present;
  const secretStorageOk = checks.secretStorage.present;
  const redactionOk = checks.redaction.present;
  const externalRequestRisk = checks.externalRequests.present;
  const settingsBoundaryOk = checks.settingsPrivacy.present;
  const warnings = [];

  if (keyRisk && !secretStorageOk) {
    warnings.push('Key/token-like settings were detected without clear SecretStorage evidence.');
  }
  if (keyRisk && !redactionOk) {
    warnings.push('Key/token-like settings were detected without clear redaction evidence.');
  }
  if (externalRequestRisk && !settingsBoundaryOk && !redactionOk) {
    warnings.push('External request hints were detected without clear user-facing settings/privacy/redaction evidence.');
  }

  return {
    heuristic: true,
    secretStorage: checks.secretStorage,
    keyMaterial: checks.keyMaterial,
    redaction: checks.redaction,
    externalRequests: checks.externalRequests,
    settingsPrivacy: checks.settingsPrivacy,
    localPersistence: checks.localPersistence,
    summary: {
      keyRisk,
      secretStorageOk,
      redactionOk,
      externalRequestRisk,
      settingsBoundaryOk,
      warningCount: warnings.length,
      warnings,
    },
  };
}

function isLocalhostUrl(rawUrl) {
  try {
    const parsed = new URL(rawUrl);
    return ['127.0.0.1', 'localhost', '::1', '[::1]'].includes(parsed.hostname);
  } catch {
    return false;
  }
}

function joinUrlPath(baseUrl, rawPath) {
  const parsed = new URL(baseUrl);
  const suffix = String(rawPath || '/').startsWith('/') ? String(rawPath || '/') : `/${rawPath}`;
  parsed.pathname = suffix;
  parsed.search = '';
  parsed.hash = '';
  return parsed.toString();
}

async function fetchJsonProbe(url, { apiKey = '', timeoutMs = 2000 } = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const headers = {};
    if (apiKey) {
      headers.Authorization = `Bearer ${apiKey}`;
    }
    const response = await fetch(url, {
      headers,
      signal: controller.signal,
    });
    const text = await response.text();
    let json = null;
    try {
      json = text ? JSON.parse(text) : null;
    } catch {
      json = null;
    }
    return {
      ok: response.ok,
      status: response.status,
      json,
      textPreview: text.slice(0, 500),
    };
  } catch (error) {
    return {
      ok: false,
      status: null,
      json: null,
      textPreview: '',
      error: error instanceof Error ? error.message : String(error),
    };
  } finally {
    clearTimeout(timeout);
  }
}

function extractToolNames(value) {
  if (!value || typeof value !== 'object') {
    return [];
  }
  const candidates = [];
  const arrays = [
    value.tools,
    value.toolWhitelist,
    value.allowedTools,
    value.whitelist,
    value.allowlist,
  ].filter(Array.isArray);

  for (const array of arrays) {
    for (const item of array) {
      if (typeof item === 'string') {
        candidates.push({ name: item });
      } else if (item && typeof item === 'object') {
        const name = item.name ?? item.id ?? item.tool ?? item.command;
        if (name) {
          candidates.push({
            name: String(name),
            description: typeof item.description === 'string' ? item.description : null,
          });
        }
      }
    }
  }

  const seen = new Set();
  return candidates.filter((entry) => {
    const key = entry.name.toLowerCase();
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function hasToolAllowlist(value) {
  if (!value || typeof value !== 'object') {
    return false;
  }
  return ['toolWhitelist', 'allowedTools', 'whitelist', 'allowlist']
    .some((key) => Array.isArray(value[key]) && value[key].length > 0);
}

async function probeRestControlSurface({
  restBaseUrl = '',
  restApiKey = '',
  restHealthPath = '/health',
  restToolsPath = '/tools',
  probeTimeoutMs = 2000,
} = {}) {
  const baseUrl = String(restBaseUrl ?? '').trim();
  if (!baseUrl) {
    return {
      configured: false,
      ok: false,
      localhost: false,
      authProvided: false,
      toolAllowlist: false,
      tools: [],
      detail: 'No REST/MCP HTTP endpoint was provided for runtime probing.',
    };
  }

  let healthUrl = '';
  let toolsUrl = '';
  try {
    healthUrl = joinUrlPath(baseUrl, restHealthPath);
    toolsUrl = joinUrlPath(baseUrl, restToolsPath);
  } catch (error) {
    return {
      configured: true,
      ok: false,
      localhost: false,
      authProvided: Boolean(restApiKey),
      toolAllowlist: false,
      tools: [],
      detail: `Invalid REST/MCP probe URL: ${error instanceof Error ? error.message : String(error)}`,
    };
  }

  const health = await fetchJsonProbe(healthUrl, { timeoutMs: probeTimeoutMs });
  const toolsProbe = await fetchJsonProbe(toolsUrl, { apiKey: restApiKey, timeoutMs: probeTimeoutMs });
  const tools = extractToolNames(toolsProbe.json);
  const toolAllowlist = hasToolAllowlist(toolsProbe.json);
  const pluginRuntimeToolNames = tools
    .map((entry) => entry.name)
    .filter((name) => /(plugin|reload|dev\.?|console|error|screenshot|dom)/i.test(name));

  return {
    configured: true,
    ok: health.ok || toolsProbe.ok,
    localhost: isLocalhostUrl(baseUrl),
    authProvided: Boolean(restApiKey),
    toolAllowlist,
    health: {
      url: healthUrl,
      ok: health.ok,
      status: health.status,
      error: health.error ?? null,
    },
    toolsEndpoint: {
      url: toolsUrl,
      ok: toolsProbe.ok,
      status: toolsProbe.status,
      error: toolsProbe.error ?? null,
    },
    tools,
    pluginRuntimeToolNames,
    authRequired: Boolean(toolsProbe.json?.authRequired) || toolsProbe.status === 401,
    detail: (health.ok || toolsProbe.ok)
      ? `REST/MCP probe reached ${isLocalhostUrl(baseUrl) ? 'localhost' : 'non-local'} endpoint with ${tools.length} tool(s) discovered.`
      : `REST/MCP probe failed for ${baseUrl}.`,
  };
}

function buildControlSurfaces({ signals, runtimeProbes }) {
  const mcpRestDetected = Boolean(signals.mcp?.present || signals.rest?.present || runtimeProbes.rest.configured);
  const devtoolsDetected = Boolean(signals.devtools?.present);

  return {
    mcpRest: {
      detected: mcpRestDetected,
      available: Boolean(runtimeProbes.rest.ok),
      source: runtimeProbes.rest.configured ? 'runtime-probe' : 'heuristic-signals',
      detail: runtimeProbes.rest.configured
        ? runtimeProbes.rest.detail
        : (mcpRestDetected ? 'MCP/REST heuristic signals were detected but runtime availability was not probed.' : 'No MCP/REST control surface signals were detected.'),
    },
    devtoolsMcp: {
      detected: devtoolsDetected,
      available: false,
      source: 'heuristic-signals',
      detail: devtoolsDetected
        ? 'DevTools/CDP/MCP-like heuristic signals were detected; attach target and MCP runtime still need confirmation.'
        : 'No DevTools MCP heuristic signals were detected.',
    },
    aiPlugin: {
      detected: Boolean(signals.aiPlugin?.present),
      available: false,
      source: 'heuristic-signals',
      detail: signals.aiPlugin?.present
        ? 'AI plugin heuristics were detected; safety checks should be reviewed before handoff.'
        : 'No AI plugin heuristics were detected.',
    },
  };
}

function buildRecommendations({ aiSafety, controlSurfaces, runtimeProbes }) {
  const recommendations = [];
  if (aiSafety.summary.keyRisk && !aiSafety.summary.secretStorageOk) {
    recommendations.push('Move API keys/tokens into Obsidian SecretStorage before release validation.');
  } else if (aiSafety.summary.keyRisk && aiSafety.summary.secretStorageOk) {
    recommendations.push('Keep SecretStorage evidence visible in diagnostics so agents can distinguish safe key handling from plaintext settings.');
  }
  if (aiSafety.summary.keyRisk && !aiSafety.summary.redactionOk) {
    recommendations.push('Add diagnostic redaction before exporting logs or handoff artifacts.');
  } else if (aiSafety.summary.keyRisk && aiSafety.summary.redactionOk) {
    recommendations.push('Keep redaction coverage in diagnostic exports and agent handoff artifacts.');
  }
  if (aiSafety.summary.externalRequestRisk && !aiSafety.summary.settingsBoundaryOk) {
    recommendations.push('Document external request behavior in user-visible settings or privacy copy.');
  }
  if (controlSurfaces.mcpRest.detected && !runtimeProbes.rest.configured) {
    recommendations.push('Probe MCP/REST runtime endpoints with --rest-base-url before trusting tool availability.');
  }
  if (runtimeProbes.rest.configured && !runtimeProbes.rest.localhost) {
    recommendations.push('Review non-local MCP/REST endpoint exposure before handing control to another agent.');
  }
  if (runtimeProbes.rest.configured && !runtimeProbes.rest.authProvided) {
    recommendations.push('Require auth/API-key evidence for MCP/REST tool endpoints.');
  }
  if (runtimeProbes.rest.configured && !runtimeProbes.rest.toolAllowlist) {
    recommendations.push('Confirm MCP/REST tool allowlist or equivalent scope controls before enabling automation.');
  } else if (runtimeProbes.rest.configured && runtimeProbes.rest.ok) {
    recommendations.push('Record MCP/REST tool list evidence in agent-tools.json before handing control to another model.');
  }
  if (recommendations.length === 0) {
    recommendations.push('Continue with the default CLI/CDP smoke loop; optional agentic support checks have no blocking warnings.');
  }
  return recommendations;
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
  restBaseUrl = '',
  restApiKey = '',
  restHealthPath = '/health',
  restToolsPath = '/tools',
  probeTimeoutMs = 2000,
} = {}) {
  const resolvedRepoDir = path.resolve(repoDir);
  const packageJsonPath = path.join(resolvedRepoDir, 'package.json');
  const packageJson = await readJsonIfExists(packageJsonPath);
  const files = await collectFiles(resolvedRepoDir, { maxFiles });
  const signalEvidence = {};
  const aiSafetyEvidence = {};
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

    for (const definition of AI_SAFETY_DEFINITIONS) {
      pushPatternEvidence(aiSafetyEvidence, definition, resolvedRepoDir, filePath, text);
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
  const aiSafety = buildAiSafety(aiSafetyEvidence);
  const runtimeProbes = {
    rest: await probeRestControlSurface({
      restBaseUrl,
      restApiKey,
      restHealthPath,
      restToolsPath,
      probeTimeoutMs,
    }),
  };
  const controlSurfaces = buildControlSurfaces({ signals, runtimeProbes });
  const recommendations = buildRecommendations({ aiSafety, controlSurfaces, runtimeProbes });
  const sourceFiles = files
    .slice(0, 240)
    .map((filePath) => toRelativePath(resolvedRepoDir, filePath))
    .sort((left, right) => left.localeCompare(right));
  const warningCount = aiSafety.summary.warningCount
    + (runtimeProbes.rest.configured && !runtimeProbes.rest.ok ? 1 : 0)
    + (runtimeProbes.rest.configured && (!runtimeProbes.rest.localhost || !runtimeProbes.rest.authProvided || !runtimeProbes.rest.toolAllowlist) ? 1 : 0);

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
    controlSurfaces,
    aiSafety,
    runtimeProbes,
    sourceFiles,
    recommendations,
    summary: {
      detectedSignalCount: detectedSignals.length,
      detectedSignals,
      undetectedSignals,
      heuristicHits,
      warningCount,
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
  --rest-base-url <url>             Optional local REST/MCP HTTP endpoint to probe.
  --rest-api-key <key>              Optional API key for REST/MCP tools endpoint.
  --rest-health-path <path>         Health path for REST/MCP probe. Defaults to /health.
  --rest-tools-path <path>          Tools path for REST/MCP probe. Defaults to /tools.
  --probe-timeout-ms <n>            Per-request timeout for runtime probes. Defaults to 2000.
  --output <path>                   Optional JSON output path.
`);
  }

  const repoDir = path.resolve(getStringOption(options, 'repo-dir', process.cwd()));
  const testVaultPluginDir = getStringOption(options, 'test-vault-plugin-dir', '').trim();
  const restBaseUrl = getStringOption(options, 'rest-base-url', '').trim();
  const restApiKey = getStringOption(options, 'rest-api-key', '').trim();
  const restHealthPath = getStringOption(options, 'rest-health-path', '/health').trim() || '/health';
  const restToolsPath = getStringOption(options, 'rest-tools-path', '/tools').trim() || '/tools';
  const probeTimeoutMs = Math.max(250, getNumberOption(options, 'probe-timeout-ms', 2000));
  const outputPath = getStringOption(options, 'output', '').trim();
  const report = await detectAgenticSupport({
    repoDir,
    testVaultPluginDir,
    restBaseUrl,
    restApiKey,
    restHealthPath,
    restToolsPath,
    probeTimeoutMs,
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
