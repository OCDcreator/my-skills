import fs from 'node:fs/promises';
import path from 'node:path';
import {
  ensureParentDirectory,
  getStringOption,
  hasHelpOption,
  nowIso,
  parseArgs,
  printHelpAndExit,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
if (hasHelpOption(options)) {
  printHelpAndExit(`
Usage: node scripts/obsidian_debug_reset_state.mjs --mode <preview|reset|restore> [options]

Modes:
  preview    Resolve targets without deleting anything.
  reset      Snapshot then clear/recreate declared plugin-local state.
  restore    Restore a previous snapshot.

Options:
  --vault-root <path>                Vault root for plugin-local paths.
  --plugin-id <id>                   Plugin id under .obsidian/plugins.
  --plugin-dir <path>                Explicit plugin directory override.
  --state-plan <path>                JSON reset plan.
  --targets <a|b>                    Pipe-separated target paths.
  --snapshot-dir <dir>               Snapshot directory.
`);
}

const mode = getStringOption(options, 'mode', '').trim().toLowerCase();
if (!['preview', 'reset', 'restore'].includes(mode)) {
  throw new Error('--mode must be preview, reset, or restore');
}

const workingDirectory = process.cwd();
const vaultRootRaw = getStringOption(options, 'vault-root', '').trim();
const pluginId = getStringOption(options, 'plugin-id', '').trim();
const pluginDirRaw = getStringOption(options, 'plugin-dir', '').trim();
const snapshotDir = path.resolve(getStringOption(options, 'snapshot-dir', '.obsidian-debug/state-reset'));
const statePlanPath = getStringOption(options, 'state-plan', '').trim();
const targetsRaw = getStringOption(options, 'targets', '').trim();
const recreateFilesRaw = getStringOption(options, 'recreate-files', '').trim();
const recreateDirsRaw = getStringOption(options, 'recreate-dirs', '').trim();
const manifestPath = path.join(snapshotDir, 'manifest.json');

function splitPipeList(value) {
  return value
    .split('|')
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
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

const resolvedVaultRoot = vaultRootRaw ? path.resolve(workingDirectory, vaultRootRaw) : '';
const resolvedPluginDir = pluginDirRaw
  ? path.resolve(workingDirectory, pluginDirRaw)
  : resolvedVaultRoot && pluginId
    ? path.resolve(resolvedVaultRoot, '.obsidian', 'plugins', pluginId)
    : '';
const context = {
  cwd: workingDirectory,
  vaultRoot: resolvedVaultRoot,
  pluginId,
  pluginDir: resolvedPluginDir,
};

function resolveTemplate(value) {
  return String(value).replace(/\{(\w+)\}/g, (_, key) => context[key] ?? '');
}

function resolveManagedPaths(paths) {
  return [...new Set(paths
    .map((entry) => resolveTemplate(entry))
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0)
    .map((entry) => path.resolve(workingDirectory, entry)))];
}

function assertSafeManagedPath(targetPath) {
  const resolvedTarget = path.resolve(targetPath);
  if (resolvedTarget === path.parse(resolvedTarget).root) {
    throw new Error(`Refusing to manage filesystem root: ${resolvedTarget}`);
  }
  const protectedPaths = [
    context.vaultRoot,
    context.pluginDir,
    context.vaultRoot ? path.join(context.vaultRoot, '.obsidian') : '',
  ].filter((entry) => entry.length > 0);
  if (protectedPaths.includes(resolvedTarget)) {
    throw new Error(`Refusing to manage protected root path directly: ${resolvedTarget}`);
  }
}

async function statOrNull(targetPath) {
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

const planDocument = statePlanPath
  ? await readJsonOrNull(path.resolve(workingDirectory, statePlanPath))
  : null;

if (statePlanPath && !planDocument) {
  throw new Error(`Unable to read state plan: ${statePlanPath}`);
}

const resolvedTargets = resolveManagedPaths([
  ...(planDocument?.targets ?? []),
  ...splitPipeList(targetsRaw),
]);
const recreateFiles = resolveManagedPaths([
  ...(planDocument?.recreateFiles ?? []),
  ...splitPipeList(recreateFilesRaw),
]);
const recreateDirs = resolveManagedPaths([
  ...(planDocument?.recreateDirs ?? []),
  ...splitPipeList(recreateDirsRaw),
]);
const allManagedTargets = [...new Set([...resolvedTargets, ...recreateFiles, ...recreateDirs])];

for (const targetPath of allManagedTargets) {
  assertSafeManagedPath(targetPath);
}

if (mode !== 'restore' && allManagedTargets.length === 0) {
  throw new Error('At least one target, recreate-file, recreate-dir, or state plan target is required');
}

if (mode === 'preview') {
  const preview = {
    generatedAt: nowIso(),
    mode,
    snapshotDir,
    statePlanPath: statePlanPath ? path.resolve(workingDirectory, statePlanPath) : null,
    description: planDocument?.description ?? null,
    context,
    targets: allManagedTargets,
    recreateFiles,
    recreateDirs,
  };
  console.log(JSON.stringify(preview, null, 2));
} else if (mode === 'reset') {
  await fs.rm(snapshotDir, { recursive: true, force: true });
  await fs.mkdir(snapshotDir, { recursive: true });

  const entries = [];
  for (let index = 0; index < allManagedTargets.length; index += 1) {
    const targetPath = allManagedTargets[index];
    const stat = await statOrNull(targetPath);
    if (!stat) {
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

  for (const targetPath of allManagedTargets) {
    await removeTarget(targetPath);
  }

  for (const directoryPath of recreateDirs) {
    await fs.mkdir(directoryPath, { recursive: true });
  }

  for (const filePath of recreateFiles) {
    await ensureParentDirectory(filePath);
    await fs.writeFile(filePath, '', 'utf8');
  }

  const manifest = {
    generatedAt: nowIso(),
    mode,
    snapshotDir,
    statePlanPath: statePlanPath ? path.resolve(workingDirectory, statePlanPath) : null,
    description: planDocument?.description ?? null,
    context,
    targets: allManagedTargets,
    recreateFiles,
    recreateDirs,
    entries,
  };
  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');

  const report = {
    generatedAt: nowIso(),
    mode,
    snapshotDir,
    manifestPath,
    targetCount: allManagedTargets.length,
    recreated: {
      files: recreateFiles,
      dirs: recreateDirs,
    },
  };
  console.log(JSON.stringify(report, null, 2));
} else {
  const manifest = await readJsonOrNull(manifestPath);
  if (!manifest) {
    throw new Error(`Unable to read reset manifest: ${manifestPath}`);
  }

  const restored = [];
  for (const entry of manifest.entries ?? []) {
    await removeTarget(entry.originalPath);
    if (!entry.exists || !entry.snapshotRelativePath) {
      restored.push({
        originalPath: entry.originalPath,
        restored: false,
        reason: 'missing-in-snapshot',
      });
      continue;
    }

    const snapshotPath = path.join(snapshotDir, entry.snapshotRelativePath);
    await ensureParentDirectory(entry.originalPath);
    await fs.cp(snapshotPath, entry.originalPath, { recursive: true, force: true });
    restored.push({
      originalPath: entry.originalPath,
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
