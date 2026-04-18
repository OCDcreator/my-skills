import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  ensureParentDirectory,
  getStringOption,
  nowIso,
  parseArgs,
} from './obsidian_cdp_common.mjs';
import {
  deriveVaultRoot,
  normalizePlatform,
  resolveTemplateCommand,
} from './obsidian_debug_command_templates.mjs';

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
const playbooksPath = getStringOption(
  options,
  'playbooks',
  path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'rules', 'issue-playbooks.json'),
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

function stringValue(value) {
  return typeof value === 'string' ? value.trim() : '';
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

function escapeRegExp(value) {
  return String(value ?? '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function toFiniteNumber(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizeAssertionSeverity(severity) {
  const normalized = String(severity ?? 'fail').trim().toLowerCase();
  if (normalized === 'warning') {
    return 'warn';
  }

  if (['fail', 'warn', 'expected', 'flaky'].includes(normalized)) {
    return normalized;
  }

  return 'fail';
}

function statusForAssertion(ok, severity) {
  return ok ? 'pass' : normalizeAssertionSeverity(severity);
}

function isWarningStatus(status) {
  return status === 'warn' || status === 'warning';
}

function isPassingOrSkipped(status) {
  return status === 'pass' || status === 'skipped';
}

function compareNumber(actual, operator, expected) {
  if (!Number.isFinite(actual) || !Number.isFinite(expected)) {
    return false;
  }

  switch (String(operator ?? '').toLowerCase()) {
    case 'gt':
    case '>':
      return actual > expected;
    case 'gte':
    case '>=':
      return actual >= expected;
    case 'lt':
    case '<':
      return actual < expected;
    case 'lte':
    case '<=':
      return actual <= expected;
    case 'eq':
    case 'equals':
    case '=':
    case '==':
      return actual === expected;
    case 'ne':
    case 'not-equals':
    case '!=':
      return actual !== expected;
    default:
      return false;
  }
}

function getNumericExpectation(assertion, defaultOperator = 'gte', defaultExpected = 1) {
  const exact = toFiniteNumber(assertion.count ?? assertion.equals ?? assertion.exact);
  if (exact !== null) {
    return { operator: 'eq', expected: exact };
  }

  const max = toFiniteNumber(assertion.max ?? assertion.maxMs ?? assertion.budgetMs);
  if (max !== null) {
    return { operator: 'lte', expected: max };
  }

  const min = toFiniteNumber(assertion.min ?? assertion.minMs);
  if (min !== null) {
    return { operator: 'gte', expected: min };
  }

  const value = toFiniteNumber(assertion.value);
  if (value !== null && assertion.operator) {
    return { operator: assertion.operator, expected: value };
  }

  return { operator: assertion.operator ?? defaultOperator, expected: defaultExpected };
}

function describeNumericExpectation(operator, expected) {
  return `${operator} ${expected}`;
}

function compileRegex(pattern, flags = '') {
  try {
    return { regex: new RegExp(String(pattern ?? ''), String(flags ?? '')) };
  } catch (error) {
    return { error };
  }
}

function countRegexMatches(text, regex) {
  if (!regex.global) {
    return regex.test(text) ? 1 : 0;
  }

  const matches = text.match(regex);
  return matches ? matches.length : 0;
}

function stripHtmlTags(value) {
  return String(value ?? '')
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function getTerminalSelectorPart(selector) {
  return String(selector ?? '')
    .trim()
    .split(/\s+|>|\+|~/)
    .filter(Boolean)
    .pop()
    ?? '';
}

function parseSimpleSelector(selector) {
  const simple = getTerminalSelectorPart(selector).replace(/:{1,2}[\w-]+(?:\([^)]*\))?/g, '');
  const tagMatch = simple.match(/^[a-zA-Z][\w:-]*/);
  const tagName = tagMatch ? tagMatch[0].toLowerCase() : null;
  const ids = [...simple.matchAll(/#([\w-]+)/g)].map((match) => match[1]);
  const classes = [...simple.matchAll(/\.([\w-]+)/g)].map((match) => match[1]);
  const attributes = [...simple.matchAll(/\[([^\]=~|^$*\s]+)(?:\s*[*^$|~]?=\s*["']?([^"'\]]+)["']?)?\]/g)]
    .map((match) => ({
      name: match[1],
      value: match[2] ?? null,
    }));

  return { tagName, ids, classes, attributes };
}

function readAttribute(attrsText, name) {
  const pattern = new RegExp(
    `(?:^|\\s)${escapeRegExp(name)}(?:\\s*=\\s*(?:"([^"]*)"|'([^']*)'|([^\\s"'<>]+)))?`,
    'i',
  );
  const match = String(attrsText ?? '').match(pattern);
  if (!match) {
    return { exists: false, value: null };
  }

  return {
    exists: true,
    value: match[1] ?? match[2] ?? match[3] ?? '',
  };
}

function parseStyleAttribute(styleText) {
  const entries = {};
  for (const part of String(styleText ?? '').split(';')) {
    const [rawName, ...rawValue] = part.split(':');
    const name = rawName?.trim().toLowerCase();
    if (!name || rawValue.length === 0) {
      continue;
    }
    entries[name] = rawValue.join(':').trim();
  }
  return entries;
}

function extractElementSnippet(html, startIndex, openingTag, tagName) {
  const openEnd = startIndex + openingTag.length;
  const closeToken = `</${tagName.toLowerCase()}>`;
  const closeIndex = html.toLowerCase().indexOf(closeToken, openEnd);
  if (closeIndex >= 0) {
    return html.slice(startIndex, Math.min(closeIndex + closeToken.length, startIndex + 5000));
  }

  return html.slice(startIndex, Math.min(html.length, startIndex + 500));
}

function elementMatchesParsedSelector(element, parsedSelector) {
  if (parsedSelector.tagName && parsedSelector.tagName !== element.tagName.toLowerCase()) {
    return false;
  }

  for (const id of parsedSelector.ids) {
    if (readAttribute(element.attrsText, 'id').value !== id) {
      return false;
    }
  }

  const classValue = readAttribute(element.attrsText, 'class').value ?? '';
  const classNames = new Set(classValue.split(/\s+/).filter(Boolean));
  for (const className of parsedSelector.classes) {
    if (!classNames.has(className)) {
      return false;
    }
  }

  for (const attribute of parsedSelector.attributes) {
    const actual = readAttribute(element.attrsText, attribute.name);
    if (!actual.exists) {
      return false;
    }
    if (attribute.value !== null && actual.value !== attribute.value) {
      return false;
    }
  }

  return true;
}

function findDomElements(html, selector) {
  const text = String(html ?? '');
  if (!selector || !text.includes('<')) {
    return [];
  }

  const selectorParts = String(selector)
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
    .map(parseSimpleSelector);
  if (selectorParts.length === 0) {
    return [];
  }

  const matches = [];
  const seen = new Set();
  const elementPattern = /<([a-zA-Z][\w:-]*)(\s[^<>]*?)?\s*\/?>/g;
  let match;
  while ((match = elementPattern.exec(text)) !== null) {
    const element = {
      tagName: match[1],
      attrsText: match[2] ?? '',
      openingTag: match[0],
      index: match.index,
      snippet: extractElementSnippet(text, match.index, match[0], match[1]),
    };
    if (!selectorParts.some((part) => elementMatchesParsedSelector(element, part))) {
      continue;
    }
    if (seen.has(element.index)) {
      continue;
    }
    seen.add(element.index);
    matches.push({
      ...element,
      textContent: stripHtmlTags(element.snippet),
    });
  }

  return matches;
}

function cdpSummaryMatchesSelector(cdpSummaryDocument, selector) {
  return cdpSummaryDocument?.selector
    && selector
    && String(cdpSummaryDocument.selector).trim() === String(selector).trim()
    && Array.isArray(cdpSummaryDocument.matches);
}

function getSelectorCount({ selector, html, cdpSummaryDocument }) {
  if (cdpSummaryDocument?.selector && String(cdpSummaryDocument.selector).trim() === String(selector ?? '').trim()) {
    const count = toFiniteNumber(cdpSummaryDocument.count);
    if (count !== null) {
      return count;
    }
  }

  return findDomElements(html, selector).length;
}

function isElementVisible(element) {
  if (readAttribute(element.attrsText, 'hidden').exists) {
    return false;
  }

  if (String(readAttribute(element.attrsText, 'aria-hidden').value ?? '').toLowerCase() === 'true') {
    return false;
  }

  const styles = parseStyleAttribute(readAttribute(element.attrsText, 'style').value ?? '');
  if (styles.display?.toLowerCase() === 'none') {
    return false;
  }
  if (['hidden', 'collapse'].includes(styles.visibility?.toLowerCase())) {
    return false;
  }
  if (styles.opacity === '0') {
    return false;
  }

  return true;
}

function isCdpMatchVisible(match) {
  const display = String(match.computedStyle?.display ?? match.display ?? '').toLowerCase();
  const visibility = String(match.computedStyle?.visibility ?? match.visibility ?? '').toLowerCase();
  const opacity = String(match.computedStyle?.opacity ?? match.opacity ?? '');

  return display !== 'none' && !['hidden', 'collapse'].includes(visibility) && opacity !== '0';
}

function getStyleValues({ selector, property, html, cdpSummaryDocument }) {
  const normalizedProperty = String(property ?? '').trim().toLowerCase();
  const values = [];

  if (cdpSummaryMatchesSelector(cdpSummaryDocument, selector)) {
    for (const match of cdpSummaryDocument.matches) {
      const computedValue = match.computedStyle?.[normalizedProperty]
        ?? match[normalizedProperty]
        ?? (normalizedProperty === 'pointer-events' ? match.pointerEvents : undefined);
      if (computedValue !== undefined && computedValue !== null) {
        values.push({
          value: String(computedValue),
          source: 'cdp-summary',
        });
      }
    }
  }

  for (const element of findDomElements(html, selector)) {
    const styles = parseStyleAttribute(readAttribute(element.attrsText, 'style').value ?? '');
    if (styles[normalizedProperty] !== undefined) {
      values.push({
        value: styles[normalizedProperty],
        source: 'inline-style',
        evidence: { filePath: element.filePath, lineNumber: 1 },
      });
    }
  }

  return values;
}

function evaluateStringExpectation(actualValue, assertion) {
  const actual = String(actualValue ?? '');
  if (assertion.pattern !== undefined || assertion.regex !== undefined) {
    const { regex, error } = compileRegex(assertion.pattern ?? assertion.regex, assertion.flags ?? '');
    if (error) {
      return { ok: false, detail: `Invalid regex: ${error.message}` };
    }
    const ok = regex.test(actual);
    return {
      ok,
      detail: `value ${ok ? 'matches' : 'does not match'} /${regex.source}/${regex.flags}`,
    };
  }

  if (assertion.contains !== undefined) {
    const expected = String(assertion.contains);
    return {
      ok: actual.includes(expected),
      detail: `value ${actual.includes(expected) ? 'contains' : 'does not contain'} ${expected}`,
    };
  }

  if (assertion.notContains !== undefined) {
    const expected = String(assertion.notContains);
    return {
      ok: !actual.includes(expected),
      detail: `value ${actual.includes(expected) ? 'contains' : 'does not contain'} ${expected}`,
    };
  }

  if (assertion.operator === 'not-equals' || assertion.operator === 'ne' || assertion.notEquals !== undefined) {
    const expected = String(assertion.notEquals ?? assertion.value ?? assertion.expected ?? '');
    return {
      ok: actual !== expected,
      detail: `value ${actual !== expected ? 'differs from' : 'equals'} ${expected}`,
    };
  }

  const expected = String(assertion.expected ?? assertion.value ?? '');
  return {
    ok: actual === expected,
    detail: `value ${actual === expected ? 'equals' : 'does not equal'} ${expected}`,
  };
}

const summary = JSON.parse((await fs.readFile(summaryPath, 'utf8')).replace(/^\uFEFF/, ''));
const signaturesDocument = (await readJsonIfExists(signaturesPath)) ?? { signatures: [] };
const playbooksDocument = (await readJsonIfExists(playbooksPath)) ?? { playbooks: [] };
const toolRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outputDir = stringValue(summary.outputDir)
  ? path.resolve(summary.outputDir)
  : path.dirname(path.resolve(outputPath));
const repoDir = stringValue(summary.repoDir)
  ? path.resolve(summary.repoDir)
  : '';
const testVaultPluginDir = stringValue(summary.testVaultPluginDir)
  ? path.resolve(summary.testVaultPluginDir)
  : '';
const platform = normalizePlatform('auto');
const runtimeContext = {
  toolRoot,
  summaryPath: path.resolve(summaryPath),
  diagnosisPath: path.resolve(outputPath),
  playbooksPath: path.resolve(playbooksPath),
  repoDir,
  outputDir,
  pluginId: stringValue(summary.pluginId),
  vaultName: stringValue(summary.vaultName),
  obsidianCommand: stringValue(summary.obsidianCommand),
  domSelector: domSelector || '.workspace-leaf.mod-active',
  testVaultPluginDir,
  vaultRoot: deriveVaultRoot(testVaultPluginDir),
};

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
  assertions.push({ id, status, severity: status === 'fail' ? 'fail' : null, detail, evidence });
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

function pushCustomAssertion(assertion, id, ok, detail, evidence = [], extra = {}) {
  const severity = normalizeAssertionSeverity(assertion.severity);
  const result = {
    id,
    type: assertion.type ?? null,
    status: statusForAssertion(ok, severity),
    severity,
    detail,
    evidence,
    ...extra,
  };

  if (assertion.description) {
    result.description = assertion.description;
  }

  customAssertions.push(result);
}

function getTextSource(source) {
  switch (source) {
    case 'dom':
      return { text: stripHtmlTags(domText ?? ''), label: 'dom', filePath: summary.dom };
    case 'errors':
      return { text: errorsText ?? '', label: 'errors', filePath: summary.errorsLog };
    case 'console':
      return { text: consoleText ?? '', label: 'console', filePath: summary.consoleLog };
    case 'cdp':
      return { text: cdpTraceText ?? '', label: 'cdp', filePath: summary.cdpTrace };
    case 'combined':
    default:
      return { text: combinedLogText, label: 'combined logs', filePath: null };
  }
}

function findFirstLine(source, predicate) {
  const sourceName = source ?? 'combined';
  return allLines.find((entry) => {
    if (sourceName === 'errors' && entry.filePath !== summary.errorsLog) {
      return false;
    }
    if (sourceName === 'console' && entry.filePath !== summary.consoleLog) {
      return false;
    }
    if (sourceName === 'cdp' && entry.filePath !== summary.cdpTrace) {
      return false;
    }
    return predicate(entry.text);
  });
}

function getTimingValue(assertion) {
  const metric = String(assertion.metric ?? '').trim();
  if (metric && Object.hasOwn(timingMetrics, metric)) {
    return {
      value: timingMetrics[metric],
      label: metric,
      evidence: [{ filePath: path.resolve(summaryPath), lineNumber: 1 }],
    };
  }

  const phase = String(assertion.phase ?? '').trim();
  const component = String(assertion.component ?? '').trim();
  const label = String(assertion.label ?? '').trim();
  const labelPattern = assertion.labelPattern ?? assertion.labelRegex;
  const { regex: labelRegex } = labelPattern ? compileRegex(labelPattern, assertion.flags ?? '') : {};
  const matches = completedMetrics.filter((entry) => {
    if (phase && entry.phase !== phase) {
      return false;
    }
    if (component && entry.component !== component) {
      return false;
    }
    if (label && entry.label !== label) {
      return false;
    }
    if (labelRegex) {
      labelRegex.lastIndex = 0;
      if (!labelRegex.test(entry.label)) {
        return false;
      }
    }
    return true;
  });

  if (matches.length === 0) {
    return {
      value: null,
      label: metric || [component, phase, label || labelPattern].filter(Boolean).join('/'),
      evidence: [],
    };
  }

  const aggregate = String(assertion.aggregate ?? 'first').toLowerCase();
  const values = matches.map((entry) => entry.ms);
  const selectedValue = aggregate === 'max'
    ? Math.max(...values)
    : aggregate === 'min'
      ? Math.min(...values)
      : aggregate === 'avg'
        ? values.reduce((sum, value) => sum + value, 0) / values.length
        : matches[0].ms;
  const selectedMatch = aggregate === 'first'
    ? matches[0]
    : matches.find((entry) => entry.ms === selectedValue) ?? matches[0];

  return {
    value: selectedValue,
    label: metric || [component || selectedMatch.component, phase || selectedMatch.phase, label || selectedMatch.label].filter(Boolean).join('/'),
    evidence: [{ filePath: selectedMatch.filePath, lineNumber: selectedMatch.lineNumber }],
    sampleCount: matches.length,
  };
}

function evaluateLogRule(rule, index) {
  const source = rule.source ?? 'combined';
  const sourceData = getTextSource(source);
  const type = rule.type ?? (rule.pattern || rule.regex ? 'regex' : 'contains');
  const ruleId = rule.id ?? `rule-${index + 1}`;
  let ok = false;
  let detail = '';
  let evidence = [];
  let count = null;

  if (type === 'contains' || type === 'not-contains') {
    const needle = String(rule.value ?? rule.contains ?? '');
    const contains = needle.length > 0 && sourceData.text.includes(needle);
    ok = type === 'contains' ? contains : !contains;
    detail = `${type} ${ok ? 'satisfied' : 'failed'} for ${needle}`;
    const line = findFirstLine(source, (text) => text.includes(needle));
    evidence = line ? [{ filePath: line.filePath, lineNumber: line.lineNumber }] : [];
  } else if (type === 'regex' || type === 'not-regex') {
    const { regex, error } = compileRegex(rule.pattern ?? rule.regex, rule.flags ?? '');
    if (error) {
      return {
        id: ruleId,
        status: 'fail',
        detail: `Invalid regex: ${error.message}`,
        evidence: [],
        count: null,
      };
    }
    const matches = countRegexMatches(sourceData.text, regex);
    count = matches;
    ok = type === 'regex' ? matches > 0 : matches === 0;
    detail = `${type} ${ok ? 'satisfied' : 'failed'} for /${regex.source}/${regex.flags}`;
    const lineRegex = new RegExp(regex.source, regex.flags.replaceAll('g', ''));
    const line = findFirstLine(source, (text) => lineRegex.test(text));
    evidence = line ? [{ filePath: line.filePath, lineNumber: line.lineNumber }] : [];
  } else if (type === 'count') {
    const { regex, error } = compileRegex(rule.pattern ?? rule.regex ?? escapeRegExp(rule.value ?? ''), rule.flags ?? 'g');
    if (error) {
      return {
        id: ruleId,
        status: 'fail',
        detail: `Invalid regex: ${error.message}`,
        evidence: [],
        count: null,
      };
    }
    count = countRegexMatches(sourceData.text, regex.global ? regex : new RegExp(regex.source, `${regex.flags}g`));
    const expectation = getNumericExpectation(rule, 'eq', 0);
    ok = compareNumber(count, expectation.operator, expectation.expected);
    detail = `count=${count} (${describeNumericExpectation(expectation.operator, expectation.expected)})`;
    const lineRegex = new RegExp(regex.source, regex.flags.replaceAll('g', ''));
    const line = findFirstLine(source, (text) => lineRegex.test(text));
    evidence = line ? [{ filePath: line.filePath, lineNumber: line.lineNumber }] : [];
  } else {
    detail = `Unsupported log rule type: ${type}`;
  }

  return {
    id: ruleId,
    status: ok ? 'pass' : 'fail',
    detail,
    evidence,
    count,
  };
}

for (const assertion of assertionsDocument?.assertions ?? []) {
  const assertionId = assertion.id ?? assertion.type ?? `assertion-${customAssertions.length + 1}`;

  switch (assertion.type) {
    case 'artifact-exists': {
      const field = assertion.field;
      const targetPath = summary[field] ?? null;
      const exists = await pathExists(targetPath);
      pushCustomAssertion(
        assertion,
        assertionId,
        exists,
        exists ? `Artifact ${field} exists at ${targetPath}.` : `Artifact ${field} is missing.`,
        exists ? [{ filePath: targetPath, lineNumber: 1 }] : [],
      );
      break;
    }
    case 'scenario-success': {
      const ok = scenarioReport?.success === true;
      pushCustomAssertion(
        assertion,
        assertionId,
        ok,
        ok ? 'Scenario completed successfully.' : 'Scenario report is missing or failed.',
        summary.scenarioReport ? [{ filePath: summary.scenarioReport, lineNumber: 1 }] : [],
      );
      break;
    }
    case 'dom-contains':
    case 'dom-not-contains': {
      const needle = String(assertion.value ?? assertion.contains ?? '');
      const contains = typeof domText === 'string' && needle.length > 0 && domText.includes(needle);
      const ok = assertion.type === 'dom-contains' ? contains : !contains;
      pushCustomAssertion(
        assertion,
        assertionId,
        ok,
        ok ? `${assertion.type} satisfied for ${needle}.` : `${assertion.type} failed for ${needle}.`,
        summary.dom ? [{ filePath: summary.dom, lineNumber: 1 }] : [],
      );
      break;
    }
    case 'dom-count':
    case 'selector-count': {
      const selector = String(assertion.selector ?? assertion.value ?? '').trim();
      const actual = getSelectorCount({ selector, html: domText, cdpSummaryDocument: cdpSummary });
      const expectation = getNumericExpectation(assertion, 'gte', 1);
      const ok = compareNumber(actual, expectation.operator, expectation.expected);
      pushCustomAssertion(
        assertion,
        assertionId,
        ok,
        `Selector ${selector} count=${actual} (${describeNumericExpectation(expectation.operator, expectation.expected)}).`,
        summary.dom ? [{ filePath: summary.dom, lineNumber: 1 }] : [],
        { actual, expected: expectation.expected, operator: expectation.operator, selector },
      );
      break;
    }
    case 'dom-visible':
    case 'selector-visible': {
      const selector = String(assertion.selector ?? assertion.value ?? '').trim();
      const minVisible = toFiniteNumber(assertion.min ?? assertion.count) ?? 1;
      let visibleCount = 0;
      let totalCount = 0;

      if (cdpSummaryMatchesSelector(cdpSummary, selector)) {
        totalCount = toFiniteNumber(cdpSummary.count) ?? cdpSummary.matches.length;
        visibleCount = cdpSummary.matches.filter(isCdpMatchVisible).length;
      } else {
        const matches = findDomElements(domText, selector);
        totalCount = matches.length;
        visibleCount = matches.filter(isElementVisible).length;
      }

      const ok = visibleCount >= minVisible;
      pushCustomAssertion(
        assertion,
        assertionId,
        ok,
        `Selector ${selector} visible=${visibleCount}/${totalCount} (min ${minVisible}).`,
        summary.dom ? [{ filePath: summary.dom, lineNumber: 1 }] : [],
        { selector, actual: visibleCount, total: totalCount, expected: minVisible, operator: 'gte' },
      );
      break;
    }
    case 'dom-text-regex':
    case 'text-regex':
    case 'log-regex': {
      const source = assertion.type === 'dom-text-regex'
        ? 'dom'
        : assertion.type === 'log-regex'
          ? (assertion.source ?? 'combined')
          : (assertion.source ?? 'dom');
      const selector = String(assertion.selector ?? '').trim();
      const sourceData = getTextSource(source);
      const text = selector && source === 'dom'
        ? findDomElements(domText, selector).map((entry) => entry.textContent).join('\n')
        : sourceData.text;
      const { regex, error } = compileRegex(assertion.pattern ?? assertion.regex ?? assertion.value, assertion.flags ?? '');
      const ok = error ? false : regex.test(text);
      pushCustomAssertion(
        assertion,
        assertionId,
        ok,
        error
          ? `Invalid regex: ${error.message}`
          : `${sourceData.label}${selector ? ` selector ${selector}` : ''} ${ok ? 'matches' : 'does not match'} /${regex.source}/${regex.flags}.`,
        sourceData.filePath ? [{ filePath: sourceData.filePath, lineNumber: 1 }] : [],
        { source, selector: selector || null },
      );
      break;
    }
    case 'dom-attribute':
    case 'attribute': {
      const selector = String(assertion.selector ?? '').trim();
      const attribute = String(assertion.attribute ?? assertion.name ?? '').trim();
      const matches = findDomElements(domText, selector);
      const values = matches
        .map((entry) => readAttribute(entry.attrsText, attribute))
        .filter((entry) => entry.exists)
        .map((entry) => entry.value);
      const mode = assertion.mode === 'all' ? 'all' : 'any';
      const expectation = assertion.exists === true && assertion.value === undefined && assertion.expected === undefined
        ? { ok: values.length > 0, detail: `attribute ${attribute} exists` }
        : values.length === 0
          ? { ok: false, detail: `attribute ${attribute} is missing` }
          : null;
      const evaluatedValues = expectation
        ? []
        : values.map((value) => evaluateStringExpectation(value, assertion));
      const ok = expectation
        ? expectation.ok
        : mode === 'all'
          ? evaluatedValues.length > 0 && evaluatedValues.every((entry) => entry.ok)
          : evaluatedValues.some((entry) => entry.ok);
      pushCustomAssertion(
        assertion,
        assertionId,
        ok,
        expectation?.detail
          ?? `Selector ${selector} attribute ${attribute} ${ok ? 'matched' : 'did not match'} (${mode}, values: ${values.join(', ') || 'none'}).`,
        summary.dom ? [{ filePath: summary.dom, lineNumber: 1 }] : [],
        { selector, attribute, actual: values, mode },
      );
      break;
    }
    case 'computed-style':
    case 'dom-computed-style': {
      const selector = String(assertion.selector ?? '').trim();
      const property = String(assertion.property ?? '').trim();
      const values = getStyleValues({
        selector,
        property,
        html: domText,
        cdpSummaryDocument: cdpSummary,
      });
      const mode = assertion.mode === 'all' ? 'all' : 'any';
      const evaluatedValues = values.map((entry) => evaluateStringExpectation(entry.value, assertion));
      const ok = mode === 'all'
        ? evaluatedValues.length > 0 && evaluatedValues.every((entry) => entry.ok)
        : evaluatedValues.some((entry) => entry.ok);
      pushCustomAssertion(
        assertion,
        assertionId,
        ok,
        `Selector ${selector} computed ${property} ${ok ? 'matched' : 'did not match'} (${mode}, values: ${values.map((entry) => entry.value).join(', ') || 'none'}).`,
        summary.cdpSummary ? [{ filePath: summary.cdpSummary, lineNumber: 1 }] : (summary.dom ? [{ filePath: summary.dom, lineNumber: 1 }] : []),
        { selector, property, actual: values, mode },
      );
      break;
    }
    case 'log-contains':
    case 'log-not-contains': {
      const needle = String(assertion.value ?? '');
      const source = assertion.source ?? 'combined';
      const sourceData = getTextSource(source);
      const line = findFirstLine(source, (text) => text.includes(needle));
      const contains = needle.length > 0 && sourceData.text.includes(needle);
      const ok = assertion.type === 'log-contains' ? contains : !contains;
      pushCustomAssertion(
        assertion,
        assertionId,
        ok,
        ok
          ? `${assertion.type} satisfied for ${needle}.`
          : `${assertion.type} failed for ${needle}.`,
        line ? [{ filePath: line.filePath, lineNumber: line.lineNumber }] : [],
      );
      break;
    }
    case 'log-group':
    case 'log-rules': {
      const rules = Array.isArray(assertion.rules) ? assertion.rules : [];
      const ruleResults = rules.map((rule, index) => evaluateLogRule(rule, index));
      const ok = ruleResults.length > 0 && ruleResults.every((entry) => entry.status === 'pass');
      pushCustomAssertion(
        assertion,
        assertionId,
        ok,
        ok
          ? `All ${ruleResults.length} grouped log rule(s) passed.`
          : `${ruleResults.filter((entry) => entry.status !== 'pass').length}/${ruleResults.length} grouped log rule(s) failed.`,
        ruleResults.flatMap((entry) => entry.evidence).slice(0, 8),
        { rules: ruleResults },
      );
      break;
    }
    case 'timing-max':
    case 'timing-min':
    case 'timing-budget':
    case 'performance-budget': {
      const timing = getTimingValue(assertion);
      const allowMissing = assertion.allowMissing === true;
      const expectation = assertion.type === 'timing-min'
        ? getNumericExpectation({ ...assertion, min: assertion.value ?? assertion.minMs ?? assertion.min }, 'gte', 0)
        : assertion.type === 'timing-max'
          ? getNumericExpectation({ ...assertion, max: assertion.value ?? assertion.maxMs ?? assertion.max }, 'lte', 0)
          : getNumericExpectation(assertion, 'lte', 0);
      const ok = Number.isFinite(timing.value)
        ? compareNumber(timing.value, expectation.operator, expectation.expected)
        : allowMissing;
      pushCustomAssertion(
        assertion,
        assertionId,
        ok,
        Number.isFinite(timing.value)
          ? `${timing.label}=${timing.value}ms (${describeNumericExpectation(expectation.operator, expectation.expected)}ms).`
          : `${timing.label || assertion.metric || 'timing metric'} is missing.`,
        timing.evidence.length > 0 ? timing.evidence : [{ filePath: path.resolve(summaryPath), lineNumber: 1 }],
        {
          actual: timing.value,
          expected: expectation.expected,
          operator: expectation.operator,
          metric: assertion.metric ?? null,
          sampleCount: timing.sampleCount ?? null,
        },
      );
      break;
    }
    case 'signature-present':
    case 'signature-absent': {
      const targetId = String(assertion.value ?? '');
      const exists = matchedSignatures.some((entry) => entry.id === targetId);
      const ok = assertion.type === 'signature-present' ? exists : !exists;
      pushCustomAssertion(
        assertion,
        assertionId,
        ok,
        ok
          ? `${assertion.type} satisfied for ${targetId}.`
          : `${assertion.type} failed for ${targetId}.`,
        [{ filePath: path.resolve(summaryPath), lineNumber: 1 }],
      );
      break;
    }
    default:
      pushCustomAssertion(
        assertion,
        assertionId,
        false,
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

const allAssertionResults = [...assertions, ...customAssertions];
const assertionSummary = allAssertionResults.reduce(
  (summaryAcc, assertion) => {
    const statusKey = assertion.status ?? 'unknown';
    summaryAcc.total += 1;
    summaryAcc.byStatus[statusKey] = (summaryAcc.byStatus[statusKey] ?? 0) + 1;
    if (statusKey === 'fail') {
      summaryAcc.blockingFailures.push(assertion.id);
    } else if (isWarningStatus(statusKey)) {
      summaryAcc.warnings.push(assertion.id);
    } else if (statusKey === 'expected') {
      summaryAcc.expected.push(assertion.id);
    } else if (statusKey === 'flaky') {
      summaryAcc.flaky.push(assertion.id);
    }
    if (!isPassingOrSkipped(statusKey)) {
      summaryAcc.nonPassing.push(assertion.id);
    }
    return summaryAcc;
  },
  {
    total: 0,
    byStatus: {},
    blockingFailures: [],
    warnings: [],
    expected: [],
    flaky: [],
    nonPassing: [],
  },
);

let status = 'pass';
if (
  matchedSignatures.some((entry) => entry.severity === 'error')
  || assertionSummary.blockingFailures.length > 0
) {
  status = 'fail';
} else if (matchedSignatures.some((entry) => entry.severity === 'warning') || assertionSummary.warnings.length > 0) {
  status = 'warning';
}

const matchedSignatureIds = new Set(matchedSignatures.map((entry) => entry.id));
const failedAssertionIds = new Set([
  ...assertions.filter((entry) => entry.status === 'fail').map((entry) => entry.id),
  ...customAssertions.filter((entry) => entry.status === 'fail').map((entry) => entry.id),
]);

function matchesPlaybook(playbook) {
  const match = playbook?.match ?? {};
  const signatureAny = match.signatureAny ?? [];
  if (signatureAny.length > 0 && !signatureAny.some((id) => matchedSignatureIds.has(id))) {
    return false;
  }

  const signatureAll = match.signatureAll ?? [];
  if (signatureAll.length > 0 && !signatureAll.every((id) => matchedSignatureIds.has(id))) {
    return false;
  }

  const assertionFailedAny = match.assertionFailedAny ?? [];
  if (assertionFailedAny.length > 0 && !assertionFailedAny.some((id) => failedAssertionIds.has(id))) {
    return false;
  }

  const assertionFailedAll = match.assertionFailedAll ?? [];
  if (assertionFailedAll.length > 0 && !assertionFailedAll.every((id) => failedAssertionIds.has(id))) {
    return false;
  }

  if (typeof match.useCdp === 'boolean' && Boolean(summary.useCdp) !== match.useCdp) {
    return false;
  }

  return true;
}

const playbooks = (playbooksDocument.playbooks ?? [])
  .filter((playbook) => matchesPlaybook(playbook))
  .map((playbook) => ({
    id: playbook.id,
    title: playbook.title,
    summary: playbook.summary,
    files: playbook.files ?? [],
    commands: (playbook.commands ?? []).map((command, index) => resolveTemplateCommand(
      typeof command === 'string'
        ? {
            id: `${playbook.id}-command-${index + 1}`,
            label: `Command ${index + 1}`,
            rendered: command,
          }
        : {
            id: command.id ?? `${playbook.id}-command-${index + 1}`,
            ...command,
          },
      {
        variables: runtimeContext,
        platform,
      },
    )),
    actions: playbook.actions ?? [],
    relatedSignatures: (playbook.match?.signatureAny ?? []).filter((id) => matchedSignatureIds.has(id)),
  }));

const highestSeveritySignature = [...matchedSignatures].sort(
  (left, right) => getSeverityRank(right.severity) - getSeverityRank(left.severity),
)[0];

const headline = highestSeveritySignature
  ? highestSeveritySignature.headline
  : customAssertions.find((entry) => entry.status === 'fail')?.detail
    ?? customAssertions.find((entry) => isWarningStatus(entry.status))?.detail
    ?? (assertions.some((entry) => entry.status === 'fail')
      ? 'Automation completed, but one or more required artifacts/assertions failed.'
      : 'Automation completed and the captured artifacts look healthy.');

const recommendations = [...new Set([
  ...matchedSignatures.flatMap((entry) => entry.nextActions ?? []),
  ...playbooks.flatMap((entry) => entry.actions ?? []),
])];

const diagnosis = {
  generatedAt: nowIso(),
  status,
  headline,
  pluginId: summary.pluginId,
  vaultName: summary.vaultName,
  useCdp: summary.useCdp,
  domSelector: domSelector || null,
  runtime: {
    platform,
    repoDir: repoDir || null,
    outputDir,
    toolRoot,
    summaryPath: path.resolve(summaryPath),
    testVaultPluginDir: testVaultPluginDir || null,
    vaultRoot: runtimeContext.vaultRoot || null,
    obsidianCommand: runtimeContext.obsidianCommand || null,
  },
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
  assertionSummary,
  timings: timingMetrics,
  topSlowSteps,
  signatures: matchedSignatures,
  playbooks,
  recommendations,
  assertionsPath: assertionsPath || null,
  playbooksPath,
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
