import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import {
  ensureParentDirectory,
  getNumberOption,
  getStringOption,
  nowIso,
  parseArgs,
  resolveTarget,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
const repoDir = path.resolve(getStringOption(options, 'repo-dir', process.cwd()));
const testVaultPluginDir = getStringOption(options, 'test-vault-plugin-dir', '').trim();
const expectedPluginId = getStringOption(options, 'plugin-id', '').trim();
const obsidianCommand = getStringOption(options, 'obsidian-command', 'obsidian').trim();
const cdpHost = getStringOption(options, 'cdp-host', '127.0.0.1');
const cdpPort = getNumberOption(options, 'cdp-port', 9222);
const cdpTargetTitleContains = getStringOption(options, 'cdp-target-title-contains', '');
const outputPath = getStringOption(options, 'output', '').trim();

function statusRank(status) {
  return { pass: 0, info: 1, warn: 2, fail: 3 }[status] ?? 3;
}

function runProcess(command, args, timeoutMs = 5000) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    let settled = false;
    const timeout = setTimeout(() => {
      if (!settled) {
        settled = true;
        child.kill();
        resolve({ ok: false, exitCode: null, stdout, stderr, timedOut: true });
      }
    }, timeoutMs);

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    child.on('error', (error) => {
      if (!settled) {
        settled = true;
        clearTimeout(timeout);
        resolve({ ok: false, exitCode: null, stdout, stderr: `${stderr}${error.message}`, timedOut: false });
      }
    });
    child.on('close', (code) => {
      if (!settled) {
        settled = true;
        clearTimeout(timeout);
        resolve({ ok: code === 0, exitCode: code, stdout, stderr, timedOut: false });
      }
    });
  });
}

async function readJsonOrNull(filePath) {
  try {
    return JSON.parse((await fs.readFile(filePath, 'utf8')).replace(/^\uFEFF/, ''));
  } catch {
    return null;
  }
}

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

function check(status, id, detail, data = {}) {
  return { id, status, detail, ...data };
}

const checks = [];

const nodeMajor = Number.parseInt(process.versions.node.split('.')[0] ?? '0', 10);
checks.push(
  check(
    nodeMajor >= 18 ? 'pass' : 'fail',
    'node-version',
    `Node.js ${process.versions.node}`,
    { minimum: '18.0.0' },
  ),
);

const manifestPath = path.join(repoDir, 'manifest.json');
const packagePath = path.join(repoDir, 'package.json');
const manifest = await readJsonOrNull(manifestPath);
const packageJson = await readJsonOrNull(packagePath);

checks.push(
  manifest
    ? check('pass', 'repo-manifest', `Found manifest.json with id ${manifest.id ?? '(missing id)'}`, { path: manifestPath })
    : check('fail', 'repo-manifest', 'manifest.json was not found or is invalid', { path: manifestPath }),
);
checks.push(
  packageJson
    ? check('pass', 'repo-package', `Found package.json${packageJson.scripts?.build ? ' with build script' : ''}`, { path: packagePath })
    : check('warn', 'repo-package', 'package.json was not found or is invalid', { path: packagePath }),
);

if (manifest && expectedPluginId) {
  checks.push(
    check(
      manifest.id === expectedPluginId ? 'pass' : 'fail',
      'plugin-id-match',
      `manifest id ${manifest.id ?? '(missing)'} ${manifest.id === expectedPluginId ? 'matches' : 'does not match'} ${expectedPluginId}`,
      { manifestId: manifest.id ?? null, expectedPluginId },
    ),
  );
}

const distMainPath = path.join(repoDir, 'dist', 'main.js');
checks.push(
  (await exists(distMainPath))
    ? check('pass', 'dist-main', 'Found dist/main.js', { path: distMainPath })
    : check('warn', 'dist-main', 'dist/main.js is missing; run the plugin build before deploy/reload', { path: distMainPath }),
);

if (testVaultPluginDir) {
  const vaultDir = path.resolve(testVaultPluginDir);
  const vaultManifestPath = path.join(vaultDir, 'manifest.json');
  const vaultMainPath = path.join(vaultDir, 'main.js');
  const vaultStylesPath = path.join(vaultDir, 'styles.css');
  const vaultManifest = await readJsonOrNull(vaultManifestPath);

  checks.push(
    (await exists(vaultDir))
      ? check('pass', 'test-vault-plugin-dir', 'Test vault plugin directory exists', { path: vaultDir })
      : check('fail', 'test-vault-plugin-dir', 'Test vault plugin directory does not exist', { path: vaultDir }),
  );
  checks.push(
    vaultManifest
      ? check('pass', 'test-vault-manifest', `Test vault manifest id ${vaultManifest.id ?? '(missing id)'}`, { path: vaultManifestPath })
      : check('warn', 'test-vault-manifest', 'Test vault manifest.json is missing or invalid', { path: vaultManifestPath }),
  );
  checks.push(
    (await exists(vaultMainPath))
      ? check('pass', 'test-vault-main', 'Test vault main.js exists', { path: vaultMainPath })
      : check('warn', 'test-vault-main', 'Test vault main.js is missing', { path: vaultMainPath }),
  );
  checks.push(
    (await exists(vaultStylesPath))
      ? check('pass', 'test-vault-styles', 'Test vault styles.css exists', { path: vaultStylesPath })
      : check('info', 'test-vault-styles', 'Test vault styles.css is missing; this is OK for plugins without CSS', { path: vaultStylesPath }),
  );
}

const obsidianHelp = await runProcess(obsidianCommand, ['help'], 7000);
const helpText = `${obsidianHelp.stdout}\n${obsidianHelp.stderr}`;
checks.push(
  obsidianHelp.ok
    ? check(
        helpText.includes('Developer:') || helpText.includes('dev:console') ? 'pass' : 'warn',
        'obsidian-cli',
        helpText.includes('Developer:') || helpText.includes('dev:console')
          ? 'Obsidian CLI is available with developer commands'
          : 'Obsidian command ran, but developer commands were not detected',
        { command: obsidianCommand, exitCode: obsidianHelp.exitCode },
      )
    : check(
        'warn',
        'obsidian-cli',
        obsidianHelp.timedOut
          ? 'Obsidian command timed out while checking help'
          : `Obsidian command failed: ${obsidianHelp.stderr.trim() || 'not available'}`,
        { command: obsidianCommand, exitCode: obsidianHelp.exitCode, timedOut: obsidianHelp.timedOut },
      ),
);

try {
  const target = await resolveTarget({
    host: cdpHost,
    port: cdpPort,
    targetTitleContains: cdpTargetTitleContains,
  });
  checks.push(
    check('pass', 'cdp-target', `CDP target is reachable: ${target.title || target.url}`, {
      host: cdpHost,
      port: cdpPort,
      title: target.title ?? null,
      url: target.url ?? null,
    }),
  );
} catch (error) {
  checks.push(
    check('warn', 'cdp-target', `CDP target is not reachable: ${error.message}`, {
      host: cdpHost,
      port: cdpPort,
      targetTitleContains: cdpTargetTitleContains || null,
    }),
  );
}

const status = checks.reduce((current, entry) => (statusRank(entry.status) > statusRank(current) ? entry.status : current), 'pass');
const report = {
  generatedAt: nowIso(),
  status,
  repoDir,
  pluginId: expectedPluginId || manifest?.id || null,
  testVaultPluginDir: testVaultPluginDir ? path.resolve(testVaultPluginDir) : null,
  obsidianCommand,
  cdp: {
    host: cdpHost,
    port: cdpPort,
    targetTitleContains: cdpTargetTitleContains || null,
  },
  checks,
};

if (outputPath) {
  const resolvedOutput = path.resolve(outputPath);
  await ensureParentDirectory(resolvedOutput);
  await fs.writeFile(resolvedOutput, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
}

console.log(JSON.stringify(report, null, 2));
