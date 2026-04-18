import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import {
  ensureParentDirectory,
  getStringOption,
  parseArgs,
} from './obsidian_cdp_common.mjs';
import { resolveArtifactPaths } from './obsidian_debug_compare_core.mjs';

const options = parseArgs(process.argv.slice(2));
const diagnosisPath = getStringOption(options, 'diagnosis', '').trim();
if (!diagnosisPath) {
  throw new Error('--diagnosis is required');
}

const comparisonPath = getStringOption(options, 'comparison', '').trim();
const profilePath = getStringOption(options, 'profile', '').trim();
const outputPath = path.resolve(
  getStringOption(options, 'output', path.join(path.dirname(path.resolve(diagnosisPath)), 'report.html')),
);
const reportDir = path.dirname(outputPath);

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

async function readTextOrNull(filePath) {
  if (!filePath) {
    return null;
  }
  try {
    return (await fs.readFile(filePath, 'utf8')).replace(/^\uFEFF/, '');
  } catch {
    return null;
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

function renderList(items, mapper) {
  if (!items || items.length === 0) {
    return '<li>None</li>';
  }
  return items.map(mapper).join('');
}

function normalizeStatusClass(status) {
  switch (status) {
    case 'warning':
      return 'warn';
    default:
      return String(status ?? 'info');
  }
}

function renderTableRows(items, mapper, colspan = 1) {
  if (!items || items.length === 0) {
    return `<tr><td colspan="${colspan}">None</td></tr>`;
  }
  return items.map(mapper).join('');
}

function renderAssertionRows(entries) {
  return renderTableRows(entries, (entry) => `
    <tr>
      <td><code>${escapeHtml(entry.id)}</code></td>
      <td><span class="badge ${escapeHtml(normalizeStatusClass(entry.status))}">${escapeHtml(entry.status)}</span></td>
      <td>${escapeHtml(entry.severity ?? '')}</td>
      <td>${escapeHtml(entry.detail)}</td>
    </tr>
    ${entry.rules?.length ? `<tr><td colspan="4"><details><summary>Grouped log rules</summary><ul>${renderList(entry.rules, (rule) => `<li><code>${escapeHtml(rule.id)}</code> — ${escapeHtml(rule.status)} — ${escapeHtml(rule.detail)}</li>`)}</ul></details></td></tr>` : ''}
  `, 4);
}

function renderPlaybooks(playbooks) {
  if (!playbooks || playbooks.length === 0) {
    return '<p>None</p>';
  }

  return playbooks.map((playbook) => `
    <div class="artifact-card">
      <strong>${escapeHtml(playbook.title ?? playbook.id)}</strong>
      <p>${escapeHtml(playbook.summary ?? '')}</p>
      <p><strong>ID:</strong> <code>${escapeHtml(playbook.id)}</code></p>
      <p><strong>Files:</strong> ${playbook.files?.length ? playbook.files.map((item) => `<code>${escapeHtml(item)}</code>`).join(' ') : 'None'}</p>
      <p><strong>Commands:</strong> ${playbook.commands?.length ? playbook.commands.map((item) => `<code>${escapeHtml(item)}</code>`).join(' ') : 'None'}</p>
      <ul>${renderList(playbook.actions ?? [], (entry) => `<li>${escapeHtml(entry)}</li>`)}</ul>
    </div>
  `).join('');
}

function pathHref(targetPath) {
  if (!targetPath) {
    return '';
  }
  const resolved = path.resolve(targetPath);
  const reportRoot = path.parse(reportDir).root.toLowerCase();
  const targetRoot = path.parse(resolved).root.toLowerCase();
  if (reportRoot === targetRoot) {
    const relative = path.relative(reportDir, resolved).replaceAll('\\', '/');
    return escapeHtml(encodeURI(relative || path.basename(resolved)));
  }
  return escapeHtml(pathToFileURL(resolved).href);
}

function renderArtifactLink(targetPath, fallback = 'Missing') {
  if (!targetPath) {
    return fallback;
  }
  return `<a href="${pathHref(targetPath)}"><code>${escapeHtml(path.basename(targetPath))}</code></a>`;
}

function renderMetricTable(metrics) {
  const entries = Object.entries(metrics ?? {});
  if (entries.length === 0) {
    return '<p>None</p>';
  }
  return `
    <table>
      <tr><th>Metric</th><th>Value</th></tr>
      ${entries.map(([key, value]) => `<tr><td>${escapeHtml(key)}</td><td>${escapeHtml(value)}</td></tr>`).join('')}
    </table>
  `;
}

function trimPreview(text, maxLines = 30, maxChars = 2400) {
  if (!text) {
    return null;
  }
  const lines = text.split(/\r?\n/);
  const clipped = lines.slice(0, maxLines).join('\n');
  if (clipped.length <= maxChars) {
    return clipped;
  }
  return `${clipped.slice(0, maxChars)}\n…`;
}

function renderPreviewCard({ title, label, path: artifactPath, preview, kind = 'text' }) {
  if (!artifactPath) {
    return `
      <div class="artifact-card">
        <h3>${escapeHtml(title)}</h3>
        <p class="muted">Missing</p>
      </div>
    `;
  }

  if (kind === 'image') {
    return `
      <div class="artifact-card">
        <h3>${escapeHtml(title)}</h3>
        <p>${renderArtifactLink(artifactPath)}</p>
        <img src="${pathHref(artifactPath)}" alt="${escapeHtml(label)}">
      </div>
    `;
  }

  return `
    <div class="artifact-card">
      <h3>${escapeHtml(title)}</h3>
      <p>${renderArtifactLink(artifactPath)}</p>
      ${preview ? `<pre>${escapeHtml(preview)}</pre>` : '<p class="muted">Preview unavailable</p>'}
    </div>
  `;
}

function renderArtifactRows(entries) {
  return renderTableRows(entries, (entry) => `
    <tr>
      <td>${escapeHtml(entry.scope)}</td>
      <td>${escapeHtml(entry.label)}</td>
      <td>${entry.path ? renderArtifactLink(entry.path) : 'Missing'}</td>
    </tr>
  `, 3);
}

function renderStatusSummary(label, value, cssClass = '') {
  return `<span class="badge ${escapeHtml(cssClass || normalizeStatusClass(value))}">${escapeHtml(label)}: ${escapeHtml(value ?? 'n/a')}</span>`;
}

const diagnosis = await readJsonOrNull(diagnosisPath);
if (!diagnosis) {
  throw new Error(`Unable to read diagnosis JSON: ${diagnosisPath}`);
}

const comparison = await readJsonOrNull(comparisonPath);
const profile = await readJsonOrNull(profilePath);
const diagnosisArtifacts = resolveArtifactPaths(diagnosis, path.resolve(diagnosisPath));
const comparisonBaselineArtifacts = comparison?.baseline?.artifacts ?? {};
const comparisonCandidateArtifacts = comparison?.candidate?.artifacts ?? {};
const screenshotDiffPath = comparison?.screenshotDiff?.diffPath ?? null;

const domPreview = trimPreview(await readTextOrNull(diagnosisArtifacts.dom));
const consolePreview = trimPreview(await readTextOrNull(diagnosisArtifacts.consoleLog));
const errorsPreview = trimPreview(await readTextOrNull(diagnosisArtifacts.errorsLog));
const cdpPreview = trimPreview(await readTextOrNull(diagnosisArtifacts.cdpTrace));
const baselineDomPreview = trimPreview(await readTextOrNull(comparisonBaselineArtifacts.dom));
const screenshotDiffExists = await exists(screenshotDiffPath);
const candidateScreenshotExists = await exists(diagnosisArtifacts.screenshot);
const baselineScreenshotExists = await exists(comparisonBaselineArtifacts.screenshot);

const artifactEntries = [
  { scope: 'candidate', label: 'diagnosis', path: path.resolve(diagnosisPath) },
  { scope: 'candidate', label: 'summary', path: diagnosisArtifacts.summary },
  { scope: 'candidate', label: 'screenshot', path: diagnosisArtifacts.screenshot },
  { scope: 'candidate', label: 'DOM snapshot', path: diagnosisArtifacts.dom },
  { scope: 'candidate', label: 'console log', path: diagnosisArtifacts.consoleLog },
  { scope: 'candidate', label: 'errors log', path: diagnosisArtifacts.errorsLog },
  { scope: 'candidate', label: 'CDP trace', path: diagnosisArtifacts.cdpTrace },
  { scope: 'candidate', label: 'deploy report', path: diagnosisArtifacts.deployReport },
  { scope: 'candidate', label: 'scenario report', path: diagnosisArtifacts.scenarioReport },
  { scope: 'comparison', label: 'comparison JSON', path: comparisonPath ? path.resolve(comparisonPath) : null },
  { scope: 'comparison', label: 'screenshot diff', path: screenshotDiffPath },
  { scope: 'baseline', label: 'baseline screenshot', path: comparisonBaselineArtifacts.screenshot ?? null },
  { scope: 'baseline', label: 'baseline DOM snapshot', path: comparisonBaselineArtifacts.dom ?? null },
  { scope: 'baseline', label: 'baseline console log', path: comparisonBaselineArtifacts.consoleLog ?? null },
  { scope: 'baseline', label: 'baseline errors log', path: comparisonBaselineArtifacts.errorsLog ?? null },
  { scope: 'profile', label: 'profile summary', path: profilePath ? path.resolve(profilePath) : null },
].filter((entry, index, all) => (
  entry.path || !all.slice(0, index).some((other) => other.scope === entry.scope && other.label === entry.label)
));

const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Obsidian Debug Report</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; color: #111; background: #fafafa; }
    h1, h2, h3 { margin-bottom: 8px; }
    p { line-height: 1.45; }
    .badge { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px; margin: 0 8px 8px 0; }
    .pass { background: #d1fae5; color: #065f46; }
    .warning { background: #fef3c7; color: #92400e; }
    .warn { background: #fef3c7; color: #92400e; }
    .fail { background: #fee2e2; color: #991b1b; }
    .expected { background: #e0e7ff; color: #3730a3; }
    .flaky { background: #fde68a; color: #92400e; }
    .info { background: #dbeafe; color: #1e3a8a; }
    .card { background: white; border: 1px solid #e5e7eb; border-radius: 14px; padding: 16px; margin: 16px 0; box-shadow: 0 8px 20px rgba(0,0,0,0.04); }
    .artifact-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
    .artifact-card { background: #fcfcfd; border: 1px solid #e5e7eb; border-radius: 12px; padding: 12px; }
    .artifact-card img { max-width: 100%; border-radius: 10px; border: 1px solid #e5e7eb; background: #fff; }
    .muted { color: #6b7280; }
    table { width: 100%; border-collapse: collapse; margin-top: 8px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #eee; font-size: 14px; vertical-align: top; }
    code { background: #f3f4f6; padding: 2px 5px; border-radius: 6px; }
    pre { background: #0f172a; color: #e2e8f0; padding: 12px; border-radius: 10px; overflow: auto; max-height: 320px; }
    ul { margin-top: 8px; }
    .meta { display: flex; flex-wrap: wrap; gap: 8px; }
  </style>
</head>
<body>
  <h1>Obsidian Debug Report</h1>
  <div class="card">
    <div class="meta">
      <span class="badge ${escapeHtml(normalizeStatusClass(diagnosis.status))}">${escapeHtml(diagnosis.status)}</span>
      ${comparison ? renderStatusSummary('Compare', comparison.status) : ''}
      ${comparison ? renderStatusSummary('Visual', comparison.visualStatus ?? comparison.screenshotDiff?.status ?? 'n/a', comparison.screenshotDiff?.status === 'different' ? 'warn' : 'info') : ''}
    </div>
    <strong>${escapeHtml(diagnosis.headline)}</strong>
    <p>Plugin: <code>${escapeHtml(diagnosis.pluginId)}</code> | Vault: <code>${escapeHtml(diagnosis.vaultName)}</code></p>
    <p>${renderArtifactLink(path.resolve(diagnosisPath), 'Diagnosis JSON')}</p>
  </div>

  <div class="card">
    <h2>UI Artifacts</h2>
    <div class="artifact-grid">
      ${renderPreviewCard({
        title: 'Candidate Screenshot',
        label: 'candidate screenshot',
        path: candidateScreenshotExists ? diagnosisArtifacts.screenshot : null,
        kind: 'image',
      })}
      ${renderPreviewCard({
        title: 'Baseline Screenshot',
        label: 'baseline screenshot',
        path: baselineScreenshotExists ? comparisonBaselineArtifacts.screenshot : null,
        kind: 'image',
      })}
      ${renderPreviewCard({
        title: 'Screenshot Diff',
        label: 'screenshot diff',
        path: screenshotDiffExists ? screenshotDiffPath : null,
        kind: 'image',
      })}
    </div>
    ${comparison?.screenshotDiff ? `<p class="muted">
      Screenshot diff: <strong>${escapeHtml(comparison.screenshotDiff.status)}</strong>
      ${comparison.screenshotDiff.reason ? ` — ${escapeHtml(comparison.screenshotDiff.reason)}` : ''}
      ${comparison.screenshotDiff.changedPixels !== null ? ` — changed pixels: ${escapeHtml(comparison.screenshotDiff.changedPixels)} / ${escapeHtml(comparison.screenshotDiff.comparedPixels)} (${escapeHtml(comparison.screenshotDiff.changedRatio)})` : ''}
      ${comparison.screenshotDiff.diffBounds ? ` — region: (${escapeHtml(comparison.screenshotDiff.diffBounds.left)}, ${escapeHtml(comparison.screenshotDiff.diffBounds.top)}) to (${escapeHtml(comparison.screenshotDiff.diffBounds.right)}, ${escapeHtml(comparison.screenshotDiff.diffBounds.bottom)})` : ''}
    </p>` : '<p class="muted">No screenshot comparison available.</p>'}
  </div>

  <div class="card">
    <h2>Artifact Links</h2>
    <table>
      <tr><th>Scope</th><th>Artifact</th><th>Path</th></tr>
      ${renderArtifactRows(artifactEntries)}
    </table>
  </div>

  <div class="card">
    <h2>Artifact Previews</h2>
    <div class="artifact-grid">
      ${renderPreviewCard({
        title: 'Candidate DOM Snapshot',
        label: 'candidate DOM snapshot',
        path: diagnosisArtifacts.dom,
        preview: domPreview,
      })}
      ${renderPreviewCard({
        title: 'Candidate Console Log',
        label: 'candidate console log',
        path: diagnosisArtifacts.consoleLog,
        preview: consolePreview,
      })}
      ${renderPreviewCard({
        title: 'Candidate Errors Log',
        label: 'candidate errors log',
        path: diagnosisArtifacts.errorsLog,
        preview: errorsPreview,
      })}
      ${renderPreviewCard({
        title: 'Candidate CDP Trace',
        label: 'candidate CDP trace',
        path: diagnosisArtifacts.cdpTrace,
        preview: cdpPreview,
      })}
      ${renderPreviewCard({
        title: 'Baseline DOM Snapshot',
        label: 'baseline DOM snapshot',
        path: comparisonBaselineArtifacts.dom ?? null,
        preview: baselineDomPreview,
      })}
    </div>
  </div>

  <div class="card">
    <h2>Timings</h2>
    ${renderMetricTable(diagnosis.timings)}
  </div>

  <div class="card">
    <h2>Assertions</h2>
    <p>
      Total: <code>${escapeHtml(diagnosis.assertionSummary?.total ?? 0)}</code>
      | Blocking: <code>${escapeHtml((diagnosis.assertionSummary?.blockingFailures ?? []).length)}</code>
      | Warn: <code>${escapeHtml((diagnosis.assertionSummary?.warnings ?? []).length)}</code>
      | Expected: <code>${escapeHtml((diagnosis.assertionSummary?.expected ?? []).length)}</code>
      | Flaky: <code>${escapeHtml((diagnosis.assertionSummary?.flaky ?? []).length)}</code>
    </p>
    <table>
      <tr><th>ID</th><th>Status</th><th>Severity</th><th>Detail</th></tr>
      ${renderAssertionRows([...(diagnosis.assertions ?? []), ...(diagnosis.customAssertions ?? [])])}
    </table>
  </div>

  <div class="card">
    <h2>Signatures</h2>
    <ul>
      ${renderList(diagnosis.signatures ?? [], (entry) => `<li><strong>${escapeHtml(entry.id)}</strong> — ${escapeHtml(entry.headline)}</li>`)}
    </ul>
  </div>

  <div class="card">
    <h2>Playbooks</h2>
    ${renderPlaybooks(diagnosis.playbooks ?? [])}
  </div>

  <div class="card">
    <h2>Recommendations</h2>
    <ul>
      ${renderList(diagnosis.recommendations ?? [], (entry) => `<li>${escapeHtml(entry)}</li>`)}
    </ul>
  </div>

  ${comparison ? `<div class="card">
    <h2>Comparison</h2>
    <p>
      ${renderStatusSummary('Status', comparison.status)}
      ${renderStatusSummary('Visual', comparison.visualStatus ?? comparison.screenshotDiff?.status ?? 'n/a', comparison.screenshotDiff?.status === 'different' ? 'warn' : 'info')}
    </p>
    <p>
      Baseline: ${renderArtifactLink(comparison.baseline?.path, 'Missing baseline diagnosis')}
      ${comparison.baseline?.name ? `(<code>${escapeHtml(comparison.baseline.name)}</code>)` : ''}
      | Candidate: ${renderArtifactLink(comparison.candidate?.path, 'Missing candidate diagnosis')}
    </p>
    ${comparison.screenshotDiff ? `<table>
      <tr><th>Visual Metric</th><th>Value</th></tr>
      <tr><td>Status</td><td>${escapeHtml(comparison.screenshotDiff.status)}</td></tr>
      <tr><td>Reason</td><td>${escapeHtml(comparison.screenshotDiff.reason ?? '')}</td></tr>
      <tr><td>Compared Pixels</td><td>${escapeHtml(comparison.screenshotDiff.comparedPixels)}</td></tr>
      <tr><td>Changed Pixels</td><td>${escapeHtml(comparison.screenshotDiff.changedPixels)}</td></tr>
      <tr><td>Changed Ratio</td><td>${escapeHtml(comparison.screenshotDiff.changedRatio)}</td></tr>
      <tr><td>Diff Region</td><td>${comparison.screenshotDiff.diffBounds ? escapeHtml(`${comparison.screenshotDiff.diffBounds.left},${comparison.screenshotDiff.diffBounds.top} → ${comparison.screenshotDiff.diffBounds.right},${comparison.screenshotDiff.diffBounds.bottom}`) : 'None'}</td></tr>
      <tr><td>Diff Artifact</td><td>${comparison.screenshotDiff.diffPath ? renderArtifactLink(comparison.screenshotDiff.diffPath) : 'Missing'}</td></tr>
    </table>` : '<p class="muted">No visual diff was recorded.</p>'}
    <table>
      <tr><th>Metric</th><th>Baseline</th><th>Candidate</th><th>Delta</th></tr>
      ${renderTableRows(comparison.timingDiffs ?? [], (entry) => `<tr><td>${escapeHtml(entry.metric)}</td><td>${escapeHtml(entry.baseline)}</td><td>${escapeHtml(entry.candidate)}</td><td>${escapeHtml(entry.delta)}</td></tr>`, 4)}
    </table>
    <table>
      <tr><th>Assertion</th><th>Baseline</th><th>Candidate</th></tr>
      ${renderTableRows(comparison.assertions?.changed ?? [], (entry) => `<tr><td><code>${escapeHtml(entry.id)}</code></td><td>${escapeHtml(entry.baseline)}</td><td>${escapeHtml(entry.candidate)}</td></tr>`, 3)}
    </table>
    <p><strong>Added signatures:</strong> ${comparison.signatures?.added?.length ? comparison.signatures.added.map((entry) => `<code>${escapeHtml(entry)}</code>`).join(' ') : 'None'}</p>
    <p><strong>Removed signatures:</strong> ${comparison.signatures?.removed?.length ? comparison.signatures.removed.map((entry) => `<code>${escapeHtml(entry)}</code>`).join(' ') : 'None'}</p>
  </div>` : ''}

  ${profile ? `<div class="card">
    <h2>Profile Summary</h2>
    <p>Label: <code>${escapeHtml(profile.label)}</code> | Mode: <code>${escapeHtml(profile.mode)}</code> | Runs: <code>${escapeHtml(profile.runs)}</code></p>
    <table>
      <tr><th>Metric</th><th>Avg</th><th>Min</th><th>Max</th><th>Samples</th></tr>
      ${renderTableRows(Object.entries(profile.timingSummary ?? {}), ([metric, summary]) => `<tr><td>${escapeHtml(metric)}</td><td>${escapeHtml(summary.avg)}</td><td>${escapeHtml(summary.min)}</td><td>${escapeHtml(summary.max)}</td><td>${escapeHtml(summary.samples)}</td></tr>`, 5)}
    </table>
  </div>` : ''}
</body>
</html>`;

await ensureParentDirectory(outputPath);
await fs.writeFile(outputPath, html, 'utf8');
console.log(outputPath);
