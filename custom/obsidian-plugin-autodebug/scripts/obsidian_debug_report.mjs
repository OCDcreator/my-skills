import fs from 'node:fs/promises';
import path from 'node:path';
import {
  ensureParentDirectory,
  getStringOption,
  parseArgs,
} from './obsidian_cdp_common.mjs';

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
    <div style="border: 1px solid #e5e7eb; border-radius: 12px; padding: 12px; margin-top: 12px;">
      <strong>${escapeHtml(playbook.title ?? playbook.id)}</strong>
      <p>${escapeHtml(playbook.summary ?? '')}</p>
      <p><strong>ID:</strong> <code>${escapeHtml(playbook.id)}</code></p>
      <p><strong>Files:</strong> ${playbook.files?.length ? playbook.files.map((item) => `<code>${escapeHtml(item)}</code>`).join(' ') : 'None'}</p>
      <p><strong>Commands:</strong> ${playbook.commands?.length ? playbook.commands.map((item) => `<code>${escapeHtml(item)}</code>`).join(' ') : 'None'}</p>
      <ul>${renderList(playbook.actions ?? [], (entry) => `<li>${escapeHtml(entry)}</li>`)}</ul>
    </div>
  `).join('');
}

const diagnosis = await readJsonOrNull(diagnosisPath);
if (!diagnosis) {
  throw new Error(`Unable to read diagnosis JSON: ${diagnosisPath}`);
}

const comparison = await readJsonOrNull(comparisonPath);
const profile = await readJsonOrNull(profilePath);

const html = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Obsidian Debug Report</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; color: #111; background: #fafafa; }
    h1, h2 { margin-bottom: 8px; }
    .badge { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px; margin-right: 8px; }
    .pass { background: #d1fae5; color: #065f46; }
    .warning { background: #fef3c7; color: #92400e; }
    .warn { background: #fef3c7; color: #92400e; }
    .fail { background: #fee2e2; color: #991b1b; }
    .expected { background: #e0e7ff; color: #3730a3; }
    .flaky { background: #fde68a; color: #92400e; }
    .info { background: #dbeafe; color: #1e3a8a; }
    .card { background: white; border: 1px solid #e5e7eb; border-radius: 14px; padding: 16px; margin: 16px 0; box-shadow: 0 8px 20px rgba(0,0,0,0.04); }
    table { width: 100%; border-collapse: collapse; margin-top: 8px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #eee; font-size: 14px; vertical-align: top; }
    code { background: #f3f4f6; padding: 2px 5px; border-radius: 6px; }
    ul { margin-top: 8px; }
  </style>
</head>
<body>
  <h1>Obsidian Debug Report</h1>
  <div class="card">
    <div class="badge ${escapeHtml(normalizeStatusClass(diagnosis.status))}">${escapeHtml(diagnosis.status)}</div>
    <strong>${escapeHtml(diagnosis.headline)}</strong>
    <p>Plugin: <code>${escapeHtml(diagnosis.pluginId)}</code> | Vault: <code>${escapeHtml(diagnosis.vaultName)}</code></p>
  </div>

  <div class="card">
    <h2>Timings</h2>
    <table>
      <tr><th>Metric</th><th>Value</th></tr>
      ${Object.entries(diagnosis.timings ?? {}).map(([key, value]) => `<tr><td>${escapeHtml(key)}</td><td>${escapeHtml(value)}</td></tr>`).join('')}
    </table>
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
    <p>Status: <strong>${escapeHtml(comparison.status)}</strong></p>
    <table>
      <tr><th>Metric</th><th>Baseline</th><th>Candidate</th><th>Delta</th></tr>
      ${(comparison.timingDiffs ?? []).map((entry) => `<tr><td>${escapeHtml(entry.metric)}</td><td>${escapeHtml(entry.baseline)}</td><td>${escapeHtml(entry.candidate)}</td><td>${escapeHtml(entry.delta)}</td></tr>`).join('')}
    </table>
  </div>` : ''}

  ${profile ? `<div class="card">
    <h2>Profile Summary</h2>
    <p>Label: <code>${escapeHtml(profile.label)}</code> | Mode: <code>${escapeHtml(profile.mode)}</code> | Runs: <code>${escapeHtml(profile.runs)}</code></p>
    <table>
      <tr><th>Metric</th><th>Avg</th><th>Min</th><th>Max</th><th>Samples</th></tr>
      ${Object.entries(profile.timingSummary ?? {}).map(([metric, summary]) => `<tr><td>${escapeHtml(metric)}</td><td>${escapeHtml(summary.avg)}</td><td>${escapeHtml(summary.min)}</td><td>${escapeHtml(summary.max)}</td><td>${escapeHtml(summary.samples)}</td></tr>`).join('')}
    </table>
  </div>` : ''}
</body>
</html>`;

await ensureParentDirectory(outputPath);
await fs.writeFile(outputPath, html, 'utf8');
console.log(outputPath);
