import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  ensureParentDirectory,
  getStringOption,
  hasHelpOption,
  nowIso,
  parseArgs,
  printHelpAndExit,
} from './obsidian_cdp_common.mjs';

export const CONTROL_CAPABILITIES = [
  'launchApp',
  'reloadPlugin',
  'captureConsole',
  'captureErrors',
  'captureDom',
  'captureScreenshot',
  'runScenario',
  'locatorActions',
  'visualReview',
  'networkInspection',
];

const BACKEND_ORDER = [
  'obsidian-cli',
  'bundled-cdp',
  'obsidian-cli-rest',
  'chrome-devtools-mcp',
  'playwright-script',
  'playwright-mcp',
];

const BACKEND_DEFINITIONS = {
  'obsidian-cli': {
    label: 'Obsidian CLI developer commands',
    type: 'local-cli',
    portable: true,
    agentNative: false,
    capabilities: ['launchApp', 'reloadPlugin', 'captureConsole', 'captureErrors', 'captureDom', 'captureScreenshot', 'runScenario'],
    boundary: 'Best default when Developer commands are available; still use CDP/Playwright for richer DOM or locator behavior.',
  },
  'bundled-cdp': {
    label: 'Bundled CDP scripts',
    type: 'local-cdp',
    portable: true,
    agentNative: false,
    capabilities: ['launchApp', 'reloadPlugin', 'captureConsole', 'captureErrors', 'captureDom', 'captureScreenshot', 'runScenario', 'networkInspection'],
    boundary: 'Portable fallback for live Obsidian Electron targets; requires a local CDP port and Node WebSocket support.',
  },
  'obsidian-cli-rest': {
    label: 'Obsidian CLI REST / MCP bridge',
    type: 'local-http',
    portable: false,
    agentNative: true,
    capabilities: ['reloadPlugin', 'captureConsole', 'captureErrors', 'captureDom', 'captureScreenshot', 'runScenario'],
    boundary: 'Only safe when bound to localhost with auth and a scoped tool allowlist; do not pass raw API keys into handoff artifacts.',
  },
  'chrome-devtools-mcp': {
    label: 'Chrome DevTools MCP',
    type: 'mcp',
    portable: false,
    agentNative: true,
    capabilities: ['captureConsole', 'captureErrors', 'captureDom', 'captureScreenshot', 'runScenario', 'networkInspection'],
    boundary: 'Useful as an agent-native DevTools backend after confirming the attached target is the Obsidian Electron window.',
  },
  'playwright-script': {
    label: 'Repo Playwright / E2E script',
    type: 'local-test-runner',
    portable: false,
    agentNative: false,
    capabilities: ['captureScreenshot', 'runScenario', 'locatorActions', 'visualReview'],
    boundary: 'Good for locator-level UI checks when the repo owns a Playwright/WDIO/E2E lane; not the primary plugin reload backend.',
  },
  'playwright-mcp': {
    label: 'Playwright MCP',
    type: 'mcp',
    portable: false,
    agentNative: true,
    capabilities: ['captureDom', 'captureScreenshot', 'runScenario', 'locatorActions', 'visualReview'],
    boundary: 'Good for agent-native browser-style interactions and accessibility snapshots; pair with CLI/CDP for plugin reload/log control.',
  },
};

function asObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function stringValue(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function booleanValue(value, fallback = false) {
  if (typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'number') {
    return value !== 0;
  }
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase();
    if (['true', '1', 'yes', 'ok', 'pass', 'available', 'enabled', 'runnable'].includes(normalized)) {
      return true;
    }
    if (['false', '0', 'no', 'fail', 'missing', 'disabled'].includes(normalized)) {
      return false;
    }
  }
  return fallback;
}

function normalizeStatus({ detected, available }) {
  if (available) {
    return 'available';
  }
  if (detected) {
    return 'detected';
  }
  return 'missing';
}

function getChecks(doctor) {
  return Array.isArray(doctor?.checks) ? doctor.checks : [];
}

function findCheck(doctor, matcher) {
  return getChecks(doctor).find((entry) => {
    const id = stringValue(entry?.id).toLowerCase();
    const category = stringValue(entry?.category).toLowerCase();
    const detail = stringValue(entry?.detail).toLowerCase();
    if (typeof matcher === 'string') {
      const needle = matcher.toLowerCase();
      return id === needle || category === needle;
    }
    return matcher.test(id) || matcher.test(category) || matcher.test(detail);
  }) ?? null;
}

function findDeepValues(root, keyPattern, { maxDepth = 8 } = {}) {
  const results = [];
  const visited = new Set();

  function walk(value, depth) {
    if (!value || depth > maxDepth || typeof value !== 'object') {
      return;
    }
    if (visited.has(value)) {
      return;
    }
    visited.add(value);

    if (Array.isArray(value)) {
      for (const item of value) {
        walk(item, depth + 1);
      }
      return;
    }

    for (const [key, entry] of Object.entries(value)) {
      if (keyPattern.test(key)) {
        results.push(entry);
      }
      walk(entry, depth + 1);
    }
  }

  walk(root, 0);
  return results;
}

function deriveNodeAvailability(node) {
  if (node === undefined || node === null) {
    return {
      detected: false,
      available: false,
      detail: '',
    };
  }
  if (typeof node === 'boolean') {
    return {
      detected: node,
      available: node,
      detail: node ? 'Boolean signal reports available.' : 'Boolean signal reports missing.',
    };
  }
  if (typeof node === 'string') {
    return {
      detected: node.trim().length > 0,
      available: booleanValue(node, false),
      detail: node.trim(),
    };
  }

  const objectNode = asObject(node);
  const status = stringValue(objectNode.status).toLowerCase();
  const available = booleanValue(
    objectNode.available ?? objectNode.usable ?? objectNode.enabled ?? objectNode.ok ?? objectNode.runnable ?? objectNode.runnableInThisCheckout,
    status === 'pass' || status === 'available',
  );
  const detected = booleanValue(
    objectNode.detected ?? objectNode.present ?? objectNode.declared ?? objectNode.installed ?? objectNode.found,
    available || status.length > 0 || Object.keys(objectNode).length > 0,
  );
  const detail = stringValue(objectNode.detail)
    || stringValue(objectNode.summary)
    || stringValue(objectNode.reason)
    || (status ? `Status: ${status}.` : 'Signal detected.');
  return { detected, available, detail };
}

function commandTemplateForBackend(id, { summary, diagnosis, doctor }) {
  const repoDir = stringValue(diagnosis.runtime?.repoDir) || stringValue(doctor?.repoDir) || stringValue(summary.repoDir) || '<repo>';
  const outputDir = stringValue(diagnosis.runtime?.outputDir) || stringValue(summary.outputDir) || '.obsidian-debug';
  const obsidianCommand = stringValue(summary.obsidianCommand) || stringValue(diagnosis.runtime?.obsidianCommand) || stringValue(doctor?.obsidianCommand) || 'obsidian';
  const vaultName = stringValue(summary.vaultName) || stringValue(diagnosis.vaultName) || stringValue(doctor?.vaultName);
  const vaultPrefix = vaultName ? `vault=${vaultName} ` : '';
  const cdp = asObject(doctor?.cdp);
  const cdpHost = stringValue(cdp.host) || '127.0.0.1';
  const cdpPort = cdp.port ?? 9222;
  const scriptRoot = 'scripts';

  switch (id) {
    case 'obsidian-cli':
      return [
        {
          capability: 'reloadPlugin',
          command: `${obsidianCommand} ${vaultPrefix}plugin:reload <plugin-id>`,
          safety: 'reloads-live-plugin',
        },
        {
          capability: 'captureScreenshot',
          command: `${obsidianCommand} ${vaultPrefix}dev:screenshot path=${outputDir}/screenshot.png`,
          safety: 'read-only',
        },
        {
          capability: 'captureDom',
          command: `${obsidianCommand} ${vaultPrefix}dev:dom selector=.workspace-leaf.mod-active path=${outputDir}/dom.html`,
          safety: 'read-only',
        },
      ];
    case 'bundled-cdp':
      return [
        {
          capability: 'captureDom',
          command: `node ${scriptRoot}/obsidian_cdp_capture_ui.mjs --cdp-host ${cdpHost} --cdp-port ${cdpPort} --html-output ${outputDir}/dom.html --screenshot-output ${outputDir}/screenshot.png`,
          safety: 'read-only',
        },
        {
          capability: 'runScenario',
          command: `node ${scriptRoot}/obsidian_debug_scenario_runner.mjs --scenario-name open-plugin-view --control-backend bundled-cdp --cdp-host ${cdpHost} --cdp-port ${cdpPort} --output ${outputDir}/scenario-report.json`,
          safety: 'interacts-with-live-app',
        },
      ];
    case 'playwright-script':
      return [
        {
          capability: 'runScenario',
          command: `node ${scriptRoot}/obsidian_debug_scenario_runner.mjs --scenario-path <scenario.json> --adapter playwright --output ${outputDir}/scenario-report.json`,
          safety: 'interacts-with-live-app',
        },
      ];
    case 'obsidian-cli-rest':
      return [
        {
          capability: 'reloadPlugin',
          command: 'Call the local REST/MCP reload tool from the probed allowlisted tools; keep API keys outside command text.',
          safety: 'requires-local-auth-review',
        },
      ];
    case 'chrome-devtools-mcp':
      return [
        {
          capability: 'captureScreenshot',
          command: 'Use the agent MCP client against Chrome DevTools MCP after confirming the selected target title/url is Obsidian.',
          safety: 'requires-target-review',
        },
      ];
    case 'playwright-mcp':
      return [
        {
          capability: 'locatorActions',
          command: 'Use Playwright MCP snapshot/click/fill/screenshot tools against the selected Obsidian UI target.',
          safety: 'requires-target-review',
        },
      ];
    default:
      return [];
  }
}

function buildBackend(id, signal, documents) {
  const definition = BACKEND_DEFINITIONS[id];
  const detected = Boolean(signal.detected);
  const available = Boolean(signal.available);
  return {
    id,
    label: definition.label,
    type: definition.type,
    status: normalizeStatus({ detected, available }),
    detected,
    available,
    portable: definition.portable,
    agentNative: definition.agentNative,
    capabilities: definition.capabilities,
    boundary: definition.boundary,
    detail: signal.detail || (available ? 'Available.' : detected ? 'Detected but not confirmed runnable.' : 'No signal detected.'),
    source: signal.source || 'inferred',
    commandTemplates: commandTemplateForBackend(id, documents),
  };
}

function extractSignals({ summary, diagnosis, doctor }) {
  const cliCheck = findCheck(doctor, 'obsidian-cli');
  const cliDetected = Boolean(
    cliCheck
    || stringValue(summary.obsidianCommand)
    || stringValue(diagnosis.runtime?.obsidianCommand)
    || stringValue(doctor?.obsidianCommand),
  );
  const cliAvailable = Boolean(cliCheck?.status === 'pass' || stringValue(summary.obsidianCommand));

  const cdp = asObject(doctor?.cdp);
  const cdpDetected = Boolean(
    diagnosis.useCdp === true
    || summary.useCdp === true
    || diagnosis.artifacts?.cdpTrace
    || diagnosis.artifacts?.cdpSummary
    || cdp.port
    || findCheck(doctor, /cdp|devtools/i),
  );
  const cdpAvailable = Boolean(
    diagnosis.useCdp === true
    || cdp.available === true
    || findCheck(doctor, /cdp-target|cdp-port|devtools/)?.status === 'pass',
  );

  const adapterLanes = asObject(doctor?.adapterLanes);
  const adapterValues = Object.values(adapterLanes).filter((entry) => entry && typeof entry === 'object');
  const playwrightDetected = Boolean(
    diagnosis.artifacts?.playwrightTrace
    || diagnosis.artifacts?.playwrightScreenshot
    || adapterValues.some((entry) => /playwright|wdio|e2e/i.test(JSON.stringify(entry))),
  );
  const playwrightAvailable = adapterValues.some((entry) => entry.runnable === true || entry.runnableInThisCheckout === true);

  const agenticSupport = asObject(doctor?.agenticSupport);
  const controlSurfaces = asObject(agenticSupport.controlSurfaces);
  const restProbe = asObject(agenticSupport.runtimeProbes?.rest);
  const mcpRest = deriveNodeAvailability(controlSurfaces.mcpRest ?? findDeepValues(agenticSupport, /(mcp.*rest|rest.*mcp|obsidian.*rest|http.*api)/i)[0]);
  const devtoolsMcp = deriveNodeAvailability(controlSurfaces.devtoolsMcp ?? findDeepValues(agenticSupport, /(devtools.*mcp|chrome.*mcp|cdp.*mcp)/i)[0]);
  const playwrightMcpRaw = findDeepValues(agenticSupport, /(playwright.*mcp|mcp.*playwright)/i)[0];
  const playwrightMcp = deriveNodeAvailability(playwrightMcpRaw);

  return {
    'obsidian-cli': {
      detected: cliDetected,
      available: cliAvailable,
      detail: cliCheck?.detail || (cliDetected ? 'Obsidian CLI command or doctor check detected.' : 'No Obsidian CLI developer-command signal detected.'),
      source: cliCheck ? 'doctor.checks' : 'summary/diagnosis',
    },
    'bundled-cdp': {
      detected: cdpDetected,
      available: cdpAvailable,
      detail: cdpDetected
        ? 'CDP configuration or artifacts detected; bundled scripts can drive the Obsidian Electron target when the port is reachable.'
        : 'No CDP endpoint/artifact signal detected.',
      source: cdpDetected ? 'doctor/diagnosis' : 'inferred',
    },
    'obsidian-cli-rest': {
      detected: Boolean(mcpRest.detected || restProbe.configured),
      available: Boolean(mcpRest.available || restProbe.ok),
      detail: restProbe.detail || mcpRest.detail || 'No REST/MCP runtime probe signal detected.',
      source: restProbe.configured ? 'doctor.agenticSupport.runtimeProbes.rest' : 'doctor.agenticSupport.controlSurfaces',
    },
    'chrome-devtools-mcp': {
      detected: devtoolsMcp.detected,
      available: devtoolsMcp.available,
      detail: devtoolsMcp.detail || 'No Chrome DevTools MCP signal detected.',
      source: 'doctor.agenticSupport.controlSurfaces',
    },
    'playwright-script': {
      detected: playwrightDetected,
      available: playwrightAvailable,
      detail: playwrightDetected
        ? (playwrightAvailable ? 'Repo-owned Playwright/E2E lane appears runnable.' : 'Playwright/E2E signals detected but no runnable lane confirmed.')
        : 'No repo-owned Playwright/E2E lane detected.',
      source: 'doctor.adapterLanes/diagnosis.artifacts',
    },
    'playwright-mcp': {
      detected: playwrightMcp.detected,
      available: playwrightMcp.available,
      detail: playwrightMcp.detail || 'No Playwright MCP signal detected.',
      source: 'doctor.agenticSupport',
    },
  };
}

function selectBackends({ backends, preferredBackend = '' }) {
  const preferred = stringValue(preferredBackend);
  const selections = {};

  for (const capability of CONTROL_CAPABILITIES) {
    const candidates = BACKEND_ORDER
      .map((id) => backends[id])
      .filter((backend) => backend?.capabilities.includes(capability));
    const preferredCandidate = preferred
      ? candidates.find((backend) => backend.id === preferred && backend.detected)
      : null;
    const availableCandidate = candidates.find((backend) => backend.available);
    const detectedCandidate = candidates.find((backend) => backend.detected);
    const selected = preferredCandidate ?? availableCandidate ?? detectedCandidate ?? candidates[0] ?? null;
    selections[capability] = selected
      ? {
          backendId: selected.id,
          status: selected.available ? 'available' : selected.detected ? 'detected' : 'missing',
          needsReview: !selected.available || ['mcp', 'local-http'].includes(selected.type),
          detail: selected.available
            ? `${capability} can use ${selected.label}.`
            : `${capability} is routed to ${selected.label}, but runtime availability is not confirmed.`,
        }
      : {
          backendId: null,
          status: 'missing',
          needsReview: true,
          detail: `No backend definition supports ${capability}.`,
        };
  }

  return selections;
}

function buildRecommendations(backends, selections) {
  const recommendations = [];
  if (backends['obsidian-cli'].available) {
    recommendations.push('Keep Obsidian CLI as the default reload/log/screenshot/DOM lane when developer commands work.');
  } else if (backends['bundled-cdp'].detected) {
    recommendations.push('Use bundled CDP as the portable fallback for live Obsidian capture until CLI developer commands are available.');
  }
  if (backends['chrome-devtools-mcp'].detected) {
    recommendations.push('Before routing to Chrome DevTools MCP, confirm the selected target is the Obsidian Electron window and record tool-list evidence.');
  }
  if (backends['playwright-mcp'].detected || backends['playwright-script'].detected) {
    recommendations.push('Use Playwright lanes for locator/assertion behavior, but pair them with CLI/CDP for plugin reload and error capture.');
  }
  if (backends['obsidian-cli-rest'].detected && !backends['obsidian-cli-rest'].available) {
    recommendations.push('Probe REST/MCP health/tools endpoints and verify localhost/auth/allowlist before agent handoff.');
  }
  if (selections.visualReview?.backendId) {
    recommendations.push('Generate a visual-review pack after screenshot capture; screenshots support human review but do not replace manual GUI validation.');
  }
  return [...new Set(recommendations)];
}

async function readJsonOrNull(filePath) {
  if (!filePath) {
    return null;
  }
  try {
    return JSON.parse((await fs.readFile(filePath, 'utf8')).replace(/^\uFEFF/, ''));
  } catch {
    return null;
  }
}

export function detectControlBackends({
  summaryDocument = {},
  diagnosisDocument = {},
  doctorDocument = {},
  preferredBackend = '',
} = {}) {
  const summary = asObject(summaryDocument);
  const diagnosis = asObject(diagnosisDocument);
  const doctor = asObject(doctorDocument);
  const signals = extractSignals({ summary, diagnosis, doctor });
  const backends = Object.fromEntries(BACKEND_ORDER.map((id) => [
    id,
    buildBackend(id, signals[id], { summary, diagnosis, doctor }),
  ]));
  const selections = selectBackends({ backends, preferredBackend });
  return {
    generatedAt: nowIso(),
    schemaVersion: 1,
    preferredBackend: stringValue(preferredBackend) || null,
    capabilities: CONTROL_CAPABILITIES,
    backends,
    selections,
    recommendations: buildRecommendations(backends, selections),
    boundary: 'Control backend selection is a routing contract for agents. It does not prove a backend is safe or attached to the correct Obsidian target unless the selected backend status is available and its boundary checks are satisfied.',
  };
}

export async function generateControlBackendsManifest({
  summaryPath = '',
  diagnosisPath = '',
  doctorPath = '',
  outputPath = '',
  preferredBackend = '',
  summaryDocument = null,
  diagnosisDocument = null,
  doctorDocument = null,
} = {}) {
  const resolvedSummaryPath = summaryPath ? path.resolve(summaryPath) : '';
  const resolvedDiagnosisPath = diagnosisPath ? path.resolve(diagnosisPath) : '';
  const resolvedDoctorPath = doctorPath ? path.resolve(doctorPath) : '';
  const summary = summaryDocument ?? await readJsonOrNull(resolvedSummaryPath);
  const diagnosis = diagnosisDocument ?? await readJsonOrNull(resolvedDiagnosisPath);
  const doctor = doctorDocument ?? await readJsonOrNull(resolvedDoctorPath);
  const manifest = detectControlBackends({
    summaryDocument: summary ?? {},
    diagnosisDocument: diagnosis ?? {},
    doctorDocument: doctor ?? {},
    preferredBackend,
  });
  const defaultOutputBase = resolvedDoctorPath || resolvedDiagnosisPath || resolvedSummaryPath || process.cwd();
  const resolvedOutputPath = path.resolve(outputPath || path.join(path.dirname(defaultOutputBase), 'control-backends.json'));
  await ensureParentDirectory(resolvedOutputPath);
  await fs.writeFile(resolvedOutputPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  return {
    ...manifest,
    outputPath: resolvedOutputPath,
  };
}

function isMainModule() {
  if (!process.argv[1]) {
    return false;
  }
  return path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
}

if (isMainModule()) {
  const options = parseArgs(process.argv.slice(2));
  if (hasHelpOption(options)) {
    printHelpAndExit(`
Usage: node scripts/obsidian_debug_control_backend_support.mjs [options]

Options:
  --summary <path>             Optional summary.json.
  --diagnosis <path>           Optional diagnosis.json.
  --doctor <path>              Optional doctor.json.
  --preferred-backend <id>     Prefer a detected backend id when routing capabilities.
  --output <path>              Output control-backends.json path.
`);
  }

  const manifest = await generateControlBackendsManifest({
    summaryPath: getStringOption(options, 'summary', '').trim(),
    diagnosisPath: getStringOption(options, 'diagnosis', '').trim(),
    doctorPath: getStringOption(options, 'doctor', '').trim(),
    preferredBackend: getStringOption(options, 'preferred-backend', '').trim(),
    outputPath: getStringOption(options, 'output', '').trim(),
  });

  console.log(JSON.stringify({
    status: 'ok',
    outputPath: manifest.outputPath,
    availableBackends: Object.values(manifest.backends).filter((entry) => entry.available).map((entry) => entry.id),
    selections: manifest.selections,
  }, null, 2));
}
