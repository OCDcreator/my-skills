import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {
  detectControlBackends,
  generateControlBackendsManifest,
} from './obsidian_debug_control_backend_support.mjs';

const doctor = {
  repoDir: 'C:/repo/plugin',
  obsidianCommand: 'obsidian',
  vaultName: 'Test Vault',
  checks: [
    {
      id: 'obsidian-cli',
      category: 'runtime',
      status: 'pass',
      detail: 'Obsidian CLI developer commands are available.',
    },
  ],
  cdp: {
    host: '127.0.0.1',
    port: 9222,
    available: true,
  },
  adapterLanes: {
    testingFramework: {
      runnable: true,
      runnableInThisCheckout: true,
      detail: 'Repo Playwright lane is runnable.',
    },
  },
  agenticSupport: {
    controlSurfaces: {
      mcpRest: {
        detected: true,
        available: true,
        detail: 'REST/MCP probe reached localhost with allowlisted tools.',
      },
      devtoolsMcp: {
        detected: true,
        available: false,
        detail: 'Chrome DevTools MCP signal detected; target still needs confirmation.',
      },
    },
    runtimeProbes: {
      rest: {
        configured: true,
        ok: true,
        localhost: true,
        authProvided: true,
        toolAllowlist: true,
      },
    },
  },
};

const diagnosis = {
  pluginId: 'sample-plugin',
  useCdp: true,
  runtime: {
    repoDir: 'C:/repo/plugin',
    outputDir: 'C:/repo/plugin/.obsidian-debug',
  },
  artifacts: {
    playwrightScreenshot: 'C:/repo/plugin/.obsidian-debug/playwright.png',
  },
};

const manifest = detectControlBackends({
  diagnosisDocument: diagnosis,
  doctorDocument: doctor,
  preferredBackend: 'playwright-script',
});

assert.equal(manifest.backends['obsidian-cli'].available, true);
assert.equal(manifest.backends['bundled-cdp'].available, true);
assert.equal(manifest.backends['obsidian-cli-rest'].available, true);
assert.equal(manifest.backends['chrome-devtools-mcp'].detected, true);
assert.equal(manifest.backends['chrome-devtools-mcp'].available, false);
assert.equal(manifest.backends['playwright-script'].available, true);
assert.equal(manifest.selections.locatorActions.backendId, 'playwright-script');
assert.equal(manifest.selections.reloadPlugin.backendId, 'obsidian-cli');
assert.equal(manifest.selections.networkInspection.backendId, 'bundled-cdp');
assert(
  manifest.recommendations.some((entry) => /visual-review pack/i.test(entry)),
  'manifest should recommend visual review after screenshot capture',
);

const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'obsidian-control-backends-'));
const doctorPath = path.join(tempDir, 'doctor.json');
const diagnosisPath = path.join(tempDir, 'diagnosis.json');
const outputPath = path.join(tempDir, 'control-backends.json');
await fs.writeFile(doctorPath, JSON.stringify(doctor, null, 2), 'utf8');
await fs.writeFile(diagnosisPath, JSON.stringify(diagnosis, null, 2), 'utf8');

const written = await generateControlBackendsManifest({
  doctorPath,
  diagnosisPath,
  outputPath,
});

assert.equal(written.outputPath, outputPath);
const writtenJson = JSON.parse(await fs.readFile(outputPath, 'utf8'));
assert.equal(writtenJson.selections.captureScreenshot.backendId, 'obsidian-cli');
assert.equal(writtenJson.backends['playwright-mcp'].status, 'missing');

console.log(JSON.stringify({
  status: 'pass',
  outputPath,
  availableBackends: Object.values(manifest.backends).filter((entry) => entry.available).map((entry) => entry.id),
}, null, 2));
