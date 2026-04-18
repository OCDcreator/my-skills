import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  ensureParentDirectory,
  getStringOption,
  nowIso,
  parseArgs,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
const summaryPath = getStringOption(options, 'summary').trim();
if (!summaryPath) {
  throw new Error('--summary is required');
}

const domSelector = getStringOption(options, 'dom-selector', '').trim();
const outputPath = getStringOption(
  options,
  'output',
  path.join(path.dirname(path.resolve(summaryPath)), 'diagnosis.json'),
);
const assertionsPath = getStringOption(options, 'assertions', '').trim();
const signaturesPath = getStringOption(
  options,
  'signatures',
  path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'rules', 'issue-signatures.json'),
);

function normalizeTimestamp(raw) {
  if (!raw) {
    return null;
  }

  const normalized = raw.replace(/([+-]\d{2})(\d{2})$/, '$1:$2');
  const parsed = Date.parse(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

async function readTextIfExists(filePath) {
  if (!filePath) {
    return null;
  }

  try {
    return await fs.readFile(filePath, 'utf8');
  } catch {
    return null;
  }
}

async function readJsonIfExists(filePath) {
  const text = await readTextIfExists(filePath);
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text.replace(/^\uFEFF/, ''));
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

function splitLines(text, filePath) {
  if (!text) {
    return [];
  }

  return text.split(/\r?\n/).map((line, index) => ({
    filePath,
    lineNumber: index + 1,
    text: line,
  })).filter((entry) => entry.text.trim().length > 0);
}

function getLineTimestamp(line) {
  const match = line.match(/^(\d{4}-\d{2}-\d{2}T[0-9:.+\-Z]+)\s/);
  return normalizeTimestamp(match?.[1] ?? null);
}

function parseCompletedMetrics(lines) {
  const pattern = /^\[([^\]]+)\]\s+\[([^\]]+)\]\s+(?:(.+?)\s+)?completed in (\d+(?:\.\d+)?)ms/;
  const metrics = [];

  for (const line of lines) {
    const normalizedText = line.text
      .replace(/^\d{4}-\d{2}-\d{2}T[0-9:.+\-Z]+\s+/, '')
      .replace(/^\[(?:console|log|runtime)\.[^\]]+\]\s+/, '')
      .replace(/^\d{2}:\d{2}:\d{2}\s+/, '')
      .replace(/^\[\d{2}:\d{2}:\d{2}\]\s+/, '');
    const match = normalizedText.match(pattern);
    if (!match) {
      continue;
    }

    metrics.push({
      component: match[1],
      phase: match[2],
      label: match[3]?.trim() || 'completed',
      ms: Number(match[4]),
      filePath: line.filePath,
      lineNumber: line.lineNumber,
      text: line.text,
    });
  }

  return metrics;
}

function getFirstMatchingLine(lines, predicates) {
  for (const predicate of predicates) {
    const line = lines.find((entry) => predicate(entry.text));
    if (line) {
      return line;
    }
  }
  return null;
}

function evaluateTimingOperator(left, operator, right) {
  if (!Number.isFinite(left) || !Number.isFinite(right)) {
    return false;
  }

  switch (operator) {
    case 'gt':
      return left > right;
    case 'gte':
      return left >= right;
    case 'lt':
      return left < right;
    case 'lte':
      return left <= right;
    case 'eq':
      return left === right;
    default:
      return false;
  }
}

function getSeverityRank(severity) {
  switch (severity) {
    case 'error':
      return 3;
    case 'warning':
      return 2;
    case 'info':
      return 1;
    default:
      return 0;
  }
}

const summary = JSON.parse((await fs.readFile(summaryPath, 'utf8')).replace(/^\uFEFF/, ''));
const signaturesDocument = (await readJsonIfExists(signaturesPath)) ?? { signatures: [] };

const consoleText = await readTextIfExists(summary.consoleLog);
const errorsText = await readTextIfExists(summary.errorsLog);
const cdpTraceText = await readTextIfExists(summary.cdpTrace);
const domText = await readTextIfExists(summary.dom);
const deployReport = await readJsonIfExists(summary.deployReport);
const cdpSummary = await readJsonIfExists(summary.cdpSummary);
const scenarioReport = await readJsonIfExists(summary.scenarioReport);
const assertionsDocument = assertionsPath ? ((await readJsonIfExists(assertionsPath)) ?? { assertions: [] }) : null;
const screenshotExists = await pathExists(summary.screenshot);
const domExists = await pathExists(summary.dom);

const allLines = [
  ...splitLines(consoleText, summary.consoleLog),
  ...splitLines(errorsText, summary.errorsLog),
  ...splitLines(cdpTraceText, summary.cdpTrace),
];

const completedMetrics = parseCompletedMetrics(allLines);
const startupCompleted = completedMetrics.find(
  (entry) => entry.component === 'OpenCodian' && entry.phase === 'startup' && entry.label.trim() === 'completed',
) ?? completedMetrics.find(
  (entry) => entry.phase === 'startup' && entry.label.trim() === 'completed',
);
const viewOpenCompleted = completedMetrics.find(
  (entry) => entry.component === 'OpenCodianView' && entry.phase === 'view-open' && entry.label.trim() === 'completed',
) ?? completedMetrics.find(
  (entry) => entry.phase === 'view-open' && entry.label.trim() === 'completed',
);
const serverReadyLine = getFirstMatchingLine(allLines, [
  (text) => text.includes('local OpenCode server ready in '),
  (text) => text.includes('ServerManager.start completed in '),
  (text) => text.includes('Server status -> running'),
]);
const chatReadyLine = getFirstMatchingLine(allLines, [
  (text) => text.includes('Chat server availability -> running'),
]);
const startupBeginLine = getFirstMatchingLine(allLines, [
  (text) => text.includes('startup begin'),
  (text) => text.includes('plugin reload'),
]);

const serverReadyDurationMatch = serverReadyLine?.text.match(/ready in (\d+(?:\.\d+)?)ms|completed in (\d+(?:\.\d+)?)ms/);
const startupAnchorTimestamp = getLineTimestamp(startupBeginLine?.text ?? '') ?? getLineTimestamp(allLines[0]?.text ?? '');
const chatReadyTimestamp = getLineTimestamp(chatReadyLine?.text ?? '');

const timingMetrics = {
  startupCompletedMs: startupCompleted?.ms ?? null,
  viewOpenCompletedMs: viewOpenCompleted?.ms ?? null,
  serverReadyMs: serverReadyDurationMatch ? Number(serverReadyDurationMatch[1] ?? serverReadyDurationMatch[2]) : null,
  chatReadyDelayMs:
    Number.isFinite(startupAnchorTimestamp)
    && Number.isFinite(chatReadyTimestamp)
      ? Math.max(0, chatReadyTimestamp - startupAnchorTimestamp)
      : null,
};

const assertions = [];

function pushAssertion(id, status, detail, evidence = []) {
  assertions.push({ id, status, detail, evidence });
}

if (summary.consoleLog || summary.cdpTrace) {
  pushAssertion(
    'trace-captured',
    allLines.length > 0 ? 'pass' : 'fail',
    allLines.length > 0 ? `Captured ${allLines.length} log lines.` : 'No console/CDP trace lines were captured.',
    allLines.length > 0 ? [{ filePath: allLines[0].filePath, lineNumber: allLines[0].lineNumber }] : [],
  );
}

pushAssertion(
  'screenshot-captured',
  screenshotExists ? 'pass' : 'fail',
  screenshotExists ? `Screenshot artifact recorded at ${summary.screenshot}.` : 'Screenshot artifact is missing.',
  screenshotExists ? [{ filePath: summary.screenshot, lineNumber: 1 }] : [],
);

const domMatched = ((cdpSummary?.count ?? null) > 0)
  || (domExists && typeof domText === 'string' && domText.trim().length > 0 && (domText.includes('<') || !domText.startsWith('No ')));
pushAssertion(
  'dom-root-present',
  domMatched ? 'pass' : 'fail',
  domMatched
    ? `DOM capture produced content${domSelector ? ` for selector ${domSelector}` : ''}.`
    : `DOM capture is empty${domSelector ? ` for selector ${domSelector}` : ''}.`,
  summary.dom ? [{ filePath: summary.dom, lineNumber: 1 }] : [],
);

if (Array.isArray(deployReport)) {
  const unmatched = deployReport.filter((entry) => entry?.matched === false);
  pushAssertion(
    'deploy-artifacts-match',
    unmatched.length === 0 ? 'pass' : 'fail',
    unmatched.length === 0
      ? `Deploy report matched for ${deployReport.length} artifact(s).`
      : `Deploy report found ${unmatched.length} mismatched artifact(s).`,
    deployReport.length > 0 ? [{ filePath: summary.deployReport, lineNumber: 1 }] : [],
  );
} else {
  pushAssertion('deploy-artifacts-match', 'skipped', 'Deploy was skipped or no deploy report exists.');
}

if (scenarioReport) {
  pushAssertion(
    'scenario-succeeded',
    scenarioReport.success ? 'pass' : 'fail',
    scenarioReport.success
      ? `Scenario ${scenarioReport.scenarioName} completed successfully.`
      : `Scenario ${scenarioReport.scenarioName} failed.`,
    [{ filePath: summary.scenarioReport, lineNumber: 1 }],
  );
}

const matchedSignatures = [];
for (const signature of signaturesDocument.signatures ?? []) {
  if (signature.type === 'text') {
    const matches = allLines.filter((line) => {
      const hasAny = (signature.matchAny ?? []).some((needle) => line.text.includes(needle));
      const hasAll = (signature.matchAll ?? []).every((needle) => line.text.includes(needle));
      if ((signature.matchAny ?? []).length > 0 && !hasAny) {
        return false;
      }
      if ((signature.matchAll ?? []).length > 0 && !hasAll) {
        return false;
      }
      return true;
    });

    if (matches.length === 0) {
      continue;
    }

    matchedSignatures.push({
      id: signature.id,
      type: signature.type,
      severity: signature.severity,
      headline: signature.headline,
      likelyCause: signature.likelyCause,
      nextActions: signature.nextActions ?? [],
      matches: matches.slice(0, 8).map((line) => ({
        filePath: line.filePath,
        lineNumber: line.lineNumber,
        text: line.text,
      })),
    });
    continue;
  }

  if (signature.type === 'timing-threshold') {
    const metricValue = timingMetrics[signature.metric];
    if (!evaluateTimingOperator(metricValue, signature.operator, Number(signature.value))) {
      continue;
    }

    matchedSignatures.push({
      id: signature.id,
      type: signature.type,
      severity: signature.severity,
      headline: signature.headline,
      likelyCause: signature.likelyCause,
      nextActions: signature.nextActions ?? [],
      metric: signature.metric,
      metricValue,
      operator: signature.operator,
      threshold: Number(signature.value),
      matches: [],
    });
  }
}

const combinedLogText = allLines.map((entry) => entry.text).join('\n');
const customAssertions = [];

function pushCustomAssertion(id, status, detail, evidence = []) {
  customAssertions.push({ id, status, detail, evidence });
}

for (const assertion of assertionsDocument?.assertions ?? []) {
  const assertionId = assertion.id ?? assertion.type ?? `assertion-${customAssertions.length + 1}`;

  switch (assertion.type) {
    case 'artifact-exists': {
      const field = assertion.field;
      const targetPath = summary[field] ?? null;
      const exists = await pathExists(targetPath);
      pushCustomAssertion(
        assertionId,
        exists ? 'pass' : 'fail',
        exists ? `Artifact ${field} exists at ${targetPath}.` : `Artifact ${field} is missing.`,
        exists ? [{ filePath: targetPath, lineNumber: 1 }] : [],
      );
      break;
    }
    case 'scenario-success': {
      const ok = scenarioReport?.success === true;
      pushCustomAssertion(
        assertionId,
        ok ? 'pass' : 'fail',
        ok ? 'Scenario completed successfully.' : 'Scenario report is missing or failed.',
        summary.scenarioReport ? [{ filePath: summary.scenarioReport, lineNumber: 1 }] : [],
      );
      break;
    }
    case 'dom-contains': {
      const needle = String(assertion.value ?? '');
      const ok = typeof domText === 'string' && needle.length > 0 && domText.includes(needle);
      pushCustomAssertion(
        assertionId,
        ok ? 'pass' : 'fail',
        ok ? `DOM contains ${needle}.` : `DOM does not contain ${needle}.`,
        summary.dom ? [{ filePath: summary.dom, lineNumber: 1 }] : [],
      );
      break;
    }
    case 'log-contains':
    case 'log-not-contains': {
      const needle = String(assertion.value ?? '');
      const source = assertion.source ?? 'combined';
      const haystack = source === 'errors'
        ? (errorsText ?? '')
        : source === 'console'
          ? (consoleText ?? '')
          : source === 'cdp'
            ? (cdpTraceText ?? '')
            : combinedLogText;
      const line = allLines.find((entry) => entry.text.includes(needle));
      const contains = needle.length > 0 && haystack.includes(needle);
      const ok = assertion.type === 'log-contains' ? contains : !contains;
      pushCustomAssertion(
        assertionId,
        ok ? 'pass' : 'fail',
        ok
          ? `${assertion.type} satisfied for ${needle}.`
          : `${assertion.type} failed for ${needle}.`,
        line ? [{ filePath: line.filePath, lineNumber: line.lineNumber }] : [],
      );
      break;
    }
    case 'timing-max':
    case 'timing-min': {
      const metric = assertion.metric;
      const limit = Number(assertion.value);
      const metricValue = timingMetrics[metric];
      const allowMissing = assertion.allowMissing === true;
      let ok = false;
      if (!Number.isFinite(metricValue)) {
        ok = allowMissing;
      } else if (assertion.type === 'timing-max') {
        ok = metricValue <= limit;
      } else {
        ok = metricValue >= limit;
      }

      pushCustomAssertion(
        assertionId,
        ok ? 'pass' : 'fail',
        Number.isFinite(metricValue)
          ? `${metric}=${metricValue}ms (${assertion.type} ${limit}ms).`
          : `${metric} is missing.`,
        [{ filePath: path.resolve(summaryPath), lineNumber: 1 }],
      );
      break;
    }
    case 'signature-present':
    case 'signature-absent': {
      const targetId = String(assertion.value ?? '');
      const exists = matchedSignatures.some((entry) => entry.id === targetId);
      const ok = assertion.type === 'signature-present' ? exists : !exists;
      pushCustomAssertion(
        assertionId,
        ok ? 'pass' : 'fail',
        ok
          ? `${assertion.type} satisfied for ${targetId}.`
          : `${assertion.type} failed for ${targetId}.`,
        [{ filePath: path.resolve(summaryPath), lineNumber: 1 }],
      );
      break;
    }
    default:
      pushCustomAssertion(
        assertionId,
        'fail',
        `Unsupported assertion type: ${assertion.type ?? 'unknown'}.`,
        assertionsPath ? [{ filePath: assertionsPath, lineNumber: 1 }] : [],
      );
      break;
  }
}

const topSlowSteps = [...completedMetrics]
  .sort((left, right) => right.ms - left.ms)
  .slice(0, 10)
  .map((entry) => ({
    component: entry.component,
    phase: entry.phase,
    label: entry.label,
    ms: entry.ms,
    filePath: entry.filePath,
    lineNumber: entry.lineNumber,
  }));

const assertionStatusRank = {
  fail: 3,
  pass: 1,
  skipped: 0,
};

let status = 'pass';
if (
  matchedSignatures.some((entry) => entry.severity === 'error')
  || assertions.some((entry) => entry.status === 'fail')
  || customAssertions.some((entry) => entry.status === 'fail')
) {
  status = 'fail';
} else if (matchedSignatures.some((entry) => entry.severity === 'warning')) {
  status = 'warning';
}

const highestSeveritySignature = [...matchedSignatures].sort(
  (left, right) => getSeverityRank(right.severity) - getSeverityRank(left.severity),
)[0];

const headline = highestSeveritySignature
  ? highestSeveritySignature.headline
  : customAssertions.find((entry) => entry.status === 'fail')?.detail
    ?? (assertions.some((entry) => entry.status === 'fail')
      ? 'Automation completed, but one or more required artifacts/assertions failed.'
      : 'Automation completed and the captured artifacts look healthy.');

const recommendations = [...new Set(matchedSignatures.flatMap((entry) => entry.nextActions ?? []))];

const diagnosis = {
  generatedAt: nowIso(),
  status,
  headline,
  pluginId: summary.pluginId,
  vaultName: summary.vaultName,
  useCdp: summary.useCdp,
  domSelector: domSelector || null,
  artifacts: {
    summary: path.resolve(summaryPath),
    buildLog: summary.buildLog,
    deployReport: summary.deployReport,
    consoleLog: summary.consoleLog,
    errorsLog: summary.errorsLog,
    cdpTrace: summary.cdpTrace,
    cdpSummary: summary.cdpSummary,
    scenarioReport: summary.scenarioReport ?? null,
    screenshot: summary.screenshot,
    dom: summary.dom,
  },
  assertions,
  customAssertions,
  timings: timingMetrics,
  topSlowSteps,
  signatures: matchedSignatures,
  recommendations,
  assertionsPath: assertionsPath || null,
  scenario: scenarioReport
    ? {
        name: scenarioReport.scenarioName,
        success: scenarioReport.success,
        stepCount: Array.isArray(scenarioReport.steps) ? scenarioReport.steps.length : 0,
      }
    : null,
  traces: {
    lineCount: allLines.length,
    firstLineTimestamp: startupAnchorTimestamp ? new Date(startupAnchorTimestamp).toISOString() : null,
    lastLineTimestamp: (() => {
      const last = [...allLines].reverse().find((entry) => getLineTimestamp(entry.text));
      const parsed = getLineTimestamp(last?.text ?? '');
      return parsed ? new Date(parsed).toISOString() : null;
    })(),
  },
};

await ensureParentDirectory(outputPath);
await fs.writeFile(outputPath, `${JSON.stringify(diagnosis, null, 2)}\n`, 'utf8');
console.log(JSON.stringify(diagnosis, null, 2));
