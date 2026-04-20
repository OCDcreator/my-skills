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
import { detectControlBackends } from './obsidian_debug_control_backend_support.mjs';

function asObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function stringValue(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function uniqueStrings(values) {
  return [...new Set(
    values
      .map((entry) => String(entry ?? '').trim())
      .filter((entry) => entry.length > 0),
  )];
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
    if (['true', '1', 'yes', 'on', 'available', 'enabled', 'ok', 'pass'].includes(normalized)) {
      return true;
    }
    if (['false', '0', 'no', 'off', 'missing', 'none', 'fail'].includes(normalized)) {
      return false;
    }
  }
  return fallback;
}

function statusRank(status) {
  switch (status) {
    case 'fail':
      return 3;
    case 'warn':
    case 'warning':
      return 2;
    case 'info':
      return 1;
    case 'pass':
      return 0;
    default:
      return 0;
  }
}

function resolveDocumentPath(documentPath, value) {
  const normalized = stringValue(value);
  if (!normalized) {
    return null;
  }
  if (path.isAbsolute(normalized)) {
    return path.resolve(normalized);
  }
  if (!documentPath) {
    return path.resolve(normalized);
  }
  return path.resolve(path.dirname(path.resolve(documentPath)), normalized);
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

async function pathExists(filePath) {
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

function normalizeSummaryPaths(summary, summaryPath) {
  const base = asObject(summary);
  return {
    ...base,
    repoDir: resolveDocumentPath(summaryPath, base.repoDir),
    outputDir: resolveDocumentPath(summaryPath, base.outputDir),
    testVaultPluginDir: resolveDocumentPath(summaryPath, base.testVaultPluginDir),
    appLaunch: resolveDocumentPath(summaryPath, base.appLaunch),
    buildLog: resolveDocumentPath(summaryPath, base.buildLog),
    deployReport: resolveDocumentPath(summaryPath, base.deployReport),
    bootstrapReport: resolveDocumentPath(summaryPath, base.bootstrapReport),
    scenarioReport: resolveDocumentPath(summaryPath, base.scenarioReport),
    comparisonReport: resolveDocumentPath(summaryPath, base.comparisonReport),
    consoleLog: resolveDocumentPath(summaryPath, base.consoleLog),
    errorsLog: resolveDocumentPath(summaryPath, base.errorsLog),
    cdpTrace: resolveDocumentPath(summaryPath, base.cdpTrace),
    cdpSummary: resolveDocumentPath(summaryPath, base.cdpSummary),
    screenshot: resolveDocumentPath(summaryPath, base.screenshot),
    dom: resolveDocumentPath(summaryPath, base.dom),
    vaultLogCapture: resolveDocumentPath(summaryPath, base.vaultLogCapture),
  };
}

function normalizeDiagnosisPaths(diagnosis, diagnosisPath) {
  const base = asObject(diagnosis);
  const artifacts = asObject(base.artifacts);
  return {
    ...base,
    runtime: {
      ...asObject(base.runtime),
      repoDir: resolveDocumentPath(diagnosisPath, base.runtime?.repoDir),
      outputDir: resolveDocumentPath(diagnosisPath, base.runtime?.outputDir),
      summaryPath: resolveDocumentPath(diagnosisPath, base.runtime?.summaryPath),
      testVaultPluginDir: resolveDocumentPath(diagnosisPath, base.runtime?.testVaultPluginDir),
    },
    artifacts: {
      ...artifacts,
      summary: resolveDocumentPath(diagnosisPath, artifacts.summary),
      appLaunch: resolveDocumentPath(diagnosisPath, artifacts.appLaunch),
      buildLog: resolveDocumentPath(diagnosisPath, artifacts.buildLog),
      deployReport: resolveDocumentPath(diagnosisPath, artifacts.deployReport),
      bootstrapReport: resolveDocumentPath(diagnosisPath, artifacts.bootstrapReport),
      consoleLog: resolveDocumentPath(diagnosisPath, artifacts.consoleLog),
      errorsLog: resolveDocumentPath(diagnosisPath, artifacts.errorsLog),
      cdpTrace: resolveDocumentPath(diagnosisPath, artifacts.cdpTrace),
      cdpSummary: resolveDocumentPath(diagnosisPath, artifacts.cdpSummary),
      vaultLogCapture: resolveDocumentPath(diagnosisPath, artifacts.vaultLogCapture),
      scenarioReport: resolveDocumentPath(diagnosisPath, artifacts.scenarioReport),
      screenshot: resolveDocumentPath(diagnosisPath, artifacts.screenshot),
      dom: resolveDocumentPath(diagnosisPath, artifacts.dom),
      playwrightTrace: resolveDocumentPath(diagnosisPath, artifacts.playwrightTrace),
      playwrightScreenshot: resolveDocumentPath(diagnosisPath, artifacts.playwrightScreenshot),
    },
    agentToolsPath: resolveDocumentPath(diagnosisPath, base.agentToolsPath),
  };
}

function getDoctorChecks(doctor) {
  const checks = doctor?.checks;
  return Array.isArray(checks) ? checks : [];
}

function findDoctorCheck(checks, matcher) {
  return checks.find((entry) => {
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

function findValuesByKeyPattern(root, keyPattern, { maxDepth = 8 } = {}) {
  const results = [];
  const visited = new Set();

  function walk(value, depth) {
    if (!value || depth > maxDepth) {
      return;
    }
    if (typeof value !== 'object') {
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

function deriveSurfaceFromNode(node) {
  if (typeof node === 'boolean') {
    return {
      detected: node,
      available: node,
      detail: node ? 'Detected from boolean signal.' : 'Boolean signal indicates unavailable.',
    };
  }

  if (typeof node === 'string') {
    return {
      detected: node.trim().length > 0,
      available: booleanValue(node, false),
      detail: node.trim() || 'Surface detail string provided.',
    };
  }

  const objectNode = asObject(node);
  const status = stringValue(objectNode.status).toLowerCase();
  const available = booleanValue(
    objectNode.available ?? objectNode.usable ?? objectNode.enabled ?? objectNode.ok ?? objectNode.runnable,
    status === 'pass',
  );
  const detected = booleanValue(
    objectNode.detected ?? objectNode.present ?? objectNode.installed ?? objectNode.declared ?? objectNode.found,
    available || status.length > 0 || Object.keys(objectNode).length > 0,
  );
  const detail = stringValue(objectNode.detail)
    || stringValue(objectNode.summary)
    || stringValue(objectNode.reason)
    || (status ? `Status: ${status}.` : 'Signal detected.');

  return {
    detected,
    available,
    detail,
  };
}

function buildControlSurface({ detected, available, detail, source }) {
  const normalizedDetected = Boolean(detected);
  const normalizedAvailable = Boolean(available);
  return {
    status: normalizedAvailable ? 'available' : (normalizedDetected ? 'detected' : 'missing'),
    detected: normalizedDetected,
    available: normalizedAvailable,
    detail: detail || (normalizedAvailable ? 'Available.' : (normalizedDetected ? 'Detected but not confirmed runnable.' : 'No signal detected.')),
    source,
  };
}

function inferControlSurfaces({ summary, diagnosis, doctor }) {
  const checks = getDoctorChecks(doctor);
  const agenticSupport = asObject(doctor?.agenticSupport);

  const cliCheck = findDoctorCheck(checks, 'obsidian-cli');
  const cliDetected = Boolean(
    stringValue(summary.obsidianCommand)
    || stringValue(diagnosis.runtime?.obsidianCommand)
    || stringValue(doctor?.obsidianCommand)
    || cliCheck,
  );
  const cliAvailable = Boolean(cliCheck?.status === 'pass' || stringValue(summary.obsidianCommand));

  const cdpDetected = Boolean(
    summary.useCdp === true
    || diagnosis.useCdp === true
    || diagnosis.artifacts?.cdpTrace
    || diagnosis.artifacts?.cdpSummary
    || asObject(doctor?.cdp).port,
  );
  const cdpAvailable = Boolean(
    diagnosis.useCdp === true && diagnosis.artifactStates?.trace?.status === 'captured',
  );

  const adapterLanes = asObject(doctor?.adapterLanes);
  const adapterValues = Object.values(adapterLanes).filter((entry) => entry && typeof entry === 'object');
  const diagnosisPlaywrightDetected = Boolean(
    diagnosis.artifacts?.playwrightTrace
    || diagnosis.artifacts?.playwrightScreenshot,
  );
  const adapterPlaywrightDetected = adapterValues.some((entry) => /playwright|e2e|wdio/i.test(JSON.stringify(entry)));
  const playwrightDetected = diagnosisPlaywrightDetected || adapterPlaywrightDetected;
  const playwrightAvailable = adapterValues.some((entry) => entry.runnable === true || entry.runnableInThisCheckout === true);

  const logstravaganzaNode = doctor?.ecosystem?.vaultPlugins?.logstravaganza;
  const logstravaganzaDetected = Boolean(
    summary.vaultLogCapture
    || diagnosis.artifacts?.vaultLogCapture
    || diagnosis.vaultLogs?.sourceCount
    || logstravaganzaNode?.installed
    || logstravaganzaNode?.filesystemInstalled,
  );
  const logstravaganzaAvailable = Boolean(
    diagnosis.vaultLogs?.usable
    || logstravaganzaNode?.usable,
  );

  const mcpRestCandidates = [
    ...findValuesByKeyPattern(agenticSupport, /(mcp.*rest|rest.*mcp|obsidian.*rest|http.*api)/i),
    ...findValuesByKeyPattern(doctor, /(mcp.*rest|rest.*mcp|obsidian.*rest|http.*api)/i),
  ];
  const devtoolsMcpCandidates = [
    ...findValuesByKeyPattern(agenticSupport, /(devtools.*mcp|chrome.*mcp|cdp.*mcp)/i),
    ...findValuesByKeyPattern(doctor, /(devtools.*mcp|chrome.*mcp|cdp.*mcp)/i),
  ];
  const playwrightMcpCandidates = [
    ...findValuesByKeyPattern(agenticSupport, /(playwright.*mcp|mcp.*playwright)/i),
    ...findValuesByKeyPattern(doctor, /(playwright.*mcp|mcp.*playwright)/i),
  ];

  const mcpRestDerived = mcpRestCandidates.map((entry) => deriveSurfaceFromNode(entry))[0] ?? { detected: false, available: false, detail: '' };
  const devtoolsMcpDerived = devtoolsMcpCandidates.map((entry) => deriveSurfaceFromNode(entry))[0] ?? { detected: false, available: false, detail: '' };
  const playwrightMcpDerived = playwrightMcpCandidates.map((entry) => deriveSurfaceFromNode(entry))[0] ?? { detected: false, available: false, detail: '' };

  return {
    cli: buildControlSurface({
      detected: cliDetected,
      available: cliAvailable,
      detail: cliCheck?.detail || (cliDetected ? 'Obsidian CLI command/config detected.' : ''),
      source: cliCheck ? 'doctor.checks' : (summary.obsidianCommand ? 'summary.obsidianCommand' : 'inferred'),
    }),
    cdp: buildControlSurface({
      detected: cdpDetected,
      available: cdpAvailable,
      detail: cdpDetected
        ? (diagnosis.useCdp ? 'CDP mode enabled in diagnosis.' : 'CDP artifacts/config detected.')
        : '',
      source: diagnosis.useCdp ? 'diagnosis.useCdp' : 'inferred',
    }),
    playwright: buildControlSurface({
      detected: playwrightDetected,
      available: playwrightAvailable,
      detail: playwrightDetected
        ? (playwrightAvailable ? 'Playwright/E2E adapter lane appears runnable.' : 'Playwright/E2E signals detected but runnable lane is not confirmed.')
        : '',
      source: diagnosisPlaywrightDetected ? 'diagnosis.artifacts' : 'doctor.adapterLanes',
    }),
    logstravaganza: buildControlSurface({
      detected: logstravaganzaDetected,
      available: logstravaganzaAvailable,
      detail: stringValue(diagnosis.vaultLogs?.detail) || stringValue(logstravaganzaNode?.capture?.detail),
      source: diagnosis.vaultLogs ? 'diagnosis.vaultLogs' : 'doctor.ecosystem.vaultPlugins.logstravaganza',
    }),
    mcpRest: buildControlSurface({
      detected: mcpRestDerived.detected,
      available: mcpRestDerived.available,
      detail: mcpRestDerived.detail,
      source: mcpRestCandidates.length > 0 ? 'doctor.agenticSupport' : 'inferred',
    }),
    devtoolsMcp: buildControlSurface({
      detected: devtoolsMcpDerived.detected,
      available: devtoolsMcpDerived.available,
      detail: devtoolsMcpDerived.detail,
      source: devtoolsMcpCandidates.length > 0 ? 'doctor.agenticSupport' : 'inferred',
    }),
    playwrightMcp: buildControlSurface({
      detected: playwrightMcpDerived.detected,
      available: playwrightMcpDerived.available,
      detail: playwrightMcpDerived.detail,
      source: playwrightMcpCandidates.length > 0 ? 'doctor.agenticSupport' : 'inferred',
    }),
  };
}

function quoteArg(value) {
  const text = String(value ?? '');
  if (text.length === 0) {
    return '""';
  }
  if (/[\s"&|<>^]/.test(text)) {
    return `"${text.replaceAll('"', '\\"')}"`;
  }
  return text;
}

function renderCommand(executable, args = []) {
  const tokens = [String(executable ?? '').trim(), ...args.map((entry) => String(entry ?? ''))]
    .filter((entry) => entry.length > 0);
  return tokens.map((entry) => quoteArg(entry)).join(' ');
}

function containsSensitiveText(value) {
  const text = String(value ?? '');
  return /(api[-_ ]?key|secret|token|authorization|bearer|sk-[a-z0-9]{8,})/i.test(text);
}

function pushSafeAction(target, action, warnings) {
  const command = stringValue(action.command);
  const cwd = stringValue(action.cwd);
  if (!command) {
    return;
  }
  if (containsSensitiveText(command) || containsSensitiveText(cwd)) {
    warnings.push(`Skipped action "${action.label || action.id || 'unknown'}" because command text appears to contain secrets/tokens.`);
    return;
  }
  target.push({
    id: action.id || null,
    label: action.label || action.id || 'Action',
    safety: action.safety || 'review',
    runnable: action.runnable !== false,
    dryRunFriendly: action.dryRunFriendly !== false,
    command,
    cwd: cwd || null,
    source: action.source || 'derived',
  });
}

function collectSafeActions({
  summaryPath,
  diagnosisPath,
  doctorPath,
  reportPath,
  outputPath,
  diagnosis,
  doctor,
  metadata,
}) {
  const actions = [];
  const warnings = [];

  for (const playbook of diagnosis.playbooks ?? []) {
    for (const command of playbook.commands ?? []) {
      pushSafeAction(actions, {
        id: stringValue(command.id) || null,
        label: stringValue(command.label) || stringValue(playbook.title) || stringValue(playbook.id),
        safety: stringValue(command.safety) || 'review',
        runnable: command.runnable !== false,
        dryRunFriendly: command.dryRunFriendly !== false,
        command: stringValue(command.rendered)
          || renderCommand(command.executable, Array.isArray(command.args) ? command.args : []),
        cwd: stringValue(command.cwd),
        source: `diagnosis.playbooks.${stringValue(playbook.id) || 'unknown'}`,
      }, warnings);
    }
  }

  for (const command of doctor.fixPlan?.commands ?? []) {
    pushSafeAction(actions, {
      id: stringValue(command.id) || null,
      label: stringValue(command.label) || stringValue(command.id) || 'Doctor fix command',
      safety: stringValue(command.safety) || 'review',
      runnable: command.runnable !== false,
      dryRunFriendly: command.dryRunFriendly !== false,
      command: renderCommand(command.executable, Array.isArray(command.args) ? command.args : []),
      cwd: stringValue(command.cwd) || stringValue(metadata.repoDir),
      source: 'doctor.fixPlan',
    }, warnings);
  }

  if (summaryPath && diagnosisPath) {
    pushSafeAction(actions, {
      id: 'rerun-analyze',
      label: 'Re-run analyzer',
      safety: 'read-only',
      runnable: true,
      dryRunFriendly: true,
      command: renderCommand('node', ['scripts/obsidian_debug_analyze.mjs', '--summary', summaryPath, '--output', diagnosisPath]),
      cwd: stringValue(metadata.repoDir),
      source: 'derived',
    }, warnings);
  }

  if (metadata.repoDir && metadata.pluginId && doctorPath) {
    pushSafeAction(actions, {
      id: 'rerun-doctor',
      label: 'Re-run doctor',
      safety: 'read-only',
      runnable: true,
      dryRunFriendly: true,
      command: renderCommand('node', [
        'scripts/obsidian_debug_doctor.mjs',
        '--repo-dir',
        metadata.repoDir,
        '--plugin-id',
        metadata.pluginId,
        '--output',
        doctorPath,
      ]),
      cwd: metadata.repoDir,
      source: 'derived',
    }, warnings);
  }

  if (diagnosisPath && reportPath) {
    pushSafeAction(actions, {
      id: 'rerun-report',
      label: 'Rebuild report',
      safety: 'read-only',
      runnable: true,
      dryRunFriendly: true,
      command: renderCommand('node', [
        'scripts/obsidian_debug_report.mjs',
        '--diagnosis',
        diagnosisPath,
        '--agent-tools',
        outputPath,
        '--output',
        reportPath,
      ]),
      cwd: stringValue(metadata.repoDir),
      source: 'derived',
    }, warnings);
  }

  if (diagnosisPath) {
    const diagnosisDir = path.dirname(path.resolve(diagnosisPath));
    pushSafeAction(actions, {
      id: 'generate-visual-review',
      label: 'Generate visual review pack',
      safety: 'read-only',
      runnable: true,
      dryRunFriendly: true,
      command: renderCommand('node', [
        'scripts/obsidian_debug_visual_review.mjs',
        '--diagnosis',
        diagnosisPath,
        '--output',
        path.join(diagnosisDir, 'visual-review.json'),
        '--html-output',
        path.join(diagnosisDir, 'visual-review.html'),
      ]),
      cwd: stringValue(metadata.repoDir),
      source: 'derived',
    }, warnings);
  }

  if (doctorPath || diagnosisPath || summaryPath) {
    const commandArgs = ['scripts/obsidian_debug_control_backend_support.mjs'];
    if (summaryPath) {
      commandArgs.push('--summary', summaryPath);
    }
    if (diagnosisPath) {
      commandArgs.push('--diagnosis', diagnosisPath);
    }
    if (doctorPath) {
      commandArgs.push('--doctor', doctorPath);
    }
    commandArgs.push('--output', path.join(path.dirname(path.resolve(doctorPath || diagnosisPath || summaryPath)), 'control-backends.json'));
    pushSafeAction(actions, {
      id: 'generate-control-backends',
      label: 'Generate control backend routing',
      safety: 'read-only',
      runnable: true,
      dryRunFriendly: true,
      command: renderCommand('node', commandArgs),
      cwd: stringValue(metadata.repoDir),
      source: 'derived',
    }, warnings);
  }

  if (summaryPath || diagnosisPath || doctorPath) {
    const commandArgs = ['scripts/obsidian_debug_agent_tools.mjs'];
    if (summaryPath) {
      commandArgs.push('--summary', summaryPath);
    }
    if (diagnosisPath) {
      commandArgs.push('--diagnosis', diagnosisPath);
    }
    if (doctorPath) {
      commandArgs.push('--doctor', doctorPath);
    }
    commandArgs.push('--output', outputPath);
    pushSafeAction(actions, {
      id: 'regenerate-agent-tools',
      label: 'Regenerate agent handoff manifest',
      safety: 'read-only',
      runnable: true,
      dryRunFriendly: true,
      command: renderCommand('node', commandArgs),
      cwd: stringValue(metadata.repoDir),
      source: 'derived',
    }, warnings);
  }

  const deduped = [];
  const seen = new Set();
  for (const action of actions) {
    const key = `${action.command}@@${action.cwd ?? ''}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    deduped.push(action);
  }

  return {
    actions: deduped,
    warnings,
  };
}

async function collectEvidence({
  summaryPath,
  diagnosisPath,
  doctorPath,
  reportPath,
  outputPath,
  summary,
  diagnosis,
}) {
  const items = [];

  function push(id, source, rawPath, required = false) {
    const normalized = stringValue(rawPath);
    if (!normalized) {
      return;
    }
    items.push({
      id,
      source,
      path: path.resolve(normalized),
      required,
    });
  }

  push('summary', 'input', summaryPath, true);
  push('diagnosis', 'input', diagnosisPath, true);
  push('doctor', 'input', doctorPath, false);
  push('reportHtml', 'input', reportPath, false);
  push('agentTools', 'output', outputPath, true);
  if (diagnosisPath) {
    const diagnosisDir = path.dirname(path.resolve(diagnosisPath));
    push('visualReview', 'derived', path.join(diagnosisDir, 'visual-review.json'));
    push('visualReviewHtml', 'derived', path.join(diagnosisDir, 'visual-review.html'));
    push('controlBackends', 'derived', path.join(diagnosisDir, 'control-backends.json'));
  } else if (doctorPath) {
    push('controlBackends', 'derived', path.join(path.dirname(path.resolve(doctorPath)), 'control-backends.json'));
  }

  const artifacts = asObject(diagnosis.artifacts);
  push('screenshot', 'diagnosis.artifacts', artifacts.screenshot);
  push('dom', 'diagnosis.artifacts', artifacts.dom);
  push('consoleLog', 'diagnosis.artifacts', artifacts.consoleLog);
  push('errorsLog', 'diagnosis.artifacts', artifacts.errorsLog);
  push('cdpTrace', 'diagnosis.artifacts', artifacts.cdpTrace);
  push('cdpSummary', 'diagnosis.artifacts', artifacts.cdpSummary);
  push('vaultLogCapture', 'diagnosis.artifacts', artifacts.vaultLogCapture);
  push('scenarioReport', 'diagnosis.artifacts', artifacts.scenarioReport);
  push('deployReport', 'diagnosis.artifacts', artifacts.deployReport);
  push('appLaunch', 'diagnosis.artifacts', artifacts.appLaunch);
  push('buildLog', 'diagnosis.artifacts', artifacts.buildLog);

  push('summaryConsoleLog', 'summary', summary.consoleLog);
  push('summaryErrorsLog', 'summary', summary.errorsLog);
  push('summaryCdpTrace', 'summary', summary.cdpTrace);
  push('summaryVaultLogCapture', 'summary', summary.vaultLogCapture);

  const deduped = [];
  const seen = new Set();
  for (const entry of items) {
    const key = `${entry.id}@@${entry.path}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    deduped.push(entry);
  }

  const withState = await Promise.all(deduped.map(async (entry) => ({
    ...entry,
    exists: entry.id === 'agentTools' ? true : await pathExists(entry.path),
  })));

  return {
    items: withState,
    availableCount: withState.filter((entry) => entry.exists).length,
    missingCount: withState.filter((entry) => !entry.exists).length,
  };
}

function collectRecommendations(diagnosis, doctor) {
  const diagnosisRecommendations = Array.isArray(diagnosis.recommendations)
    ? diagnosis.recommendations.filter((entry) => stringValue(entry))
    : [];
  const doctorRecommendations = [];

  for (const check of doctor.checks ?? []) {
    if (!['fail', 'warn', 'warning'].includes(stringValue(check.status).toLowerCase())) {
      continue;
    }
    const detail = stringValue(check.detail);
    if (detail) {
      doctorRecommendations.push(`${stringValue(check.id) || 'doctor-check'}: ${detail}`);
    }
  }

  const agenticSupport = asObject(doctor.agenticSupport);
  const agenticRecommendations = [
    ...(Array.isArray(agenticSupport.recommendations) ? agenticSupport.recommendations : []),
    ...(Array.isArray(agenticSupport.nextActions) ? agenticSupport.nextActions : []),
  ].filter((entry) => stringValue(entry));

  return uniqueStrings([
    ...diagnosisRecommendations,
    ...doctorRecommendations,
    ...agenticRecommendations,
  ]).slice(0, 16);
}

function collectWarnings({
  controlSurfaces,
  evidence,
  safeActionWarnings,
  summary,
  diagnosis,
  doctor,
}) {
  const warnings = [...safeActionWarnings];
  const missingRequired = evidence.items.filter((entry) => entry.required && !entry.exists);
  for (const item of missingRequired) {
    warnings.push(`Missing required evidence: ${item.id} (${item.path}).`);
  }

  for (const [name, surface] of Object.entries(controlSurfaces)) {
    if (surface.detected && !surface.available) {
      warnings.push(`Control surface "${name}" is detected but not confirmed runnable.`);
    }
  }

  const controlBackends = asObject(doctor.controlBackends);
  for (const backend of Object.values(asObject(controlBackends.backends))) {
    if (backend?.detected && !backend?.available) {
      warnings.push(`Control backend "${backend.id || backend.label || 'unknown'}" is detected but not confirmed runnable.`);
    }
  }

  const mcpSignalsText = JSON.stringify({
    agenticSupport: doctor.agenticSupport ?? null,
    checks: doctor.checks ?? [],
    recommendations: diagnosis.recommendations ?? [],
  }).toLowerCase();
  if (controlSurfaces.mcpRest.detected) {
    const hasBoundaryHint = /(localhost|127\.0\.0\.1|auth|token|api key|apikey|allowlist|whitelist)/i.test(mcpSignalsText);
    if (!hasBoundaryHint) {
      warnings.push('MCP/REST surface detected without clear localhost/auth/allowlist evidence. Review boundary controls before handing off.');
    }
  }

  const hasRawLogs = [summary.consoleLog, summary.errorsLog, summary.cdpTrace, diagnosis.artifacts?.vaultLogCapture]
    .some((entry) => stringValue(entry).length > 0);
  if (hasRawLogs) {
    warnings.push('Review raw logs for sensitive values before sharing the handoff package.');
  }

  return uniqueStrings(warnings);
}

export async function generateAgentToolsManifest({
  summaryPath = '',
  diagnosisPath = '',
  doctorPath = '',
  outputPath = '',
  reportPath = '',
  summaryDocument = null,
  diagnosisDocument = null,
  doctorDocument = null,
} = {}) {
  const resolvedSummaryPath = summaryPath ? path.resolve(summaryPath) : '';
  const resolvedDiagnosisPath = diagnosisPath ? path.resolve(diagnosisPath) : '';
  const resolvedDoctorPath = doctorPath ? path.resolve(doctorPath) : '';
  const resolvedReportPath = reportPath ? path.resolve(reportPath) : '';

  const summaryRaw = summaryDocument ?? await readJsonOrNull(resolvedSummaryPath);
  const diagnosisRaw = diagnosisDocument ?? await readJsonOrNull(resolvedDiagnosisPath);
  const doctorRaw = doctorDocument ?? await readJsonOrNull(resolvedDoctorPath);

  if (!summaryRaw && !diagnosisRaw && !doctorRaw) {
    throw new Error('At least one of --summary, --diagnosis, or --doctor must point to readable JSON.');
  }

  const summary = normalizeSummaryPaths(summaryRaw ?? {}, resolvedSummaryPath || resolvedDiagnosisPath || resolvedDoctorPath);
  const diagnosis = normalizeDiagnosisPaths(diagnosisRaw ?? {}, resolvedDiagnosisPath || resolvedSummaryPath || resolvedDoctorPath);
  const doctor = asObject(doctorRaw);

  const defaultOutputBase = resolvedDiagnosisPath || resolvedSummaryPath || resolvedDoctorPath || process.cwd();
  const resolvedOutputPath = path.resolve(
    outputPath || path.join(path.dirname(defaultOutputBase), 'agent-tools.json'),
  );

  const metadata = {
    generatedAt: nowIso(),
    status: stringValue(diagnosis.status)
      || stringValue(doctor.status)
      || 'unknown',
    pluginId: stringValue(diagnosis.pluginId)
      || stringValue(doctor.pluginId)
      || stringValue(summary.pluginId)
      || null,
    vaultName: stringValue(diagnosis.vaultName)
      || stringValue(doctor.vaultName)
      || stringValue(summary.vaultName)
      || null,
    repoDir: stringValue(diagnosis.runtime?.repoDir)
      || stringValue(doctor.repoDir)
      || stringValue(summary.repoDir)
      || null,
    outputDir: stringValue(diagnosis.runtime?.outputDir)
      || stringValue(summary.outputDir)
      || null,
  };

  const controlSurfaces = inferControlSurfaces({
    summary,
    diagnosis,
    doctor,
  });
  const controlBackends = Object.keys(asObject(doctor.controlBackends)).length > 0
    ? doctor.controlBackends
    : detectControlBackends({
        summaryDocument: summary,
        diagnosisDocument: diagnosis,
        doctorDocument: doctor,
      });
  const safeActionResult = collectSafeActions({
    summaryPath: resolvedSummaryPath || diagnosis.runtime?.summaryPath || null,
    diagnosisPath: resolvedDiagnosisPath || null,
    doctorPath: resolvedDoctorPath || null,
    reportPath: resolvedReportPath || null,
    outputPath: resolvedOutputPath,
    diagnosis,
    doctor,
    metadata,
  });
  const evidence = await collectEvidence({
    summaryPath: resolvedSummaryPath || diagnosis.runtime?.summaryPath || null,
    diagnosisPath: resolvedDiagnosisPath || null,
    doctorPath: resolvedDoctorPath || null,
    reportPath: resolvedReportPath || null,
    outputPath: resolvedOutputPath,
    summary,
    diagnosis,
  });
  const nextRecommendations = collectRecommendations(diagnosis, doctor);
  const warnings = collectWarnings({
    controlSurfaces,
    evidence,
    safeActionWarnings: safeActionResult.warnings,
    summary,
    diagnosis,
    doctor,
  });

  const manifest = {
    metadata,
    controlSurfaces,
    controlBackends,
    safeActions: safeActionResult.actions,
    evidence,
    nextRecommendations,
    warnings,
  };

  await ensureParentDirectory(resolvedOutputPath);
  await fs.writeFile(resolvedOutputPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  return manifest;
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
Usage: node scripts/obsidian_debug_agent_tools.mjs [options]

Options:
  --summary <path>          Optional summary.json input.
  --diagnosis <path>        Optional diagnosis.json input.
  --doctor <path>           Optional doctor.json input.
  --report <path>           Optional HTML report path for evidence linking.
  --output <path>           Output path. Defaults near the first available input.
`);
  }

  const summaryPath = getStringOption(options, 'summary', '').trim();
  const diagnosisPath = getStringOption(options, 'diagnosis', '').trim();
  const doctorPath = getStringOption(options, 'doctor', '').trim();
  const reportPath = getStringOption(options, 'report', '').trim();
  const outputPath = getStringOption(options, 'output', '').trim();

  const manifest = await generateAgentToolsManifest({
    summaryPath,
    diagnosisPath,
    doctorPath,
    reportPath,
    outputPath,
  });
  console.log(JSON.stringify(manifest, null, 2));
}
