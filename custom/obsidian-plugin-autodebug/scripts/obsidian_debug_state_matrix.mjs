import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import {
  ensureParentDirectory,
  getBooleanOption,
  getStringOption,
  nowIso,
  parseArgs,
} from './obsidian_cdp_common.mjs';
import {
  normalizePlatform,
  renderExplicitCommand,
} from './obsidian_debug_command_templates.mjs';

const options = parseArgs(process.argv.slice(2));
const jobPathRaw = getStringOption(options, 'job', '').trim();
const statePlanRaw = getStringOption(options, 'state-plan', '').trim();
const vaultRootRaw = getStringOption(options, 'vault-root', '').trim();
const pluginId = getStringOption(options, 'plugin-id', '').trim();

if (!jobPathRaw) {
  throw new Error('--job is required');
}
if (!statePlanRaw) {
  throw new Error('--state-plan is required');
}
if (!vaultRootRaw) {
  throw new Error('--vault-root is required');
}
if (!pluginId) {
  throw new Error('--plugin-id is required');
}

const mode = getBooleanOption(options, 'run', false)
  ? 'run'
  : getBooleanOption(options, 'dry-run', false)
    ? 'dry-run'
    : getStringOption(options, 'mode', 'dry-run').trim().toLowerCase();
if (!['dry-run', 'run'].includes(mode)) {
  throw new Error('--mode must be dry-run or run');
}

const platform = normalizePlatform(getStringOption(options, 'platform', 'auto'));
const toolRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const jobPath = path.resolve(jobPathRaw);
const statePlanPath = path.resolve(statePlanRaw);
const vaultRoot = path.resolve(vaultRootRaw);
const snapshotDir = path.resolve(getStringOption(options, 'snapshot-dir', '.obsidian-debug/state-matrix/plugin-reset'));
const outputRoot = path.resolve(getStringOption(options, 'output-root', '.obsidian-debug/state-matrix'));
const outputPath = path.resolve(getStringOption(options, 'output', path.join(outputRoot, 'state-matrix.json')));

function buildCommand({ phase, summary, executable, args, cwd = '' }) {
  return {
    phase,
    summary,
    executable,
    args,
    cwd: cwd || null,
    platform,
    rendered: renderExplicitCommand({ executable, args, platform }),
  };
}

function buildPlan() {
  const resetScript = path.join(toolRoot, 'scripts', 'obsidian_debug_reset_state.mjs');
  const jobScript = path.join(toolRoot, 'scripts', 'obsidian_debug_job.mjs');
  const cleanOutputDir = path.join(outputRoot, 'clean-state');
  const restoredOutputDir = path.join(outputRoot, 'restored-state');
  const commonStateArgs = [
    '--state-plan',
    statePlanPath,
    '--vault-root',
    vaultRoot,
    '--plugin-id',
    pluginId,
    '--snapshot-dir',
    snapshotDir,
  ];
  const jobMode = mode === 'run' ? 'run' : 'dry-run';

  const cleanStateCommands = [
    buildCommand({
      phase: 'preview-reset',
      summary: 'Preview the plugin-local reset plan before mutating state.',
      executable: 'node',
      args: [resetScript, '--mode', 'preview', ...commonStateArgs],
    }),
    buildCommand({
      phase: 'reset-state',
      summary: 'Capture the current plugin-local state and reset to a clean slate.',
      executable: 'node',
      args: [resetScript, '--mode', 'reset', ...commonStateArgs],
    }),
    buildCommand({
      phase: 'run-clean-state',
      summary: 'Run the configured debug job against clean plugin-local state.',
      executable: 'node',
      args: [jobScript, '--job', jobPath, '--platform', platform, '--mode', jobMode, '--output-dir', cleanOutputDir],
    }),
    buildCommand({
      phase: 'restore-state',
      summary: 'Restore the pre-reset plugin-local state from the captured snapshot.',
      executable: 'node',
      args: [resetScript, '--mode', 'restore', '--snapshot-dir', snapshotDir],
    }),
  ];

  const restoredStateCommands = [
    buildCommand({
      phase: 'run-restored-state',
      summary: 'Run the same debug job after the original plugin-local state has been restored.',
      executable: 'node',
      args: [jobScript, '--job', jobPath, '--platform', platform, '--mode', jobMode, '--output-dir', restoredOutputDir],
    }),
  ];

  return {
    generatedAt: nowIso(),
    mode,
    platform,
    jobPath,
    statePlanPath,
    vaultRoot,
    pluginId,
    snapshotDir,
    outputRoot,
    cases: [
      {
        id: 'clean-state',
        label: 'Clean state',
        outputDir: cleanOutputDir,
        commands: cleanStateCommands,
      },
      {
        id: 'restored-state',
        label: 'Restored state',
        outputDir: restoredOutputDir,
        commands: restoredStateCommands,
      },
    ],
  };
}

function runCommand(command) {
  return new Promise((resolve, reject) => {
    console.error(`\n== ${command.phase} ==`);
    console.error(command.rendered);
    const child = spawn(command.executable, command.args, {
      cwd: command.cwd || undefined,
      shell: false,
      windowsHide: true,
      stdio: 'inherit',
    });
    child.on('error', reject);
    child.on('close', (code) => resolve(code ?? 0));
  });
}

async function executeCommand(command) {
  const startedAt = nowIso();
  const exitCode = await runCommand(command);
  return {
    phase: command.phase,
    summary: command.summary,
    rendered: command.rendered,
    startedAt,
    finishedAt: nowIso(),
    exitCode,
  };
}

async function executePlan(plan) {
  const result = {
    ...plan,
    executedCases: [],
    status: 'pass',
  };

  const cleanCase = plan.cases[0];
  const restoredCase = plan.cases[1];

  const cleanExecuted = [];
  let cleanFailure = null;
  try {
    cleanExecuted.push(await executeCommand(cleanCase.commands[0]));
    const resetResult = await executeCommand(cleanCase.commands[1]);
    cleanExecuted.push(resetResult);
    if (resetResult.exitCode !== 0) {
      cleanFailure = new Error(`${cleanCase.commands[1].phase} failed with exit code ${resetResult.exitCode}`);
      throw cleanFailure;
    }

    const runResult = await executeCommand(cleanCase.commands[2]);
    cleanExecuted.push(runResult);
    if (runResult.exitCode !== 0) {
      cleanFailure = new Error(`${cleanCase.commands[2].phase} failed with exit code ${runResult.exitCode}`);
      throw cleanFailure;
    }
  } finally {
    const restoreResult = await executeCommand(cleanCase.commands[3]);
    cleanExecuted.push(restoreResult);
    if (restoreResult.exitCode !== 0 && !cleanFailure) {
      cleanFailure = new Error(`${cleanCase.commands[3].phase} failed with exit code ${restoreResult.exitCode}`);
    }
  }

  result.executedCases.push({
    id: cleanCase.id,
    label: cleanCase.label,
    outputDir: cleanCase.outputDir,
    commands: cleanExecuted,
    status: cleanFailure ? 'fail' : 'pass',
  });

  if (cleanFailure) {
    result.status = 'fail';
    throw Object.assign(cleanFailure, { planResult: result });
  }

  const restoredExecuted = [];
  const restoredResult = await executeCommand(restoredCase.commands[0]);
  restoredExecuted.push(restoredResult);
  const restoredFailure = restoredResult.exitCode !== 0
    ? new Error(`${restoredCase.commands[0].phase} failed with exit code ${restoredResult.exitCode}`)
    : null;
  result.executedCases.push({
    id: restoredCase.id,
    label: restoredCase.label,
    outputDir: restoredCase.outputDir,
    commands: restoredExecuted,
    status: restoredFailure ? 'fail' : 'pass',
  });

  if (restoredFailure) {
    result.status = 'fail';
    throw Object.assign(restoredFailure, { planResult: result });
  }

  return result;
}

let finalReport = buildPlan();
await ensureParentDirectory(outputPath);
await fs.writeFile(outputPath, `${JSON.stringify(finalReport, null, 2)}\n`, 'utf8');
console.log(JSON.stringify(finalReport, null, 2));

if (mode === 'run') {
  try {
    finalReport = await executePlan(finalReport);
  } catch (error) {
    finalReport = error.planResult ?? {
      ...finalReport,
      status: 'fail',
    };
    await fs.writeFile(outputPath, `${JSON.stringify(finalReport, null, 2)}\n`, 'utf8');
    console.log(JSON.stringify(finalReport, null, 2));
    throw error;
  }

  await fs.writeFile(outputPath, `${JSON.stringify(finalReport, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify(finalReport, null, 2));
}
