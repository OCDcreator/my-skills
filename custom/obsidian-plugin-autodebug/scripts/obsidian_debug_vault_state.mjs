import fs from 'node:fs/promises';
import path from 'node:path';
import {
  ensureParentDirectory,
  getBooleanOption,
  getStringOption,
  nowIso,
  parseArgs,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
const mode = getStringOption(options, 'mode', '').trim().toLowerCase();
if (mode !== 'snapshot' && mode !== 'restore') {
  throw new Error('--mode must be snapshot or restore');
}

const snapshotDir = path.resolve(getStringOption(options, 'snapshot-dir', '.obsidian-debug/vault-state-snapshot'));
const targetsRaw = getStringOption(options, 'targets', '').trim();
const targets = targetsRaw
  .split('|')
  .map((entry) => entry.trim())
  .filter((entry) => entry.length > 0)
  .map((entry) => path.resolve(entry));

const allowMissing = getBooleanOption(options, 'allow-missing', true);
const manifestPath = path.join(snapshotDir, 'manifest.json');

if (mode === 'snapshot' && targets.length === 0) {
  throw new Error('--targets is required for snapshot mode');
}

async function pathStatOrNull(targetPath) {
  try {
    return await fs.stat(targetPath);
  } catch {
    return null;
  }
}

async function removeTarget(targetPath) {
  await fs.rm(targetPath, { recursive: true, force: true });
}

async function copyIntoSnapshot(targetPath, relativeName) {
  const destination = path.join(snapshotDir, relativeName);
  await ensureParentDirectory(destination);
  await fs.cp(targetPath, destination, { recursive: true, force: true });
  return destination;
}

if (mode === 'snapshot') {
  await fs.rm(snapshotDir, { recursive: true, force: true });
  await fs.mkdir(snapshotDir, { recursive: true });

  const entries = [];
  for (let index = 0; index < targets.length; index += 1) {
    const targetPath = targets[index];
    const stat = await pathStatOrNull(targetPath);
    if (!stat) {
      if (!allowMissing) {
        throw new Error(`Snapshot target does not exist: ${targetPath}`);
      }

      entries.push({
        originalPath: targetPath,
        exists: false,
        type: null,
        snapshotRelativePath: null,
      });
      continue;
    }

    const snapshotRelativePath = `${String(index + 1).padStart(2, '0')}__${path.basename(targetPath)}`;
    await copyIntoSnapshot(targetPath, snapshotRelativePath);
    entries.push({
      originalPath: targetPath,
      exists: true,
      type: stat.isDirectory() ? 'directory' : 'file',
      snapshotRelativePath,
    });
  }

  const manifest = {
    generatedAt: nowIso(),
    mode,
    snapshotDir,
    allowMissing,
    entries,
  };
  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify(manifest, null, 2));
} else {
  const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'));
  const restored = [];

  for (const entry of manifest.entries ?? []) {
    const targetPath = entry.originalPath;
    await removeTarget(targetPath);

    if (!entry.exists || !entry.snapshotRelativePath) {
      restored.push({
        originalPath: targetPath,
        restored: false,
        reason: 'missing-in-snapshot',
      });
      continue;
    }

    const snapshotPath = path.join(snapshotDir, entry.snapshotRelativePath);
    await ensureParentDirectory(targetPath);
    await fs.cp(snapshotPath, targetPath, { recursive: true, force: true });
    restored.push({
      originalPath: targetPath,
      restored: true,
      snapshotPath,
    });
  }

  const report = {
    generatedAt: nowIso(),
    mode,
    snapshotDir,
    restored,
  };
  console.log(JSON.stringify(report, null, 2));
}
