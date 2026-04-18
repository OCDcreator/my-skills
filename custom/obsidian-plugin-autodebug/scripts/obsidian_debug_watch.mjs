import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import {
  ensureParentDirectory,
  getBooleanOption,
  getNumberOption,
  getStringOption,
  nowIso,
  parseArgs,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
const watchRootsRaw = getStringOption(options, 'watch-roots', '').trim();
const commandTemplate = getStringOption(options, 'command', '').trim();
const workingDirectory = path.resolve(getStringOption(options, 'cwd', process.cwd()));
const rootOutput = path.resolve(getStringOption(options, 'root-output', '.obsidian-debug/watch-runs'));
const summaryPath = path.resolve(getStringOption(options, 'summary', path.join(rootOutput, 'watch-summary.json')));
const debounceMs = Math.max(50, getNumberOption(options, 'debounce-ms', 800));
const pollMs = Math.max(50, getNumberOption(options, 'poll-ms', 500));
const maxRuns = Math.max(0, getNumberOption(options, 'max-runs', 0));
const timeoutMs = Math.max(0, getNumberOption(options, 'timeout-ms', 0));
const onceOnStart = getBooleanOption(options, 'once-on-start', false);
const label = getStringOption(options, 'label', 'default');
const mode = getStringOption(options, 'mode', 'watch');
const excludeNeedles = getStringOption(options, 'exclude', '')
  .split('|')
  .map((entry) => entry.trim())
  .filter((entry) => entry.length > 0);
const watchRoots = watchRootsRaw
  .split('|')
  .map((entry) => entry.trim())
  .filter((entry) => entry.length > 0)
  .map((entry) => path.resolve(workingDirectory, entry));

if (watchRoots.length === 0) {
  throw new Error('--watch-roots is required');
}

if (!commandTemplate) {
  throw new Error('--command is required');
}

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function shouldExclude(targetPath) {
  return excludeNeedles.some((needle) => targetPath.includes(needle));
}

async function statOrNull(targetPath) {
  try {
    return await fs.stat(targetPath);
  } catch {
    return null;
  }
}

async function collectSnapshotEntries(targetPath, entries) {
  if (shouldExclude(targetPath)) {
    return;
  }

  const stat = await statOrNull(targetPath);
  if (!stat) {
    return;
  }

  const normalizedPath = path.resolve(targetPath);
  if (stat.isDirectory()) {
    entries.set(normalizedPath, {
      type: 'directory',
      mtimeMs: stat.mtimeMs,
      size: 0,
    });
    const children = await fs.readdir(normalizedPath, { withFileTypes: true });
    for (const child of children.sort((left, right) => left.name.localeCompare(right.name))) {
      if (child.isSymbolicLink()) {
        continue;
      }
      await collectSnapshotEntries(path.join(normalizedPath, child.name), entries);
    }
    return;
  }

  entries.set(normalizedPath, {
    type: stat.isFile() ? 'file' : 'other',
    mtimeMs: stat.mtimeMs,
    size: stat.size,
  });
}

async function captureSnapshot() {
  const entries = new Map();
  for (const watchRoot of watchRoots) {
    await collectSnapshotEntries(watchRoot, entries);
  }
  return entries;
}

function compareSnapshots(previousSnapshot, nextSnapshot) {
  const added = [];
  const removed = [];
  const changed = [];

  for (const [filePath, nextEntry] of nextSnapshot.entries()) {
    const previousEntry = previousSnapshot.get(filePath);
    if (!previousEntry) {
      added.push(filePath);
      continue;
    }

    if (
      previousEntry.type !== nextEntry.type
      || previousEntry.size !== nextEntry.size
      || previousEntry.mtimeMs !== nextEntry.mtimeMs
    ) {
      changed.push(filePath);
    }
  }

  for (const filePath of previousSnapshot.keys()) {
    if (!nextSnapshot.has(filePath)) {
      removed.push(filePath);
    }
  }

  return {
    added,
    removed,
    changed,
    changedPaths: [...new Set([...added, ...changed, ...removed])].sort((left, right) => left.localeCompare(right)),
  };
}

function buildCommand(command, outputDir, runNumber) {
  return command
    .replaceAll('{{outputDir}}', outputDir)
    .replaceAll('{{run}}', String(runNumber));
}

function runShellCommand(command, cwd) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, {
      cwd,
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

async function writeSummary(summary) {
  await ensureParentDirectory(summaryPath);
  await fs.writeFile(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
}

await fs.mkdir(rootOutput, { recursive: true });

let previousSnapshot = await captureSnapshot();
const startedAtIso = nowIso();
const startedAtMs = Date.now();
let runCount = 0;
let timedOut = false;
let pending = onceOnStart;
let lastChangeAtMs = onceOnStart ? Date.now() : 0;
const pendingPaths = new Set(onceOnStart ? ['[initial-run]'] : []);
const watchEvents = [];
const runsData = [];

while (true) {
  if (timeoutMs > 0 && Date.now() - startedAtMs >= timeoutMs) {
    timedOut = true;
    break;
  }

  await sleep(pollMs);

  const nextSnapshot = await captureSnapshot();
  const diff = compareSnapshots(previousSnapshot, nextSnapshot);
  previousSnapshot = nextSnapshot;

  if (diff.changedPaths.length > 0) {
    lastChangeAtMs = Date.now();
    pending = true;
    for (const changedPath of diff.changedPaths) {
      pendingPaths.add(changedPath);
    }
    watchEvents.push({
      detectedAt: nowIso(),
      changedPaths: diff.changedPaths,
      added: diff.added,
      removed: diff.removed,
      changed: diff.changed,
    });
  }

  if (!pending || Date.now() - lastChangeAtMs < debounceMs) {
    continue;
  }

  runCount += 1;
  const runOutput = path.join(rootOutput, `run-${String(runCount).padStart(2, '0')}`);
  await fs.rm(runOutput, { recursive: true, force: true });
  await fs.mkdir(runOutput, { recursive: true });

  const changedPaths = [...pendingPaths];
  pending = false;
  pendingPaths.clear();

  const command = buildCommand(commandTemplate, runOutput, runCount);
  const startedAt = nowIso();
  const result = await runShellCommand(command, workingDirectory);
  const finishedAt = nowIso();

  const runData = {
    run: runCount,
    outputDir: runOutput,
    command,
    startedAt,
    finishedAt,
    exitCode: result.exitCode,
    changedPaths,
  };
  runsData.push(runData);

  await fs.writeFile(
    path.join(runOutput, 'watch-run.json'),
    `${JSON.stringify(runData, null, 2)}\n`,
    'utf8',
  );

  const summary = {
    generatedAt: nowIso(),
    startedAt: startedAtIso,
    label,
    mode,
    workingDirectory,
    watchRoots,
    excludeNeedles,
    rootOutput,
    summaryPath,
    debounceMs,
    pollMs,
    timeoutMs,
    maxRuns,
    timedOut,
    onceOnStart,
    watchEvents,
    runsData,
  };
  await writeSummary(summary);

  if (maxRuns > 0 && runCount >= maxRuns) {
    break;
  }
}

const summary = {
  generatedAt: nowIso(),
  startedAt: startedAtIso,
  label,
  mode,
  workingDirectory,
  watchRoots,
  excludeNeedles,
  rootOutput,
  summaryPath,
  debounceMs,
  pollMs,
  timeoutMs,
  maxRuns,
  timedOut,
  onceOnStart,
  watchEvents,
  runsData,
};

await writeSummary(summary);
console.log(JSON.stringify(summary, null, 2));
