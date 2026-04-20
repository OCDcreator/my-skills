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
  hasHelpOption,
  nowIso,
  parseArgs,
  printHelpAndExit,
  resolveTarget,
} from './obsidian_cdp_common.mjs';
import {
  buildCommandScript,
  normalizePlatform,
  resolveTemplateCommand,
  scriptExtension,
} from './obsidian_debug_command_templates.mjs';
import {
  buildHotReloadGuidance,
  detectHotReloadContext,
} from './obsidian_debug_hot_reload_support.mjs';
import { detectAdapterSupport } from './obsidian_debug_adapter_support.mjs';
import { detectEcosystemSupport } from './obsidian_debug_ecosystem_support.mjs';
import { discoverLogstravaganzaCapture } from './obsidian_debug_logstravaganza.mjs';
import {
  detectPreflightSupport,
  getPreflightGate,
} from './obsidian_debug_preflight_support.mjs';
import { detectRepoRuntime } from './obsidian_debug_repo_runtime.mjs';
import { detectTestingFrameworkSupport } from './obsidian_debug_testing_framework_support.mjs';

const options = parseArgs(process.argv.slice(2));
if (hasHelpOption(options)) {
  printHelpAndExit(`
Usage: node scripts/obsidian_debug_doctor.mjs [options]

Common options:
  --repo-dir <path>                 Plugin repo directory. Defaults to cwd.
  --plugin-id <id>                  Expected manifest/plugin id.
  --test-vault-plugin-dir <path>    Target vault plugin directory.
  --obsidian-command <command>      Obsidian CLI/app command. Defaults to obsidian.
  --vault-name <name>               Vault name for CLI commands.
  --app-path <path>                 Optional Obsidian desktop app/executable path.
  --vault-uri <uri>                 Optional obsidian:// URI for auto-launch fixes.
  --vault-path <path>               Optional vault/file path for auto-launch fixes.
  --cdp-host <host> --cdp-port <n>  CDP endpoint. Defaults to 127.0.0.1:9222.
  --platform <auto|windows|bash>    Fix-plan command platform.
  --output <path>                   Doctor JSON output path.
  --fix                            Emit reviewable fix scripts/plan.
`);
}

const repoDir = path.resolve(getStringOption(options, 'repo-dir', process.cwd()));
const testVaultPluginDir = getStringOption(options, 'test-vault-plugin-dir', '').trim();
const expectedPluginId = getStringOption(options, 'plugin-id', '').trim();
const obsidianCommand = getStringOption(options, 'obsidian-command', 'obsidian').trim();
const vaultName = getStringOption(options, 'vault-name', '').trim();
const appPath = getStringOption(options, 'app-path', '').trim();
const vaultUri = getStringOption(options, 'vault-uri', '').trim();
const vaultPath = getStringOption(options, 'vault-path', '').trim();
const cdpHost = getStringOption(options, 'cdp-host', '127.0.0.1');
const cdpPort = getNumberOption(options, 'cdp-port', 9222);
const cdpTargetTitleContains = getStringOption(options, 'cdp-target-title-contains', '');
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
  appPath,
  vaultUri,
  vaultPath,
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

function supportStatus(entry) {
  return entry?.available ? 'pass' : entry?.declared ? 'warn' : 'info';
}

function listedScriptNames(scripts = []) {
  return scripts
    .map((entry) => entry?.name)
    .filter((entry) => typeof entry === 'string' && entry.trim().length > 0)
    .join(', ');
}

function commandFixSpec({ id, label, summary, safety, commandEntry }) {
  if (!commandEntry?.available || !Array.isArray(commandEntry.command) || commandEntry.command.length === 0) {
    return null;
  }

  return {
    id,
    label,
    summary,
    safety,
    dryRunFriendly: false,
    executable: commandEntry.command[0],
    args: commandEntry.command.slice(1),
    cwd: '{{repoDir}}',
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
const manifest = await readJsonOrNull(manifestPath);
const runtimeSupport = await detectRepoRuntime({ repoDir });
const packageJson = runtimeSupport.packageJson ?? await readJsonOrNull(packagePath);
const repoRuntime = runtimeSupport.packageJson ? runtimeSupport : null;
const ecosystemSupport = await detectEcosystemSupport({ repoDir });
const preflightSupport = await detectPreflightSupport({
  repoDir,
  runtimeSupport,
  ecosystemSupport,
});
const lintPreflightGate = getPreflightGate(preflightSupport, 'lint');
const pluginEntryPreflightGate = getPreflightGate(preflightSupport, 'plugin-entry-validation');
const testingFramework = await detectTestingFrameworkSupport({ repoDir });
const adapterSupport = await detectAdapterSupport({
  repoDir,
  runtimeSupport,
  ecosystemSupport,
  testingFrameworkSupport: testingFramework,
});
const obsidianE2EAdapter = adapterSupport.adapters.obsidianE2E;
const testingFrameworkAdapter = adapterSupport.adapters.testingFramework;
const wdioAdapter = adapterSupport.adapters.wdioObsidianService;
const buildScriptExists = Boolean(runtimeSupport.scripts?.important?.build?.exists);
const lintScriptExists = Boolean(lintPreflightGate?.present);

const buildFix = buildScriptExists
  ? commandFixSpec({
      id: 'run-build',
      label: 'Build plugin output',
      summary: 'Regenerate the deployable dist artifacts before retrying deploy/reload.',
      safety: 'writes-build-output',
      commandEntry: runtimeSupport.commands?.build,
    })
  : null;
const buildFixes = buildFix ? [buildFix] : [];
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
const appLaunchFixes = [
  {
    id: 'launch-obsidian-app',
    label: 'Launch or focus Obsidian',
    summary: 'Starts or focuses Obsidian, opens the target vault when provided, and waits for CLI or CDP readiness before retrying automation.',
    safety: 'launches-app',
    dryRunFriendly: false,
    executable: 'node',
    args: [
      '{{toolRoot}}/scripts/obsidian_debug_launch_app.mjs',
      '--mode',
      'auto',
      '--obsidian-command',
      '{{obsidianCommand}}',
      ...(appPath ? ['--app-path', appPath] : []),
      ...(vaultName ? ['--vault-name', '{{vaultName}}'] : []),
      ...(vaultUri ? ['--vault-uri', vaultUri] : []),
      ...(vaultPath ? ['--vault-path', vaultPath] : []),
      '--cdp-host',
      '{{cdpHost}}',
      '--cdp-port',
      '{{cdpPort}}',
    ],
    cwd: '{{repoDir}}',
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

function buildHotReloadCycleFixes(mode, settleMs, summary) {
  if (!expectedPluginId || !testVaultPluginDir) {
    return [];
  }

  const normalizedSettleMs = Math.max(0, Number(settleMs) || 0);
  if (platform === 'windows') {
    return [
      {
        id: `hot-reload-${mode}-cycle`,
        label: mode === 'coexist' ? 'Re-run in Hot Reload coexist mode' : 'Re-run in controlled reload mode',
        summary,
        safety: 'writes-local-state',
        dryRunFriendly: false,
        executable: 'powershell',
        args: [
          '-NoProfile',
          '-ExecutionPolicy',
          'Bypass',
          '-File',
          '{{toolRoot}}/scripts/obsidian_plugin_debug_cycle.ps1',
          '-PluginId',
          '{{pluginId}}',
          '-TestVaultPluginDir',
          '{{testVaultPluginDir}}',
          '-ObsidianCommand',
          '{{obsidianCommand}}',
          ...(vaultName ? ['-VaultName', '{{vaultName}}'] : []),
          '-HotReloadMode',
          mode,
          '-HotReloadSettleMs',
          String(normalizedSettleMs),
          '-SkipBuild',
          '-SkipDeploy',
        ],
        cwd: '{{repoDir}}',
      },
    ];
  }

  return [
    {
      id: `hot-reload-${mode}-cycle`,
      label: mode === 'coexist' ? 'Re-run in Hot Reload coexist mode' : 'Re-run in controlled reload mode',
      summary,
      safety: 'writes-local-state',
      dryRunFriendly: false,
      executable: 'bash',
      args: [
        '{{toolRoot}}/scripts/obsidian_plugin_debug_cycle.sh',
        '--plugin-id',
        '{{pluginId}}',
        '--test-vault-plugin-dir',
        '{{testVaultPluginDir}}',
        '--obsidian-command',
        '{{obsidianCommand}}',
        ...(vaultName ? ['--vault-name', '{{vaultName}}'] : []),
        '--hot-reload-mode',
        mode,
        '--hot-reload-settle-ms',
        String(normalizedSettleMs),
        '--skip-build',
        '--skip-deploy',
      ],
      cwd: '{{repoDir}}',
    },
  ];
}

checks.push(
  manifest
    ? check('pass', 'repo-manifest', 'repo', `Found manifest.json with id ${manifest.id ?? '(missing id)'}`, { path: manifestPath })
    : check('fail', 'repo-manifest', 'repo', 'manifest.json was not found or is invalid', { path: manifestPath }),
);
checks.push(
  packageJson
    ? check('pass', 'repo-package', 'build', `Found package.json${buildScriptExists ? ' with build script' : ''}`, { path: packagePath })
    : check('warn', 'repo-package', 'build', 'package.json was not found or is invalid', { path: packagePath }),
);
checks.push(
  buildScriptExists
    ? check('pass', 'build-script', 'build', 'package.json defines a build script', { path: packagePath })
    : check('warn', 'build-script', 'build', 'package.json is missing scripts.build; build fixes stay informational only', { path: packagePath }),
);
checks.push(
  check(
    runtimeSupport.packageManagerField?.supported
      ? 'pass'
      : runtimeSupport.packageManagerField
        ? 'warn'
        : 'info',
    'package-manager-field',
    'runtime',
    runtimeSupport.packageManagerField
      ? runtimeSupport.packageManagerField.supported
        ? `package.json declares packageManager=${runtimeSupport.packageManagerField.raw}.`
        : `package.json declares packageManager=${runtimeSupport.packageManagerField.raw}, but the value is unsupported or malformed.`
      : 'package.json does not declare packageManager; runtime inference falls back to lockfiles and available tools.',
    {
      packageManagerField: runtimeSupport.packageManagerField,
    },
  ),
);
checks.push(
  check(
    runtimeSupport.inference.weak ? 'info' : 'pass',
    'package-manager-inference',
    'runtime',
    `Inferred ${runtimeSupport.inference.manager} (${runtimeSupport.inference.confidence} confidence): ${runtimeSupport.inference.reasons.join('; ')}`,
    {
      inference: runtimeSupport.inference,
      lockfiles: runtimeSupport.lockfiles,
    },
  ),
);
checks.push(
  check(
    runtimeSupport.runtime.corepackReady ? 'pass' : 'warn',
    'package-manager-tooling',
    'runtime',
    runtimeSupport.runtime.corepackReady
      ? `Package-manager tooling is ready for inferred ${runtimeSupport.runtime.inferredManager}.`
      : `Package-manager tooling is not yet ready for inferred ${runtimeSupport.runtime.inferredManager}. ${runtimeSupport.tools?.[runtimeSupport.runtime.inferredManager]?.detail ?? ''}`.trim(),
    {
      runtime: runtimeSupport.runtime,
      tools: runtimeSupport.tools,
    },
  ),
);
checks.push(
  check(
    lintScriptExists ? 'pass' : 'info',
    'lint-script',
    'lint',
    lintScriptExists
      ? lintPreflightGate.detail
      : 'No repo-owned lint preflight script was detected; pre-build lint stays optional until the repo owns one.',
    {
      path: packagePath,
      script: lintPreflightGate?.scriptName ?? '',
      command: lintPreflightGate?.command?.rendered || lintPreflightGate?.command?.previewRendered || null,
      runnable: Boolean(lintPreflightGate?.command?.available),
      remediationHints: lintPreflightGate?.remediationHints ?? [],
    },
  ),
);
checks.push(
  check(
    supportStatus(ecosystemSupport.tools.obsidianDevUtils),
    'obsidian-dev-utils-module',
    'build',
    ecosystemSupport.tools.obsidianDevUtils.available
      ? `${ecosystemSupport.tools.obsidianDevUtils.detail} Prefer repo-owned dev/build scripts when they already route through it.`
      : ecosystemSupport.tools.obsidianDevUtils.detail,
    {
      tool: ecosystemSupport.tools.obsidianDevUtils,
    },
  ),
);
checks.push(
  check(
    ecosystemSupport.tools.obsidianDevUtils.scripts.length > 0 ? 'pass' : 'info',
    'obsidian-dev-utils-scripts',
    'build',
    ecosystemSupport.tools.obsidianDevUtils.scripts.length > 0
      ? `Found repo-owned obsidian-dev-utils-aligned script(s): ${listedScriptNames(ecosystemSupport.tools.obsidianDevUtils.scripts)}.`
      : 'No repo-owned script explicitly advertises obsidian-dev-utils usage.',
    {
      scripts: ecosystemSupport.tools.obsidianDevUtils.scripts,
    },
  ),
);
checks.push(
  check(
    supportStatus(ecosystemSupport.tools.eslintObsidianmd),
    'eslint-plugin-obsidianmd-module',
    'lint',
    ecosystemSupport.tools.eslintObsidianmd.available
      ? `${ecosystemSupport.tools.eslintObsidianmd.detail} Use a repo-owned lint script before build to catch manifest/sample-code issues earlier.`
      : ecosystemSupport.tools.eslintObsidianmd.detail,
    {
      tool: ecosystemSupport.tools.eslintObsidianmd,
    },
  ),
);
checks.push(
  check(
    ecosystemSupport.tools.eslintObsidianmd.scripts.length > 0 || lintScriptExists ? 'pass' : 'info',
    'eslint-plugin-obsidianmd-scripts',
    'lint',
    ecosystemSupport.tools.eslintObsidianmd.scripts.length > 0
      ? `Found repo-owned lint script(s) that reference eslint-plugin-obsidianmd: ${listedScriptNames(ecosystemSupport.tools.eslintObsidianmd.scripts)}.`
      : lintScriptExists
        ? 'A repo-owned lint script exists; wire eslint-plugin-obsidianmd into that script when the repo wants official Obsidian lint coverage.'
        : 'No repo-owned lint script currently references eslint-plugin-obsidianmd.',
    {
      scripts: ecosystemSupport.tools.eslintObsidianmd.scripts,
    },
  ),
);
checks.push(
  check(
    testingFramework.available ? 'pass' : testingFramework.declared ? 'warn' : 'info',
    'testing-framework-module',
    'test',
    testingFramework.detail,
    {
      testingFramework: {
        available: testingFramework.available,
        declared: testingFramework.declared,
        moduleName: testingFramework.moduleName,
        version: testingFramework.version,
        resolvedPath: testingFramework.resolvedPath,
        declaredDependencies: testingFramework.declaredDependencies,
      },
    },
  ),
);
checks.push(
  check(
    supportStatus(ecosystemSupport.tools.obsidianE2E),
    'obsidian-e2e-module',
    'test',
    ecosystemSupport.tools.obsidianE2E.available
      ? `${ecosystemSupport.tools.obsidianE2E.detail} This is a Vitest-first optional Obsidian integration test path.`
      : ecosystemSupport.tools.obsidianE2E.detail,
    {
      tool: ecosystemSupport.tools.obsidianE2E,
    },
  ),
);
checks.push(
  check(
    obsidianE2EAdapter.status,
    'obsidian-e2e-scripts',
    'test',
    obsidianE2EAdapter.detail,
    {
      scripts: obsidianE2EAdapter.scripts,
      script: obsidianE2EAdapter.scriptName,
      command: obsidianE2EAdapter.command.rendered || obsidianE2EAdapter.command.previewRendered || null,
      runnable: obsidianE2EAdapter.runnable,
      runnableInThisCheckout: obsidianE2EAdapter.runnableInThisCheckout,
      repoOwnedPaths: obsidianE2EAdapter.repoOwnedPaths,
      missingRepoOwnedPaths: obsidianE2EAdapter.missingRepoOwnedPaths,
    },
  ),
);
checks.push(
  check(
    testingFrameworkAdapter.status,
    'testing-framework-scripts',
    'test',
    testingFrameworkAdapter.detail,
    {
      scripts: testingFrameworkAdapter.scripts,
      script: testingFrameworkAdapter.scriptName,
      command: testingFrameworkAdapter.command.rendered || testingFrameworkAdapter.command.previewRendered || null,
      runnable: testingFrameworkAdapter.runnable,
      runnableInThisCheckout: testingFrameworkAdapter.runnableInThisCheckout,
      repoOwnedPaths: testingFrameworkAdapter.repoOwnedPaths,
      missingRepoOwnedPaths: testingFrameworkAdapter.missingRepoOwnedPaths,
    },
  ),
);
checks.push(
  check(
    supportStatus(ecosystemSupport.tools.wdioObsidianService),
    'wdio-obsidian-service-module',
    'test',
    ecosystemSupport.tools.wdioObsidianService.available
      ? `${ecosystemSupport.tools.wdioObsidianService.detail} This can move real plugin E2E into CI when the repo owns a WDIO suite.`
      : ecosystemSupport.tools.wdioObsidianService.detail,
    {
      tool: ecosystemSupport.tools.wdioObsidianService,
    },
  ),
);
checks.push(
  check(
    wdioAdapter.status,
    'wdio-obsidian-service-scripts',
    'test',
    wdioAdapter.detail,
    {
      scripts: wdioAdapter.scripts,
      script: wdioAdapter.scriptName,
      command: wdioAdapter.command.rendered || wdioAdapter.command.previewRendered || null,
      runnable: wdioAdapter.runnable,
      runnableInThisCheckout: wdioAdapter.runnableInThisCheckout,
      repoOwnedPaths: wdioAdapter.repoOwnedPaths,
      missingRepoOwnedPaths: wdioAdapter.missingRepoOwnedPaths,
    },
  ),
);
checks.push(
  check(
    pluginEntryPreflightGate?.present ? 'pass' : 'info',
    'plugin-entry-validation-scripts',
    'ci',
    pluginEntryPreflightGate?.present
      ? pluginEntryPreflightGate.detail
      : ecosystemSupport.scripts.pluginEntryValidation.detail,
    {
      scripts: ecosystemSupport.scripts.pluginEntryValidation.scripts,
      script: pluginEntryPreflightGate?.scriptName ?? '',
      command: pluginEntryPreflightGate?.command?.rendered || pluginEntryPreflightGate?.command?.previewRendered || null,
      runnable: Boolean(pluginEntryPreflightGate?.command?.available),
      remediationHints: pluginEntryPreflightGate?.remediationHints ?? [],
    },
  ),
);
checks.push(
  check(
    'info',
    'ci-quality-gate-templates',
    'ci',
    'Headless quality-gate templates can be emitted for install/build/test/script dry-runs while desktop Obsidian reload/capture stays local-only.',
    {
      templateScript: path.join(toolRoot, 'scripts', 'obsidian_debug_ci_templates.mjs'),
      preflight: preflightSupport,
      ciSuitable: [
        'repo-owned install command',
        'repo-owned lint and optional plugin-entry preflight commands before build',
        'repo-owned build/test commands',
        'optional obsidian-e2e package script',
        'optional obsidian-testing-framework package script',
        'optional wdio-obsidian-service package script',
        'obsidian_debug_job.mjs dry-run plans',
      ],
      localOnly: [
        'fresh-vault bootstrap',
        'desktop Obsidian reload',
        'CLI/CDP log capture',
        'screenshots, DOM snapshots, and Playwright traces',
      ],
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
        helpText.includes('Developer:') || helpText.includes('dev:console') ? [] : appLaunchFixes,
      )
    : check(
        'warn',
        'obsidian-cli',
        'cli',
        obsidianHelp.timedOut
          ? 'Obsidian command timed out while checking help'
          : `Obsidian command failed: ${obsidianHelp.stderr.trim() || 'not available'}`,
        { command: obsidianCommand, exitCode: obsidianHelp.exitCode, timedOut: obsidianHelp.timedOut },
        appLaunchFixes,
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

let installedPlugins = [];
let enabledPlugins = [];
if (obsidianHelp.ok) {
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
  installedPlugins = installedPluginsResult.ok ? parsePluginList(installedPluginsResult.stdout) : [];
  enabledPlugins = enabledPluginsResult.ok ? parsePluginList(enabledPluginsResult.stdout) : [];
}

const logstravaganzaInstalled = installedPlugins.find((entry) => entry.id === 'logstravaganza') ?? null;
const logstravaganzaEnabled = enabledPlugins.find((entry) => entry.id === 'logstravaganza') ?? null;
const mobileHotReloadInstalled = installedPlugins.find((entry) => entry.id === 'mobile-hot-reload') ?? null;
const mobileHotReloadEnabled = enabledPlugins.find((entry) => entry.id === 'mobile-hot-reload') ?? null;
const logstravaganzaCapture = await discoverLogstravaganzaCapture({ testVaultPluginDir });
const logstravaganzaFilesystemInstalled = Boolean(logstravaganzaCapture.pluginDirExists);
const logstravaganzaDetected = Boolean(logstravaganzaInstalled) || logstravaganzaFilesystemInstalled;
const logstravaganzaUsable = Boolean(logstravaganzaCapture.usable);

checks.push(
  check(
    logstravaganzaUsable ? 'pass' : 'info',
    'logstravaganza-vault',
    'capture',
    logstravaganzaUsable
      ? `${logstravaganzaCapture.detail} The cycle capture writes vault-log-capture.json, and analysis/reporting merge those events with console/CDP evidence while preserving source paths and line numbers.`
      : logstravaganzaEnabled
        ? `Vault enables Logstravaganza, but no usable NDJSON files were discovered yet. ${logstravaganzaCapture.detail}`
        : logstravaganzaDetected
          ? `Vault contains Logstravaganza context, but persistent NDJSON capture is not usable yet. ${logstravaganzaCapture.detail}`
          : 'Logstravaganza was not detected in the target vault; persistent secondary file logging remains optional.',
    {
      installedVersion: logstravaganzaInstalled?.version ?? null,
      enabledVersion: logstravaganzaEnabled?.version ?? null,
      filesystemInstalled: logstravaganzaFilesystemInstalled,
      usable: logstravaganzaUsable,
      sourceCount: logstravaganzaCapture.sourceCount,
      lineCount: logstravaganzaCapture.lineCount,
      capture: logstravaganzaCapture,
    },
  ),
);
checks.push(
  check(
    mobileHotReloadEnabled ? 'warn' : mobileHotReloadInstalled ? 'info' : 'info',
    'mobile-hot-reload-vault',
    'reload',
    mobileHotReloadEnabled
      ? 'Vault enables Mobile Hot Reload; treat it as intentional cross-device watch context because background sync can influence reload timing.'
      : mobileHotReloadInstalled
        ? 'Vault contains Mobile Hot Reload but it is not enabled; cross-device hot reload remains optional.'
        : 'Mobile Hot Reload was not detected in the target vault.',
    {
      installedVersion: mobileHotReloadInstalled?.version ?? null,
      enabledVersion: mobileHotReloadEnabled?.version ?? null,
    },
  ),
);

const hotReloadContext = await detectHotReloadContext({
  repoRuntime,
  testVaultPluginDir,
  installedPlugins,
  enabledPlugins,
});
const hotReloadGuidance = buildHotReloadGuidance(hotReloadContext);
const hotReloadFixes = hotReloadContext.likelyPresent
  ? [
      ...buildHotReloadCycleFixes(
        'controlled',
        hotReloadGuidance.recommendedSettleMs || 1500,
        'Wait for background Hot Reload churn to settle, clear buffers, then issue a deterministic explicit reload.',
      ),
      ...buildHotReloadCycleFixes(
        'coexist',
        hotReloadGuidance.recommendedSettleMs || 1500,
        'Skip the explicit plugin reload and let a background Hot Reload helper drive startup while the capture stays in coexistence mode.',
      ),
    ]
  : [];

checks.push(
  check(
    hotReloadContext.vault.hotReloadEnabledIds.length > 0
      ? 'warn'
      : hotReloadContext.vault.hotReloadInstalledIds.length > 0
        ? 'info'
        : 'info',
    'hot-reload-vault',
    'reload',
    hotReloadContext.vault.hotReloadEnabledIds.length > 0
      ? `Vault Hot Reload helper(s) are enabled: ${hotReloadContext.vault.hotReloadEnabledIds.join(', ')}.`
      : hotReloadContext.vault.hotReloadInstalledIds.length > 0
        ? `Vault contains Hot Reload-like plugin ids, but none are enabled: ${hotReloadContext.vault.hotReloadInstalledIds.join(', ')}.`
        : 'No Hot Reload-like community plugin ids were detected in the target vault state.',
    {
      hotReload: hotReloadContext,
    },
  ),
);
checks.push(
  check(
    'info',
    'hot-reload-repo-signals',
    'reload',
    hotReloadContext.repo.watchScripts.length > 0 || hotReloadContext.repo.symlinkedEntries.length > 0
      ? [
          hotReloadContext.repo.watchScripts.length > 0
            ? `Watch-capable repo scripts: ${hotReloadContext.repo.watchScripts.map((entry) => entry.name).join(', ')}`
            : null,
          hotReloadContext.repo.symlinkedEntries.length > 0
            ? `Symlinked test-vault entries: ${hotReloadContext.repo.symlinkedEntries.map((entry) => path.basename(entry.path)).join(', ')}`
            : null,
        ].filter(Boolean).join('; ')
      : 'Repo-side watch and symlink signals do not currently suggest a background Hot Reload loop.',
    {
      hotReload: hotReloadContext,
    },
  ),
);
checks.push(
  check(
    hotReloadContext.likelyActive ? 'warn' : 'info',
    'hot-reload-coordination',
    'reload',
    hotReloadGuidance.detail,
    {
      hotReload: hotReloadContext,
      guidance: hotReloadGuidance,
    },
    hotReloadFixes,
  ),
);

if (obsidianHelp.ok && expectedPluginId && testVaultPluginDir) {
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
      [...appLaunchFixes, ...cdpProbeFixes],
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
  appLaunch: {
    appPath: appPath || null,
    vaultUri: vaultUri || null,
    vaultPath: vaultPath || null,
  },
  cdp: {
    host: cdpHost,
    port: cdpPort,
    targetTitleContains: cdpTargetTitleContains || null,
  },
  categoryCounts,
  testingFramework: {
    available: testingFramework.available,
    declared: testingFramework.declared,
    moduleName: testingFramework.moduleName,
    version: testingFramework.version,
    scripts: testingFramework.scripts,
    detail: testingFramework.detail,
  },
  repoRuntime: {
    packageManagerField: runtimeSupport.packageManagerField,
    inference: runtimeSupport.inference,
    runtime: runtimeSupport.runtime,
    tools: runtimeSupport.tools,
    scripts: runtimeSupport.scripts,
    commands: runtimeSupport.commands,
  },
  preflight: preflightSupport,
  adapterLanes: adapterSupport.adapters,
  ecosystem: {
    tools: ecosystemSupport.tools,
    scripts: ecosystemSupport.scripts,
    vaultPlugins: {
      logstravaganza: {
        installed: logstravaganzaDetected,
        enabled: Boolean(logstravaganzaEnabled),
        installedVersion: logstravaganzaInstalled?.version ?? null,
        enabledVersion: logstravaganzaEnabled?.version ?? null,
        filesystemInstalled: logstravaganzaFilesystemInstalled,
        usable: logstravaganzaUsable,
        sourceCount: logstravaganzaCapture.sourceCount,
        lineCount: logstravaganzaCapture.lineCount,
        capture: logstravaganzaCapture,
      },
      mobileHotReload: {
        installed: Boolean(mobileHotReloadInstalled),
        enabled: Boolean(mobileHotReloadEnabled),
        installedVersion: mobileHotReloadInstalled?.version ?? null,
        enabledVersion: mobileHotReloadEnabled?.version ?? null,
      },
    },
  },
  ciTemplates: {
    script: path.join(toolRoot, 'scripts', 'obsidian_debug_ci_templates.mjs'),
    preflight: preflightSupport,
    adapterLanes: adapterSupport.adapters,
    ciSuitable: [
      'repo-owned install command',
      'repo-owned lint and optional plugin-entry preflight commands before build',
      'repo-owned build/test commands',
      'optional obsidian-e2e package script',
      'optional obsidian-testing-framework package script',
      'optional wdio-obsidian-service package script',
      'obsidian_debug_job.mjs dry-run plans',
    ],
    localOnly: [
      'fresh-vault bootstrap',
      'desktop Obsidian reload',
      'CLI/CDP log capture',
      'screenshots, DOM snapshots, and Playwright traces',
    ],
  },
  hotReload: {
    ...hotReloadContext,
    guidance: hotReloadGuidance,
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
