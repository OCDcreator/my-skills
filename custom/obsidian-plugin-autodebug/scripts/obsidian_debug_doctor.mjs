import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import {
  ensureParentDirectory,
  getBooleanOption,
  getNumberOption,
  getStringOption,
  getWebSocketSupportDetail,
  hasGlobalWebSocket,
  nowIso,
  parseArgs,
  resolveTarget,
} from './obsidian_cdp_common.mjs';
import {
  buildCommandScript,
  normalizePlatform,
  resolveTemplateCommand,
  scriptExtension,
} from './obsidian_debug_command_templates.mjs';
import {
  detectRepoRuntime,
  formatCommandTokens,
  readJsonFileOrNull,
} from './obsidian_debug_repo_runtime.mjs';
import { detectPlaywrightSupport } from './obsidian_debug_playwright_support.mjs';

const options = parseArgs(process.argv.slice(2));
const repoDir = path.resolve(getStringOption(options, 'repo-dir', process.cwd()));
const testVaultPluginDir = getStringOption(options, 'test-vault-plugin-dir', '').trim();
const expectedPluginId = getStringOption(options, 'plugin-id', '').trim();
const obsidianCommand = getStringOption(options, 'obsidian-command', 'obsidian').trim();
const vaultName = getStringOption(options, 'vault-name', '').trim();
const cdpHost = getStringOption(options, 'cdp-host', '127.0.0.1');
const cdpPort = getNumberOption(options, 'cdp-port', 9222);
const cdpTargetTitleContains = getStringOption(options, 'cdp-target-title-contains', '');
const playwrightModuleName = getStringOption(options, 'playwright-module', '').trim();
const outputPath = getStringOption(options, 'output', '').trim();
const platform = normalizePlatform(getStringOption(options, 'platform', 'auto'));
const fixRequested = getBooleanOption(options, 'fix', false);
const toolRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const defaultFixOutput = outputPath
  ? path.join(path.dirname(path.resolve(outputPath)), `doctor-fixes.${scriptExtension(platform)}`)
  : path.join(repoDir, '.obsidian-debug', `doctor-fixes.${scriptExtension(platform)}`);
const defaultBootstrapOutput = outputPath
  ? path.join(path.dirname(path.resolve(outputPath)), 'bootstrap-plugin.json')
  : path.join(repoDir, '.obsidian-debug', 'bootstrap-plugin.json');
const fixOutputPath = fixRequested
  ? path.resolve(getStringOption(options, 'fix-output', defaultFixOutput))
  : '';

const buildSnippet = "import fs from 'node:fs/promises'; import path from 'node:path'; const repo=process.argv[1]; const target=process.argv[2]; await fs.mkdir(target,{recursive:true}); for (const name of ['main.js','manifest.json','styles.css']) { const src=path.join(repo,'dist',name); try { await fs.copyFile(src,path.join(target,name)); } catch (error) { if (error?.code !== 'ENOENT') throw error; } }";
const mkdirSnippet = "import fs from 'node:fs/promises'; await fs.mkdir(process.argv[1], { recursive: true });";
const cdpProbeSnippet = "const response = await fetch(`http://${process.argv[1]}:${process.argv[2]}/json/list`); if (!response.ok) { throw new Error(`HTTP ${response.status}`); } console.log(await response.text());";

const commandContext = {
  toolRoot,
  repoDir,
  testVaultPluginDir: testVaultPluginDir ? path.resolve(testVaultPluginDir) : '',
  pluginId: expectedPluginId,
  vaultName,
  obsidianCommand,
  cdpHost,
  cdpPort,
  cdpTargetTitleContains,
  outputPath: outputPath ? path.resolve(outputPath) : '',
  bootstrapOutputPath: path.resolve(defaultBootstrapOutput),
  fixOutputPath,
};

function statusRank(status) {
  return { pass: 0, info: 1, warn: 2, fail: 3 }[status] ?? 3;
}

function dedupeCommands(commands) {
  const seen = new Set();
  return commands.filter((command) => {
    const key = JSON.stringify([
      command.id ?? null,
      command.label ?? null,
      command.rendered ?? null,
      command.cwd ?? null,
    ]);
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function resolveFixes(fixSpecs = []) {
  return fixSpecs
    .map((fixSpec, index) => resolveTemplateCommand(
      {
        id: fixSpec.id ?? `fix-${index + 1}`,
        ...fixSpec,
      },
      {
        variables: commandContext,
        platform,
      },
    ))
    .filter((entry) => entry.rendered || entry.summary);
}

function check(status, id, category, detail, data = {}, fixSpecs = []) {
  return {
    id,
    category,
    status,
    detail,
    fixes: resolveFixes(fixSpecs),
    ...data,
  };
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

function buildVaultScopedArgs(command, args = []) {
  return [
    ...(vaultName ? [`vault=${vaultName}`] : []),
    command,
    ...args,
  ];
}

function parsePluginList(text) {
  try {
    const parsed = JSON.parse(String(text ?? '').replace(/^\uFEFF/, ''));
    if (Array.isArray(parsed)) {
      return parsed
        .map((entry) => ({
          id: typeof entry === 'string' ? entry : String(entry?.id ?? ''),
          version: typeof entry === 'object' && entry ? entry.version ?? null : null,
        }))
        .filter((entry) => entry.id.length > 0);
    }
  } catch {
    // Fall back to line parsing below.
  }

  return String(text ?? '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.toLowerCase().startsWith('error:'))
    .map((line) => ({
      id: line.split(/\s+/)[0],
      version: null,
    }))
    .filter((entry) => entry.id.length > 0);
}

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

const checks = [];
const nodeMajor = Number.parseInt(process.versions.node.split('.')[0] ?? '0', 10);
checks.push(
  check(
    nodeMajor >= 18 ? 'pass' : 'fail',
    'node-version',
    'runtime',
    `Node.js ${process.versions.node}`,
    { minimum: '18.0.0' },
  ),
);
checks.push(
  check(
    hasGlobalWebSocket() ? 'pass' : 'warn',
    'node-websocket-global',
    'runtime',
    getWebSocketSupportDetail(),
    {
      nodeVersion: process.versions.node,
      websocketType: typeof globalThis.WebSocket,
    },
  ),
);

const manifestPath = path.join(repoDir, 'manifest.json');
const packagePath = path.join(repoDir, 'package.json');
const distDir = path.join(repoDir, 'dist');
const distMainPath = path.join(distDir, 'main.js');
const distManifestPath = path.join(distDir, 'manifest.json');
const distStylesPath = path.join(distDir, 'styles.css');
const manifest = await readJsonFileOrNull(manifestPath);
const repoRuntime = await detectRepoRuntime({ repoDir });
const playwrightSupport = await detectPlaywrightSupport({
  repoDir,
  moduleName: playwrightModuleName,
});
const packageJson = repoRuntime.packageJson;
const buildScriptExists = repoRuntime.scripts.important.build.exists;
const inferredBuildCommand = repoRuntime.commands.build.available
  ? repoRuntime.commands.build.command
  : [];
const inferredBuildCommandText = formatCommandTokens(inferredBuildCommand);

const buildFixes = buildScriptExists && inferredBuildCommand.length > 0
  ? [
      {
        id: 'run-build',
        label: 'Build plugin output',
        summary: inferredBuildCommandText
          ? `Regenerate the deployable dist artifacts with ${inferredBuildCommandText} before retrying deploy/reload.`
          : 'Regenerate the deployable dist artifacts before retrying deploy/reload.',
        safety: 'writes-build-output',
        dryRunFriendly: false,
        executable: inferredBuildCommand[0],
        args: inferredBuildCommand.slice(1),
        cwd: '{{repoDir}}',
      },
    ]
  : [];
const deployFixes = testVaultPluginDir
  ? [
      {
        id: 'deploy-dist-artifacts',
        label: 'Copy dist artifacts into the test vault',
        summary: 'Creates the test vault plugin directory if needed and copies dist/main.js, dist/manifest.json, and dist/styles.css when present.',
        safety: 'writes-local-state',
        dryRunFriendly: false,
        executable: 'node',
        args: ['--input-type=module', '-e', buildSnippet, '{{repoDir}}', '{{testVaultPluginDir}}'],
        cwd: '{{repoDir}}',
      },
    ]
  : [];
const createTestVaultDirFixes = testVaultPluginDir
  ? [
      {
        id: 'create-test-vault-plugin-dir',
        label: 'Create the test vault plugin directory',
        summary: 'Creates the target plugin directory used by deploy and reload automation.',
        safety: 'writes-local-state',
        dryRunFriendly: false,
        executable: 'node',
        args: ['--input-type=module', '-e', mkdirSnippet, '{{testVaultPluginDir}}'],
      },
    ]
  : [];
const cdpProbeFixes = [
  {
    id: 'probe-cdp-targets',
    label: 'Probe CDP targets',
    summary: 'Lists the currently exposed CDP targets before retrying app launch or reload automation.',
    safety: 'read-only',
    dryRunFriendly: true,
    executable: 'node',
    args: ['--input-type=module', '-e', cdpProbeSnippet, '{{cdpHost}}', '{{cdpPort}}'],
  },
];
const bootstrapFixes = expectedPluginId && testVaultPluginDir
  ? [
      {
        id: 'bootstrap-plugin-discovery',
        label: 'Bootstrap fresh plugin discovery',
        summary: 'Disables restricted mode, reloads the target vault, restarts Obsidian only if needed, and enables the plugin once it becomes discoverable.',
        safety: 'writes-local-state',
        dryRunFriendly: false,
        executable: 'node',
        args: [
          '{{toolRoot}}/scripts/obsidian_debug_bootstrap_plugin.mjs',
          '--plugin-id',
          '{{pluginId}}',
          '--test-vault-plugin-dir',
          '{{testVaultPluginDir}}',
          '--obsidian-command',
          '{{obsidianCommand}}',
          ...(vaultName ? ['--vault-name', '{{vaultName}}'] : []),
          '--output',
          '{{bootstrapOutputPath}}',
        ],
      },
    ]
  : [];

checks.push(
  manifest
    ? check('pass', 'repo-manifest', 'repo', `Found manifest.json with id ${manifest.id ?? '(missing id)'}`, { path: manifestPath })
    : check('fail', 'repo-manifest', 'repo', 'manifest.json was not found or is invalid', { path: manifestPath }),
);
checks.push(
  packageJson
    ? check(
        'pass',
        'repo-package',
        'build',
        `Found package.json${repoRuntime.scripts.names.length > 0 ? ` with scripts: ${repoRuntime.scripts.names.join(', ')}` : ''}`,
        {
          path: packagePath,
          scripts: repoRuntime.scripts.names,
        },
      )
    : check('warn', 'repo-package', 'build', 'package.json was not found or is invalid', { path: packagePath }),
);
checks.push(
  buildScriptExists
    ? check(
        repoRuntime.commands.build.available ? 'pass' : 'warn',
        'build-script',
        'build',
        repoRuntime.commands.build.available
          ? `package.json defines scripts.build; inferred build command is ${repoRuntime.commands.build.rendered}`
          : `package.json defines scripts.build, but no runnable package-manager command was found: ${repoRuntime.commands.build.detail}`,
        {
          path: packagePath,
          inferredCommand: repoRuntime.commands.build.command,
          via: repoRuntime.commands.build.via,
        },
      )
    : check('warn', 'build-script', 'build', 'package.json is missing scripts.build; build fixes stay informational only', { path: packagePath }),
);
checks.push(
  repoRuntime.packageManagerField
    ? check(
        repoRuntime.packageManagerField.supported && repoRuntime.packageManagerField.valid ? 'pass' : 'warn',
        'package-manager-field',
        'runtime',
        repoRuntime.packageManagerField.supported
          ? `package.json declares packageManager=${repoRuntime.packageManagerField.raw}`
          : `package.json declares unsupported packageManager=${repoRuntime.packageManagerField.raw}`,
        {
          path: packagePath,
          packageManager: repoRuntime.packageManagerField,
        },
      )
    : check(
        'info',
        'package-manager-field',
        'runtime',
        'package.json does not declare a packageManager field; lockfiles and fallback heuristics drive inference.',
        { path: packagePath },
      ),
);
checks.push(
  repoRuntime.lockfiles.length > 0
    ? check(
        'pass',
        'package-manager-lockfiles',
        'build',
        `Detected lockfiles: ${repoRuntime.lockfiles.map((lockfile) => lockfile.name).join(', ')}`,
        {
          lockfiles: repoRuntime.lockfiles.map((lockfile) => ({
            name: lockfile.name,
            manager: lockfile.manager,
            path: lockfile.path,
          })),
        },
      )
    : check(
        'info',
        'package-manager-lockfiles',
        'build',
        'No package-manager lockfiles were detected; inference may be weaker on repos that omit packageManager.',
        {},
      ),
);
checks.push(
  check(
    repoRuntime.inference.weak ? 'warn' : 'pass',
    'package-manager-inference',
    'runtime',
    `Inferred ${repoRuntime.inference.manager} with ${repoRuntime.inference.confidence} confidence from ${repoRuntime.inference.reasons.join('; ') || 'fallback heuristics'}.`,
    {
      inference: repoRuntime.inference,
      suggestedCommands: Object.fromEntries(
        Object.entries(repoRuntime.commands)
          .filter(([, command]) => command.exists)
          .map(([name, command]) => [name, command.command]),
      ),
    },
  ),
);
checks.push(
  check(
    repoRuntime.runtime.corepackRelevant
      ? repoRuntime.runtime.corepackReady ? 'pass' : 'warn'
      : repoRuntime.tools.corepack.available ? 'info' : 'info',
    'corepack-readiness',
    'runtime',
    repoRuntime.runtime.corepackRelevant
      ? repoRuntime.runtime.corepackReady
        ? repoRuntime.tools[repoRuntime.runtime.inferredManager]?.available
          ? `${repoRuntime.runtime.inferredManager} is available directly; Corepack is optional for this repo.`
          : `${repoRuntime.tools.corepack.detail} can launch ${repoRuntime.runtime.inferredManager} for this repo.`
        : `${repoRuntime.runtime.inferredManager} is inferred for this repo, but neither ${repoRuntime.runtime.inferredManager} nor Corepack is available.`
      : repoRuntime.tools.corepack.available
        ? `${repoRuntime.tools.corepack.detail} is available, but this repo does not currently require a Corepack-managed package manager.`
        : 'Corepack is unavailable; that is OK unless the repo expects pnpm or yarn through packageManager.',
    {
      tools: {
        corepack: repoRuntime.tools.corepack,
        npm: repoRuntime.tools.npm,
        pnpm: repoRuntime.tools.pnpm,
        yarn: repoRuntime.tools.yarn,
        bun: repoRuntime.tools.bun,
      },
      inferredManager: repoRuntime.runtime.inferredManager,
    },
  ),
);
checks.push(
  check(
    ['build', 'dev', 'test'].some((name) => repoRuntime.scripts.important[name].exists) ? 'pass' : 'info',
    'repo-script-catalog',
    'build',
    ['build', 'dev', 'test']
      .filter((name) => repoRuntime.scripts.important[name].exists)
      .map((name) => `${name} → ${repoRuntime.commands[name].available ? repoRuntime.commands[name].rendered : repoRuntime.scripts.important[name].body}`)
      .join('; ') || 'No build/dev/test scripts were detected in package.json.',
    {
      scripts: Object.fromEntries(
        ['build', 'dev', 'test'].map((name) => [
          name,
          {
            exists: repoRuntime.scripts.important[name].exists,
            body: repoRuntime.scripts.important[name].body,
            inferredCommand: repoRuntime.commands[name].command,
          },
        ]),
      ),
    },
  ),
);
checks.push(
  playwrightSupport.available
    ? check(
        'pass',
        'playwright-adapter',
        'runtime',
        `Optional Playwright adapter is available via ${playwrightSupport.detail}.`,
        {
          playwright: playwrightSupport,
        },
      )
    : check(
        playwrightModuleName ? 'warn' : 'info',
        'playwright-adapter',
        'runtime',
        playwrightModuleName
          ? `Requested Playwright module ${playwrightModuleName} was not found. ${playwrightSupport.detail}`
          : `Optional Playwright adapter is not installed in this repo. ${playwrightSupport.detail} Install playwright only when richer locator/trace automation is needed.`,
        {
          playwright: playwrightSupport,
        },
      ),
);

if (manifest && expectedPluginId) {
  checks.push(
    check(
      manifest.id === expectedPluginId ? 'pass' : 'fail',
      'plugin-id-match',
      'deploy',
      `manifest id ${manifest.id ?? '(missing)'} ${manifest.id === expectedPluginId ? 'matches' : 'does not match'} ${expectedPluginId}`,
      { manifestId: manifest.id ?? null, expectedPluginId },
    ),
  );
}

checks.push(
  (await exists(distMainPath))
    ? check('pass', 'dist-main', 'build', 'Found dist/main.js', { path: distMainPath })
    : check('warn', 'dist-main', 'build', 'dist/main.js is missing; run the plugin build before deploy/reload', { path: distMainPath }, buildFixes),
);
checks.push(
  (await exists(distManifestPath))
    ? check('pass', 'dist-manifest', 'deploy', 'Found dist/manifest.json', { path: distManifestPath })
    : check('warn', 'dist-manifest', 'deploy', 'dist/manifest.json is missing; deploy cannot update the test vault manifest yet', { path: distManifestPath }, buildFixes),
);
checks.push(
  (await exists(distStylesPath))
    ? check('pass', 'dist-styles', 'deploy', 'Found dist/styles.css', { path: distStylesPath })
    : check('info', 'dist-styles', 'deploy', 'dist/styles.css is missing; this is OK for plugins without CSS', { path: distStylesPath }),
);

if (testVaultPluginDir) {
  const vaultDir = path.resolve(testVaultPluginDir);
  const vaultManifestPath = path.join(vaultDir, 'manifest.json');
  const vaultMainPath = path.join(vaultDir, 'main.js');
  const vaultStylesPath = path.join(vaultDir, 'styles.css');
  const vaultManifest = await readJsonOrNull(vaultManifestPath);

  checks.push(
    (await exists(vaultDir))
      ? check('pass', 'test-vault-plugin-dir', 'deploy', 'Test vault plugin directory exists', { path: vaultDir })
      : check('fail', 'test-vault-plugin-dir', 'deploy', 'Test vault plugin directory does not exist', { path: vaultDir }, [...createTestVaultDirFixes, ...deployFixes]),
  );
  checks.push(
    vaultManifest
      ? check('pass', 'test-vault-manifest', 'deploy', `Test vault manifest id ${vaultManifest.id ?? '(missing id)'}`, { path: vaultManifestPath })
      : check('warn', 'test-vault-manifest', 'deploy', 'Test vault manifest.json is missing or invalid', { path: vaultManifestPath }, deployFixes),
  );
  checks.push(
    (await exists(vaultMainPath))
      ? check('pass', 'test-vault-main', 'deploy', 'Test vault main.js exists', { path: vaultMainPath })
      : check('warn', 'test-vault-main', 'deploy', 'Test vault main.js is missing', { path: vaultMainPath }, deployFixes),
  );
  checks.push(
    (await exists(vaultStylesPath))
      ? check('pass', 'test-vault-styles', 'deploy', 'Test vault styles.css exists', { path: vaultStylesPath })
      : check('info', 'test-vault-styles', 'deploy', 'Test vault styles.css is missing; this is OK for plugins without CSS', { path: vaultStylesPath }),
  );
}

const obsidianHelp = await runProcess(obsidianCommand, ['help'], 7000);
const helpText = `${obsidianHelp.stdout}\n${obsidianHelp.stderr}`;
checks.push(
  obsidianHelp.ok
    ? check(
        helpText.includes('Developer:') || helpText.includes('dev:console') ? 'pass' : 'warn',
        'obsidian-cli',
        'cli',
        helpText.includes('Developer:') || helpText.includes('dev:console')
          ? 'Obsidian CLI is available with developer commands'
          : 'Obsidian command ran, but developer commands were not detected',
        { command: obsidianCommand, exitCode: obsidianHelp.exitCode },
      )
    : check(
        'warn',
        'obsidian-cli',
        'cli',
        obsidianHelp.timedOut
          ? 'Obsidian command timed out while checking help'
          : `Obsidian command failed: ${obsidianHelp.stderr.trim() || 'not available'}`,
        { command: obsidianCommand, exitCode: obsidianHelp.exitCode, timedOut: obsidianHelp.timedOut },
      ),
);

if (obsidianHelp.ok) {
  const restrictResult = await runProcess(obsidianCommand, buildVaultScopedArgs('plugins:restrict'), 7000);
  const restrictText = `${restrictResult.stdout}\n${restrictResult.stderr}`.trim().toLowerCase();
  const restricted = restrictResult.ok && restrictText === 'on';
  checks.push(
    check(
      restricted ? 'warn' : 'pass',
      'restricted-mode',
      'cli',
      restricted
        ? 'Restricted mode is enabled; fresh community plugin discovery will stay blocked until it is turned off.'
        : 'Restricted mode is already off or not blocking community plugins.',
      {
        command: obsidianCommand,
        vaultName: vaultName || null,
        output: restrictText || null,
      },
      restricted ? bootstrapFixes : [],
    ),
  );
}

if (obsidianHelp.ok && expectedPluginId && testVaultPluginDir) {
  const installedPluginsResult = await runProcess(
    obsidianCommand,
    buildVaultScopedArgs('plugins', ['filter=community', 'versions', 'format=json']),
    10000,
  );
  const enabledPluginsResult = await runProcess(
    obsidianCommand,
    buildVaultScopedArgs('plugins:enabled', ['filter=community', 'versions', 'format=json']),
    10000,
  );
  const installedPlugins = parsePluginList(installedPluginsResult.stdout || installedPluginsResult.text);
  const enabledPlugins = parsePluginList(enabledPluginsResult.stdout || enabledPluginsResult.text);
  const discoveredEntry = installedPlugins.find((entry) => entry.id === expectedPluginId) ?? null;
  const enabledEntry = enabledPlugins.find((entry) => entry.id === expectedPluginId) ?? null;

  checks.push(
    check(
      discoveredEntry ? 'pass' : 'warn',
      'plugin-discovered',
      'deploy',
      discoveredEntry
        ? `${expectedPluginId} is already discoverable in the target vault plugin catalog.`
        : `${expectedPluginId} is not yet discoverable in the target vault plugin catalog; fresh-vault bootstrap is required before reload automation can confirm the plugin is loaded.`,
      {
        command: obsidianCommand,
        vaultName: vaultName || null,
        pluginId: expectedPluginId,
        installedVersion: discoveredEntry?.version ?? null,
      },
      discoveredEntry ? [] : bootstrapFixes,
    ),
  );
  checks.push(
    check(
      enabledEntry ? 'pass' : 'warn',
      'plugin-enabled',
      'deploy',
      enabledEntry
        ? `${expectedPluginId} is enabled in the target vault.`
        : `${expectedPluginId} is not enabled in the target vault yet; bootstrap can enable it after discovery.`,
      {
        command: obsidianCommand,
        vaultName: vaultName || null,
        pluginId: expectedPluginId,
        enabledVersion: enabledEntry?.version ?? null,
      },
      enabledEntry ? [] : bootstrapFixes,
    ),
  );
}

try {
  const target = await resolveTarget({
    host: cdpHost,
    port: cdpPort,
    targetTitleContains: cdpTargetTitleContains,
  });
  checks.push(
    check('pass', 'cdp-target', 'cdp', `CDP target is reachable: ${target.title || target.url}`, {
      host: cdpHost,
      port: cdpPort,
      title: target.title ?? null,
      url: target.url ?? null,
    }),
  );
} catch (error) {
  checks.push(
    check(
      'warn',
      'cdp-target',
      'cdp',
      `CDP target is not reachable: ${error.message}`,
      {
        host: cdpHost,
        port: cdpPort,
        targetTitleContains: cdpTargetTitleContains || null,
      },
      cdpProbeFixes,
    ),
  );
}

const status = checks.reduce((current, entry) => (statusRank(entry.status) > statusRank(current) ? entry.status : current), 'pass');
const categoryCounts = checks.reduce((counts, entry) => {
  counts[entry.category] = counts[entry.category] ?? { pass: 0, info: 0, warn: 0, fail: 0 };
  counts[entry.category][entry.status] = (counts[entry.category][entry.status] ?? 0) + 1;
  return counts;
}, {});
const fixCommands = dedupeCommands(
  checks
    .flatMap((entry) => entry.fixes ?? [])
    .filter((entry) => entry.rendered),
);

let fixScriptPath = null;
if (fixRequested && fixCommands.length > 0) {
  fixScriptPath = fixOutputPath;
  const scriptText = buildCommandScript({
    title: 'Obsidian debug doctor fixes',
    commands: fixCommands,
    platform,
  });
  await ensureParentDirectory(fixScriptPath);
  await fs.writeFile(fixScriptPath, scriptText, 'utf8');
}

const report = {
  generatedAt: nowIso(),
  status,
  platform,
  repoDir,
  pluginId: expectedPluginId || manifest?.id || null,
  vaultName: vaultName || null,
  testVaultPluginDir: testVaultPluginDir ? path.resolve(testVaultPluginDir) : null,
  obsidianCommand,
  cdp: {
    host: cdpHost,
    port: cdpPort,
    targetTitleContains: cdpTargetTitleContains || null,
  },
  categoryCounts,
  repoRuntime: {
    packageManagerField: repoRuntime.packageManagerField,
    lockfiles: repoRuntime.lockfiles,
    scripts: repoRuntime.scripts,
    inference: repoRuntime.inference,
    tools: repoRuntime.tools,
    commands: repoRuntime.commands,
    runtime: repoRuntime.runtime,
    playwright: playwrightSupport,
  },
  checks,
  fixPlan: {
    requested: fixRequested,
    platform,
    commandCount: fixCommands.length,
    scriptPath: fixScriptPath,
    commands: fixCommands,
  },
};

if (outputPath) {
  const resolvedOutput = path.resolve(outputPath);
  await ensureParentDirectory(resolvedOutput);
  await fs.writeFile(resolvedOutput, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
}

console.log(JSON.stringify(report, null, 2));
