import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import {
  ensureParentDirectory,
  getNumberOption,
  getStringOption,
  nowIso,
  parseArgs,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
const runs = Math.max(1, getNumberOption(options, 'runs', 2));
const commandTemplate = getStringOption(options, 'command', '').trim();
const rootOutput = path.resolve(getStringOption(options, 'root-output', '.obsidian-debug/profile-runs'));
const summaryPath = path.resolve(getStringOption(options, 'summary', path.join(rootOutput, 'profile-summary.json')));
const label = getStringOption(options, 'label', 'default');
const mode = getStringOption(options, 'mode', 'warm');
const workingDirectory = getStringOption(options, 'cwd', '').trim();

if (!commandTemplate) {
  throw new Error('--command is required');
}

function average(values) {
  if (values.length === 0) {
    return null;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function min(values) {
  return values.length > 0 ? Math.min(...values) : null;
}

function max(values) {
  return values.length > 0 ? Math.max(...values) : null;
}

function buildCommand(command, outputDir, runNumber) {
  return command
    .replaceAll('{{outputDir}}', outputDir)
    .replaceAll('{{run}}', String(runNumber));
}

function runShellCommand(command, cwd) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, {
      cwd: cwd || undefined,
      shell: true,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      const text = chunk.toString();
      stdout += text;
      process.stdout.write(text);
    });
    child.stderr.on('data', (chunk) => {
      const text = chunk.toString();
      stderr += text;
      process.stderr.write(text);
    });
    child.on('error', reject);
    child.on('close', (code) => {
      resolve({
        exitCode: code ?? 0,
        stdout,
        stderr,
      });
    });
  });
}

await fs.mkdir(rootOutput, { recursive: true });
const runsData = [];

for (let runNumber = 1; runNumber <= runs; runNumber += 1) {
  const runOutput = path.join(rootOutput, `run-${String(runNumber).padStart(2, '0')}`);
  await fs.rm(runOutput, { recursive: true, force: true });
  await fs.mkdir(runOutput, { recursive: true });

  const command = buildCommand(commandTemplate, runOutput, runNumber);
  const startedAt = nowIso();
  const result = await runShellCommand(command, workingDirectory);
  const finishedAt = nowIso();

  const diagnosisPath = path.join(runOutput, 'diagnosis.json');
  let diagnosis = null;
  try {
    diagnosis = JSON.parse(await fs.readFile(diagnosisPath, 'utf8'));
  } catch {
    diagnosis = null;
  }

  runsData.push({
    run: runNumber,
    outputDir: runOutput,
    command,
    startedAt,
    finishedAt,
    exitCode: result.exitCode,
    diagnosisPath: diagnosis ? diagnosisPath : null,
    diagnosisStatus: diagnosis?.status ?? null,
    timings: diagnosis?.timings ?? {},
    signatures: (diagnosis?.signatures ?? []).map((entry) => entry.id),
    assertionsFailed: [
      ...(diagnosis?.assertions ?? []).filter((entry) => entry.status === 'fail').map((entry) => entry.id),
      ...(diagnosis?.customAssertions ?? []).filter((entry) => entry.status === 'fail').map((entry) => entry.id),
    ],
  });
}

const timingMetrics = ['startupCompletedMs', 'viewOpenCompletedMs', 'serverReadyMs', 'chatReadyDelayMs'];
const timingSummary = Object.fromEntries(
  timingMetrics.map((metric) => {
    const values = runsData
      .map((entry) => entry.timings?.[metric])
      .filter((value) => Number.isFinite(value));
    return [
      metric,
      {
        avg: average(values),
        min: min(values),
        max: max(values),
        samples: values.length,
      },
    ];
  }),
);

const statusCounts = {};
for (const run of runsData) {
  const key = run.diagnosisStatus ?? 'missing';
  statusCounts[key] = (statusCounts[key] ?? 0) + 1;
}

const signatureCounts = {};
for (const run of runsData) {
  for (const signature of run.signatures) {
    signatureCounts[signature] = (signatureCounts[signature] ?? 0) + 1;
  }
}

const failedAssertionCounts = {};
for (const run of runsData) {
  for (const assertionId of run.assertionsFailed) {
    failedAssertionCounts[assertionId] = (failedAssertionCounts[assertionId] ?? 0) + 1;
  }
}

const profileSummary = {
  generatedAt: nowIso(),
  label,
  mode,
  runs,
  rootOutput,
  timingSummary,
  statusCounts,
  signatureCounts,
  failedAssertionCounts,
  runsData,
};

await ensureParentDirectory(summaryPath);
await fs.writeFile(summaryPath, `${JSON.stringify(profileSummary, null, 2)}\n`, 'utf8');
console.log(JSON.stringify(profileSummary, null, 2));
