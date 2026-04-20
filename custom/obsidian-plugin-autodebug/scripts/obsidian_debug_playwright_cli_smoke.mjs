import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const toolRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const scriptRoot = path.join(toolRoot, 'scripts');

function runProcess(command, args, { cwd, env } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd,
      env,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    child.on('error', reject);
    child.on('close', (code) => {
      resolve({
        code: code ?? 1,
        stdout,
        stderr,
      });
    });
  });
}

async function writeFakeCli(tempDir) {
  const statePath = path.join(tempDir, 'playwright-cli-state.json');
  const cliPath = path.join(tempDir, 'fake-playwright-cli.mjs');
  await fs.writeFile(statePath, '[]\n', 'utf8');
  await fs.writeFile(cliPath, `import fs from 'node:fs/promises';
import path from 'node:path';

const args = process.argv.slice(2);
const statePath = process.env.PLAYWRIGHT_CLI_SMOKE_STATE;

async function appendState(entry) {
  const existing = JSON.parse(await fs.readFile(statePath, 'utf8'));
  existing.push(entry);
  await fs.writeFile(statePath, JSON.stringify(existing, null, 2), 'utf8');
}

function findCommand(argv) {
  for (const token of argv) {
    if (!token.startsWith('-')) {
      return token;
    }
  }
  return '';
}

function findFilename(argv) {
  const direct = argv.find((entry) => entry.startsWith('--filename='));
  if (direct) {
    return direct.slice('--filename='.length);
  }
  const index = argv.findIndex((entry) => entry === '--filename');
  return index >= 0 ? argv[index + 1] ?? '' : '';
}

function findTracePathFromCode(argv) {
  const index = argv.findIndex((entry) => entry === 'run-code');
  const code = index >= 0 ? argv[index + 1] ?? '' : '';
  const match = code.match(/tracing\\.stop\\(\\{\\s*path:\\s*"([^"]+)"/);
  return match ? JSON.parse(\`"\${match[1]}"\`) : '';
}

await appendState({ args });

if (args.includes('--version')) {
  console.log('playwright-cli 0.0.0-smoke');
  process.exit(0);
}

const command = findCommand(args);
if (command === 'attach') {
  console.log('attached');
  process.exit(0);
}

if (command === 'run-code') {
  const tracePath = findTracePathFromCode(args);
  if (tracePath) {
    await fs.mkdir(path.dirname(tracePath), { recursive: true });
    await fs.writeFile(tracePath, 'fake trace', 'utf8');
  }
  console.log('ok');
  process.exit(0);
}

if (command === 'screenshot') {
  const filename = findFilename(args);
  if (!filename) {
    console.error('missing --filename');
    process.exit(1);
  }
  await fs.mkdir(path.dirname(filename), { recursive: true });
  await fs.writeFile(filename, 'fake screenshot', 'utf8');
  console.log(filename);
  process.exit(0);
}

if (command === 'tracing-start') {
  console.log('trace-started');
  process.exit(0);
}

if (command === 'close') {
  console.log('closed');
  process.exit(0);
}

console.error(\`unsupported command: \${command || '(none)'}\`);
process.exit(1);
`, 'utf8');
  return {
    cliPath,
    statePath,
  };
}

async function writeScenario(tempDir, { trace = true } = {}) {
  const scenarioPath = path.join(tempDir, 'scenario.json');
  await fs.writeFile(scenarioPath, JSON.stringify({
    name: 'playwright-cli-smoke',
    description: 'Exercise explicit playwright-cli fallback for locator and screenshot steps.',
    adapter: 'playwright',
    playwright: {
      trace,
      tracePath: path.join(tempDir, 'playwright-trace.zip'),
      screenshotPath: path.join(tempDir, 'playwright-scenario.png'),
      selectorTimeoutMs: 2500,
    },
    steps: [
      {
        type: 'locator-wait',
        selector: '#root',
        state: 'visible',
      },
      {
        type: 'locator-click',
        selector: '#root button.primary',
      },
      {
        type: 'locator-fill',
        selector: '#search',
        value: 'hello',
      },
      {
        type: 'locator-press',
        selector: '#search',
        key: 'Enter',
      },
      {
        type: 'locator-assert',
        selector: '#status',
        state: 'visible',
        textIncludes: 'ready',
      },
      {
        type: 'page-screenshot',
        path: path.join(tempDir, 'step-screenshot.png'),
      },
    ],
  }, null, 2), 'utf8');
  return scenarioPath;
}

async function writeSurfaceProfile(tempDir) {
  const surfaceProfilePath = path.join(tempDir, 'surface-profile.json');
  await fs.writeFile(surfaceProfilePath, JSON.stringify({
    plugin: {
      id: 'sample-plugin',
      name: 'Sample Plugin',
    },
    dom: {
      elements: [
        {
          tag: 'div',
          id: 'root',
          classes: ['workspace-leaf', 'mod-active'],
          text: 'Sample Plugin',
          attributes: {
            'data-plugin-id': 'sample-plugin',
          },
        },
      ],
    },
  }, null, 2), 'utf8');
  return surfaceProfilePath;
}

async function main() {
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'obsidian-playwright-cli-smoke-'));
  const { cliPath, statePath } = await writeFakeCli(tempDir);
  const scenarioPath = await writeScenario(tempDir, { trace: true });
  const surfaceProfilePath = await writeSurfaceProfile(tempDir);
  const successReportPath = path.join(tempDir, 'scenario-report.json');
  const successRun = await runProcess(
    'node',
    [
      path.join(scriptRoot, 'obsidian_debug_scenario_runner.mjs'),
      '--scenario-path',
      scenarioPath,
      '--adapter',
      'playwright',
      '--cli-available',
      'false',
      '--surface-profile',
      surfaceProfilePath,
      '--cdp-port',
      '9222',
      '--playwright-cli-command',
      `node ${JSON.stringify(cliPath).slice(1, -1)}`,
      '--playwright-no-bootstrap',
      '--output',
      successReportPath,
    ],
    {
      cwd: toolRoot,
      env: {
        ...process.env,
        PLAYWRIGHT_CLI_SMOKE_STATE: statePath,
      },
    },
  );

  assert.equal(successRun.code, 0, `success case should pass:\nSTDOUT:\n${successRun.stdout}\nSTDERR:\n${successRun.stderr}`);

  const successReport = JSON.parse(successRun.stdout);
  assert.equal(successReport.success, true, 'scenario should succeed when explicit playwright-cli command is available');
  assert.equal(successReport.adapter, 'playwright');
  assert.equal(successReport.playwright?.driver?.mode, 'cli');
  assert.equal(successReport.playwright?.trace?.captured, true);
  assert.equal(successReport.playwright?.screenshot?.captured, true);
  assert.equal(await fs.readFile(path.join(tempDir, 'step-screenshot.png'), 'utf8'), 'fake screenshot');
  assert.equal(await fs.readFile(path.join(tempDir, 'playwright-trace.zip'), 'utf8'), 'fake trace');

  const state = JSON.parse(await fs.readFile(statePath, 'utf8'));
  assert(state.some((entry) => entry.args.includes('attach')), 'fake playwright-cli should receive attach');
  assert(state.some((entry) => entry.args.includes('run-code')), 'fake playwright-cli should receive run-code');
  assert(state.some((entry) => entry.args.includes('screenshot')), 'fake playwright-cli should receive screenshot');
  assert(state.some((entry) => entry.args.some((arg) => /async page =>/.test(arg))), 'run-code should receive playwright-cli function wrapper');
  assert(state.some((entry) => entry.args.some((arg) => /tracing\.start/.test(arg))), 'fake playwright-cli should start tracing through run-code');
  assert(state.some((entry) => entry.args.some((arg) => /tracing\.stop/.test(arg))), 'fake playwright-cli should stop tracing through run-code');
  assert(state.some((entry) => entry.args.includes('close')), 'fake playwright-cli should receive close');

  const missingReportPath = path.join(tempDir, 'missing-report.json');
  const missingRun = await runProcess(
    'node',
    [
      path.join(scriptRoot, 'obsidian_debug_scenario_runner.mjs'),
      '--scenario-path',
      scenarioPath,
      '--adapter',
      'playwright',
      '--cli-available',
      'false',
      '--dry-run',
      '--surface-profile',
      surfaceProfilePath,
      '--playwright-cli-command',
      `node ${JSON.stringify(path.join(tempDir, 'missing-playwright-cli.mjs')).slice(1, -1)}`,
      '--playwright-no-bootstrap',
      '--output',
      missingReportPath,
    ],
    {
      cwd: toolRoot,
    },
  );

  assert.equal(missingRun.code, 1, 'missing explicit playwright-cli should fail cleanly');
  assert.doesNotMatch(missingRun.stderr, /Scenario failed:|Error: Scenario failed|at file:/, 'missing-path failure should not print a raw stack');
  const missingReport = JSON.parse(missingRun.stdout);
  assert.equal(missingReport.success, false);
  assert.equal(missingReport.playwright?.driver?.mode, 'cli');
  assert.equal(missingReport.playwright?.driver?.available, false);
  assert.match(missingReport.steps?.[0]?.error ?? '', /playwright/i);

  console.log(JSON.stringify({
    status: 'pass',
    reportPath: successReportPath,
    checkedCases: ['explicit-cli-success', 'explicit-cli-missing-clean-failure'],
  }, null, 2));
}

await main();
