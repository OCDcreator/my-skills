import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { generateVisualReviewPack } from './obsidian_debug_visual_review.mjs';

const ONE_PIXEL_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=',
  'base64',
);

const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'obsidian-visual-review-'));
const screenshotPath = path.join(tempDir, 'screenshot.png');
const domPath = path.join(tempDir, 'dom.html');
const scenarioPath = path.join(tempDir, 'scenario-report.json');
const comparisonPath = path.join(tempDir, 'comparison.json');
const diagnosisPath = path.join(tempDir, 'diagnosis.json');
const outputPath = path.join(tempDir, 'visual-review.json');
const htmlOutputPath = path.join(tempDir, 'visual-review.html');

await fs.writeFile(screenshotPath, ONE_PIXEL_PNG);
await fs.writeFile(domPath, '<div class="workspace-leaf mod-active"><button>Run</button></div>\n', 'utf8');
await fs.writeFile(scenarioPath, JSON.stringify({
  success: true,
  scenarioName: 'open-plugin-view',
  selectedStrategy: { kind: 'obsidian-command', commandId: 'sample:open-view' },
}, null, 2), 'utf8');
await fs.writeFile(comparisonPath, JSON.stringify({
  screenshotDiff: { status: 'identical', changedRatio: '0' },
}, null, 2), 'utf8');
await fs.writeFile(diagnosisPath, JSON.stringify({
  pluginId: 'sample-plugin',
  artifacts: {
    screenshot: screenshotPath,
    dom: domPath,
    scenarioReport: scenarioPath,
    comparisonReport: comparisonPath,
  },
  assertions: [
    { id: 'screenshot-captured', status: 'pass', detail: 'Captured screenshot.' },
  ],
}, null, 2), 'utf8');

const pack = await generateVisualReviewPack({
  diagnosisPath,
  outputPath,
  htmlOutputPath,
});

assert.equal(pack.visualReview.canReplaceManualGuiValidation, false);
assert.equal(pack.visualReview.humanReviewRequired, true);
assert.equal(pack.visualReview.status, 'needs-human-review');
assert.equal(pack.metadata.pluginId, 'sample-plugin');
assert.equal(pack.artifacts.screenshot.exists, true);
assert.equal(pack.artifacts.dom.exists, true);
assert(pack.checklist.length >= 5, 'visual checklist should include default human review checks');
assert(
  pack.checklist.every((entry) => entry.status === 'needs-human-review'),
  'checklist entries should stay human-review gated',
);
assert(
  pack.findings.some((entry) => entry.id === 'scenario-status' && entry.status === 'pass'),
  'scenario success should be summarized',
);

const writtenJson = JSON.parse(await fs.readFile(outputPath, 'utf8'));
const writtenHtml = await fs.readFile(htmlOutputPath, 'utf8');
assert.equal(writtenJson.visualReview.canReplaceManualGuiValidation, false);
assert(writtenHtml.includes('Obsidian Visual Review Pack'));
assert(writtenHtml.includes('Screenshots, DOM, and scenario output'));

console.log(JSON.stringify({
  status: 'pass',
  outputPath,
  htmlOutputPath,
  checklistCount: pack.checklist.length,
}, null, 2));
