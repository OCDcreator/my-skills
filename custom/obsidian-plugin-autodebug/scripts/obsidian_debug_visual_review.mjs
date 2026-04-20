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

const DEFAULT_CHECKLIST = [
  {
    id: 'target-surface-visible',
    label: 'Target surface is visible',
    prompt: 'The expected plugin view, settings tab, ribbon result, modal, or command output is visible in the screenshot.',
    evidence: ['screenshot', 'scenarioReport', 'dom'],
  },
  {
    id: 'no-blank-or-crashed-shell',
    label: 'No blank/crashed shell',
    prompt: 'The active Obsidian pane is not blank, stuck on a loading skeleton, or replaced by an Electron crash/error page.',
    evidence: ['screenshot', 'dom', 'consoleLog', 'errorsLog'],
  },
  {
    id: 'primary-action-reachable',
    label: 'Primary action is reachable',
    prompt: 'The main button/input/list/card needed for this smoke test is visible and not clipped, disabled, or covered.',
    evidence: ['screenshot', 'dom'],
  },
  {
    id: 'error-copy-visible',
    label: 'Errors are visible and actionable',
    prompt: 'Any visible error or warning has actionable copy and does not leak secrets, tokens, or local-only debug spam.',
    evidence: ['screenshot', 'dom', 'consoleLog', 'errorsLog'],
  },
  {
    id: 'layout-regression-check',
    label: 'Layout regression check',
    prompt: 'Spacing, overflow, clipped text, theme contrast, and responsive sizing look acceptable for the captured viewport.',
    evidence: ['screenshot', 'comparisonReport'],
  },
];

function asObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function stringValue(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function normalizePath(value, basePath = '') {
  const text = stringValue(value);
  if (!text) {
    return null;
  }
  if (path.isAbsolute(text)) {
    return path.resolve(text);
  }
  if (basePath) {
    return path.resolve(path.dirname(path.resolve(basePath)), text);
  }
  return path.resolve(text);
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

async function readTextPreview(filePath, { maxChars = 1800 } = {}) {
  if (!filePath) {
    return '';
  }
  try {
    return (await fs.readFile(filePath, 'utf8')).replace(/^\uFEFF/, '').slice(0, maxChars);
  } catch {
    return '';
  }
}

async function exists(filePath) {
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

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function relativeHref(fromFile, targetFile) {
  if (!targetFile) {
    return '';
  }
  const relative = path.relative(path.dirname(path.resolve(fromFile)), path.resolve(targetFile));
  return relative.replaceAll(path.sep, '/');
}

function collectScenarioFindings(scenarioReport) {
  const report = asObject(scenarioReport);
  const findings = [];
  if (Object.keys(report).length === 0) {
    return findings;
  }

  findings.push({
    id: 'scenario-status',
    status: report.success === false ? 'fail' : (report.success === true ? 'pass' : 'info'),
    detail: report.scenarioName
      ? `Scenario ${report.scenarioName} ${report.success === false ? 'failed' : report.success === true ? 'completed' : 'was recorded'}.`
      : 'Scenario report was recorded.',
  });

  const strategy = report.selectedStrategy ?? report.selectedSurfaceStrategy;
  if (strategy) {
    findings.push({
      id: 'surface-open-strategy',
      status: 'info',
      detail: `Surface open strategy: ${JSON.stringify(strategy)}`,
    });
  }

  for (const warning of Array.isArray(report.warnings) ? report.warnings : []) {
    findings.push({
      id: 'scenario-warning',
      status: 'warn',
      detail: String(warning),
    });
  }

  return findings;
}

function collectDiagnosisFindings(diagnosis) {
  const findings = [];
  const assertions = Array.isArray(diagnosis?.assertions) ? diagnosis.assertions : [];
  for (const assertion of assertions.filter((entry) => ['fail', 'warn', 'warning'].includes(stringValue(entry.status).toLowerCase())).slice(0, 12)) {
    findings.push({
      id: stringValue(assertion.id) || 'diagnosis-assertion',
      status: stringValue(assertion.status) || 'warn',
      detail: stringValue(assertion.detail) || 'Diagnosis assertion needs review.',
    });
  }

  for (const recommendation of Array.isArray(diagnosis?.recommendations) ? diagnosis.recommendations.slice(0, 8) : []) {
    findings.push({
      id: 'diagnosis-recommendation',
      status: 'info',
      detail: String(recommendation),
    });
  }

  return findings;
}

function collectComparisonFindings(comparison) {
  const screenshotDiff = asObject(comparison?.screenshotDiff);
  if (Object.keys(screenshotDiff).length === 0) {
    return [];
  }

  return [
    {
      id: 'screenshot-diff',
      status: screenshotDiff.status === 'different' ? 'warn' : 'info',
      detail: screenshotDiff.status
        ? `Screenshot diff status: ${screenshotDiff.status}${screenshotDiff.changedRatio ? ` (${screenshotDiff.changedRatio})` : ''}.`
        : 'Screenshot diff was recorded.',
    },
  ];
}

function buildArtifactEntry({ id, label, path: artifactPath, required = false, preview = '' }) {
  return {
    id,
    label,
    path: artifactPath ?? null,
    exists: false,
    required,
    preview,
  };
}

async function resolveArtifacts({
  summary,
  summaryPath,
  diagnosis,
  diagnosisPath,
  scenarioReportPath,
  screenshotPath,
  domPath,
  comparisonPath,
}) {
  const artifacts = asObject(diagnosis?.artifacts);
  const summaryBase = summaryPath || diagnosisPath;
  const diagnosisBase = diagnosisPath || summaryPath;
  const resolved = {
    screenshot: normalizePath(screenshotPath, diagnosisBase)
      ?? normalizePath(artifacts.screenshot, diagnosisBase)
      ?? normalizePath(summary?.screenshot, summaryBase),
    dom: normalizePath(domPath, diagnosisBase)
      ?? normalizePath(artifacts.dom, diagnosisBase)
      ?? normalizePath(summary?.dom, summaryBase),
    scenarioReport: normalizePath(scenarioReportPath, diagnosisBase)
      ?? normalizePath(artifacts.scenarioReport, diagnosisBase)
      ?? normalizePath(summary?.scenarioReport, summaryBase),
    comparisonReport: normalizePath(comparisonPath, diagnosisBase)
      ?? normalizePath(artifacts.comparisonReport, diagnosisBase)
      ?? normalizePath(summary?.comparisonReport, summaryBase),
    consoleLog: normalizePath(artifacts.consoleLog, diagnosisBase)
      ?? normalizePath(summary?.consoleLog, summaryBase),
    errorsLog: normalizePath(artifacts.errorsLog, diagnosisBase)
      ?? normalizePath(summary?.errorsLog, summaryBase),
  };

  const entries = [
    buildArtifactEntry({ id: 'screenshot', label: 'Screenshot', path: resolved.screenshot, required: true }),
    buildArtifactEntry({ id: 'dom', label: 'DOM snapshot', path: resolved.dom }),
    buildArtifactEntry({ id: 'scenarioReport', label: 'Scenario report', path: resolved.scenarioReport }),
    buildArtifactEntry({ id: 'comparisonReport', label: 'Comparison report', path: resolved.comparisonReport }),
    buildArtifactEntry({ id: 'consoleLog', label: 'Console log', path: resolved.consoleLog }),
    buildArtifactEntry({ id: 'errorsLog', label: 'Errors log', path: resolved.errorsLog }),
  ];

  return Object.fromEntries(await Promise.all(entries.map(async (entry) => [
    entry.id,
    {
      ...entry,
      exists: await exists(entry.path),
      preview: ['dom', 'consoleLog', 'errorsLog'].includes(entry.id) ? await readTextPreview(entry.path) : '',
    },
  ])));
}

function buildChecklist({ checklist = DEFAULT_CHECKLIST, artifacts }) {
  return checklist.map((entry) => {
    const evidence = Array.isArray(entry.evidence) ? entry.evidence : [];
    const availableEvidence = evidence.filter((id) => artifacts[id]?.exists);
    return {
      ...entry,
      status: 'needs-human-review',
      availableEvidence,
      missingEvidence: evidence.filter((id) => !artifacts[id]?.exists),
    };
  });
}

function renderHtml(pack, htmlOutputPath) {
  const screenshot = pack.artifacts.screenshot;
  const screenshotHref = screenshot?.exists ? relativeHref(htmlOutputPath, screenshot.path) : '';
  const artifactRows = Object.values(pack.artifacts).map((entry) => `
    <tr>
      <td><code>${escapeHtml(entry.id)}</code></td>
      <td>${escapeHtml(entry.label)}</td>
      <td><span class="badge ${entry.exists ? 'pass' : entry.required ? 'fail' : 'info'}">${entry.exists ? 'exists' : 'missing'}</span></td>
      <td>${entry.path ? `<code>${escapeHtml(entry.path)}</code>` : ''}</td>
    </tr>
  `).join('');
  const checklistRows = pack.checklist.map((entry) => `
    <tr>
      <td><code>${escapeHtml(entry.id)}</code></td>
      <td>${escapeHtml(entry.label)}</td>
      <td>${escapeHtml(entry.prompt)}</td>
      <td>${entry.availableEvidence.map((id) => `<span class="badge pass">${escapeHtml(id)}</span>`).join(' ') || '<span class="badge fail">no evidence</span>'}</td>
    </tr>
  `).join('');
  const findingRows = pack.findings.map((entry) => `
    <tr>
      <td><code>${escapeHtml(entry.id)}</code></td>
      <td><span class="badge ${entry.status === 'pass' ? 'pass' : entry.status === 'fail' ? 'fail' : entry.status === 'warn' || entry.status === 'warning' ? 'warn' : 'info'}">${escapeHtml(entry.status)}</span></td>
      <td>${escapeHtml(entry.detail)}</td>
    </tr>
  `).join('') || '<tr><td colspan="3">No findings recorded.</td></tr>';

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Obsidian Visual Review Pack</title>
  <style>
    body { font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1f2937; background: #f8fafc; }
    h1, h2 { color: #111827; }
    .notice { border-left: 4px solid #f59e0b; background: #fffbeb; padding: 12px 16px; margin: 16px 0; }
    .panel { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; margin: 18px 0; box-shadow: 0 1px 2px rgba(15, 23, 42, .06); }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: left; vertical-align: top; }
    code { background: #f1f5f9; padding: 1px 4px; border-radius: 4px; }
    .badge { display: inline-block; border-radius: 999px; padding: 2px 8px; font-size: 12px; background: #e5e7eb; color: #374151; }
    .pass { background: #dcfce7; color: #166534; }
    .warn { background: #fef3c7; color: #92400e; }
    .fail { background: #fee2e2; color: #991b1b; }
    .info { background: #dbeafe; color: #1e40af; }
    img { max-width: 100%; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; }
    pre { white-space: pre-wrap; max-height: 360px; overflow: auto; background: #0f172a; color: #e2e8f0; border-radius: 8px; padding: 12px; }
  </style>
</head>
<body>
  <h1>Obsidian Visual Review Pack</h1>
  <p>Generated at <code>${escapeHtml(pack.metadata.generatedAt)}</code> for plugin <code>${escapeHtml(pack.metadata.pluginId ?? 'unknown')}</code>.</p>
  <div class="notice"><strong>Boundary:</strong> ${escapeHtml(pack.visualReview.boundary)}</div>
  <section class="panel">
    <h2>Screenshot</h2>
    ${screenshotHref ? `<p><a href="${escapeHtml(screenshotHref)}">Open screenshot artifact</a></p><img src="${escapeHtml(screenshotHref)}" alt="Obsidian screenshot">` : '<p>No screenshot artifact was found. Re-run capture before asking for human review.</p>'}
  </section>
  <section class="panel">
    <h2>Human Checklist</h2>
    <table><thead><tr><th>ID</th><th>Check</th><th>What to inspect</th><th>Evidence</th></tr></thead><tbody>${checklistRows}</tbody></table>
  </section>
  <section class="panel">
    <h2>Findings</h2>
    <table><thead><tr><th>ID</th><th>Status</th><th>Detail</th></tr></thead><tbody>${findingRows}</tbody></table>
  </section>
  <section class="panel">
    <h2>Artifacts</h2>
    <table><thead><tr><th>ID</th><th>Label</th><th>State</th><th>Path</th></tr></thead><tbody>${artifactRows}</tbody></table>
  </section>
  ${pack.artifacts.dom?.preview ? `<section class="panel"><h2>DOM Preview</h2><pre>${escapeHtml(pack.artifacts.dom.preview)}</pre></section>` : ''}
</body>
</html>
`;
}

export async function generateVisualReviewPack({
  summaryPath = '',
  diagnosisPath = '',
  scenarioReportPath = '',
  screenshotPath = '',
  domPath = '',
  comparisonPath = '',
  outputPath = '',
  htmlOutputPath = '',
  summaryDocument = null,
  diagnosisDocument = null,
  scenarioReportDocument = null,
  comparisonDocument = null,
} = {}) {
  const resolvedSummaryPath = summaryPath ? path.resolve(summaryPath) : '';
  const resolvedDiagnosisPath = diagnosisPath ? path.resolve(diagnosisPath) : '';
  const summary = summaryDocument ?? await readJsonOrNull(resolvedSummaryPath);
  const diagnosis = diagnosisDocument ?? await readJsonOrNull(resolvedDiagnosisPath);
  const artifacts = await resolveArtifacts({
    summary: summary ?? {},
    summaryPath: resolvedSummaryPath,
    diagnosis: diagnosis ?? {},
    diagnosisPath: resolvedDiagnosisPath,
    scenarioReportPath,
    screenshotPath,
    domPath,
    comparisonPath,
  });
  const resolvedScenarioReportPath = artifacts.scenarioReport.path;
  const resolvedComparisonPath = artifacts.comparisonReport.path;
  const scenarioReport = scenarioReportDocument ?? await readJsonOrNull(resolvedScenarioReportPath);
  const comparison = comparisonDocument ?? await readJsonOrNull(resolvedComparisonPath);
  const defaultOutputBase = resolvedDiagnosisPath || resolvedSummaryPath || process.cwd();
  const resolvedOutputPath = path.resolve(outputPath || path.join(path.dirname(defaultOutputBase), 'visual-review.json'));
  const resolvedHtmlOutputPath = htmlOutputPath
    ? path.resolve(htmlOutputPath)
    : path.join(path.dirname(resolvedOutputPath), 'visual-review.html');
  const metadata = {
    generatedAt: nowIso(),
    pluginId: stringValue(diagnosis?.pluginId) || stringValue(summary?.pluginId) || null,
    vaultName: stringValue(diagnosis?.vaultName) || stringValue(summary?.vaultName) || null,
    source: {
      summaryPath: resolvedSummaryPath || null,
      diagnosisPath: resolvedDiagnosisPath || null,
    },
  };
  const pack = {
    metadata,
    visualReview: {
      status: artifacts.screenshot.exists ? 'needs-human-review' : 'blocked-missing-screenshot',
      humanReviewRequired: true,
      canReplaceManualGuiValidation: false,
      boundary: 'Screenshots, DOM, and scenario output create a human-review artifact, but they do not fully replace reliable manual Obsidian GUI validation.',
      usefulFor: [
        'Checking blank panes, clipping, obvious layout regressions, visible errors, theme contrast, and command/view reachability.',
        'Handing another agent or human a compact review target with exact artifact paths.',
      ],
      notEnoughFor: [
        'Proving hover/focus/drag behavior, keyboard accessibility, timing-sensitive animation, or full manual exploratory testing.',
        'Guaranteeing official review acceptance.',
      ],
    },
    artifacts,
    checklist: buildChecklist({ artifacts }),
    findings: [
      ...collectScenarioFindings(scenarioReport),
      ...collectDiagnosisFindings(diagnosis ?? {}),
      ...collectComparisonFindings(comparison ?? {}),
    ],
    nextSteps: artifacts.screenshot.exists
      ? [
          'Open visual-review.html and inspect each checklist row against the screenshot.',
          'Use DOM/log artifacts for deterministic follow-up; do not treat screenshot review as the only assertion.',
          'If a visual diff exists, inspect the changed region before accepting the run.',
        ]
      : [
          'Re-run the debug cycle with screenshot capture enabled.',
          'If CLI screenshot is unavailable, use CDP or Playwright screenshot capture and pass --screenshot explicitly.',
        ],
  };

  await ensureParentDirectory(resolvedOutputPath);
  await fs.writeFile(resolvedOutputPath, `${JSON.stringify(pack, null, 2)}\n`, 'utf8');
  await ensureParentDirectory(resolvedHtmlOutputPath);
  await fs.writeFile(resolvedHtmlOutputPath, renderHtml(pack, resolvedHtmlOutputPath), 'utf8');
  return {
    ...pack,
    outputPath: resolvedOutputPath,
    htmlOutputPath: resolvedHtmlOutputPath,
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
Usage: node scripts/obsidian_debug_visual_review.mjs [options]

Options:
  --summary <path>          Optional summary.json from a debug cycle.
  --diagnosis <path>        Optional diagnosis.json from obsidian_debug_analyze.mjs.
  --scenario-report <path>  Optional scenario-report.json override.
  --screenshot <path>       Optional screenshot path override.
  --dom <path>              Optional DOM snapshot path override.
  --comparison <path>       Optional comparison JSON.
  --output <path>           Output visual-review.json path.
  --html-output <path>      Output visual-review.html path.
`);
  }

  const result = await generateVisualReviewPack({
    summaryPath: getStringOption(options, 'summary', '').trim(),
    diagnosisPath: getStringOption(options, 'diagnosis', '').trim(),
    scenarioReportPath: getStringOption(options, 'scenario-report', '').trim(),
    screenshotPath: getStringOption(options, 'screenshot', '').trim(),
    domPath: getStringOption(options, 'dom', '').trim(),
    comparisonPath: getStringOption(options, 'comparison', '').trim(),
    outputPath: getStringOption(options, 'output', '').trim(),
    htmlOutputPath: getStringOption(options, 'html-output', '').trim(),
  });

  console.log(JSON.stringify({
    status: result.visualReview.status,
    outputPath: result.outputPath,
    htmlOutputPath: result.htmlOutputPath,
    checklistCount: result.checklist.length,
  }, null, 2));
}
