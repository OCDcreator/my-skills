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

const options = parseArgs(process.argv.slice(2));
const jobPathRaw = getStringOption(options, 'job', '').trim();
if (!jobPathRaw) {
  throw new Error('--job is required');
}

const mode = getBooleanOption(options, 'run', false)
  ? 'run'
  : getBooleanOption(options, 'dry-run', false)
    ? 'dry-run'
    : getStringOption(options, 'mode', 'dry-run').trim().toLowerCase();
if (!['dry-run', 'run'].includes(mode)) {
  throw new Error('--mode must be dry-run or run');
}

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const jobPath = path.resolve(jobPathRaw);
const jobSpec = JSON.parse((await fs.readFile(jobPath, 'utf8')).replace(/^\uFEFF/, ''));
const platform = normalizePlatform(getStringOption(options, 'platform', 'auto'));
const cwdOverride = getStringOption(options, 'cwd', '').trim();
const outputPath = getStringOption(options, 'output', '').trim();
const outputDirOverride = getStringOption(options, 'output-dir', '').trim();

function normalizePlatform(value) {
  const normalized = value.trim().toLowerCase();
  if (!normalized || normalized === 'auto') {
    return process.platform === 'win32' ? 'windows' : 'bash';
  }
  if (['windows', 'powershell', 'pwsh', 'ps1'].includes(normalized)) {
    return 'windows';
  }
  if (['bash', 'macos', 'linux', 'darwin', 'sh'].includes(normalized)) {
    return 'bash';
  }
  throw new Error('--platform must be auto, windows, or bash');
}

function asObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function asArray(value) {
  if (Array.isArray(value)) {
    return value.map((entry) => String(entry)).filter((entry) => entry.length > 0);
  }
  if (typeof value === 'string' && value.trim().length > 0) {
    return [value.trim()];
  }
  return [];
}

function enabled(section, fallback = true) {
  if (!section || typeof section !== 'object' || Array.isArray(section)) {
    return fallback;
  }
  return section.enabled !== false;
}

function stringValue(value, fallback = '') {
  return typeof value === 'string' && value.length > 0 ? value : fallback;
}

function numberValue(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function booleanValue(value, fallback = false) {
  return typeof value === 'boolean' ? value : fallback;
}

function interpolate(value, variables) {
  return String(value ?? '').replace(/\{\{(\w+)\}\}/g, (_, key) => variables[key] ?? '');
}

function quoteBash(value) {
  return `'${String(value).replaceAll("'", "'\\''")}'`;
}

function quotePowerShell(value) {
  return `'${String(value).replaceAll("'", "''")}'`;
}

function renderCommand(command) {
  const quote = command.platform === 'windows' ? quotePowerShell : quoteBash;
  if (command.platform === 'windows') {
    return `& ${quote(command.executable)} ${command.args.map((entry) => quote(entry)).join(' ')}`;
  }
  return [command.executable, ...command.args].map((entry) => quote(entry)).join(' ');
}

function addValue(args, flag, value) {
  if (value === undefined || value === null || String(value).trim().length === 0) {
    return;
  }
  args.push(flag, String(value));
}

function addSwitch(args, flag, isEnabled) {
  if (isEnabled) {
    args.push(flag);
  }
}

function commandFor({ phase, executable, args, cwd, platform, summary }) {
  const command = {
    phase,
    executable,
    args: args.map((entry) => String(entry)),
    cwd,
    platform,
    summary,
  };
  return {
    ...command,
    rendered: renderCommand(command),
  };
}

function buildCycleCommand({ spec, platform, cwd, warnings, outputDirOverride = '' }) {
  const runtime = asObject(spec.runtime);
  const build = asObject(spec.build);
  const deploy = asObject(spec.deploy);
  const reload = asObject(spec.reload);
  const logWatch = asObject(spec.logWatch);
  const scenario = asObject(spec.scenario);
  const assertions = asObject(spec.assertions);
  const comparison = asObject(spec.comparison);
  const capture = asObject(spec.capture);
  const job = asObject(spec.job);
  const jobId = stringValue(job.id, 'obsidian-debug-job');
  const outputDir = outputDirOverride || interpolate(stringValue(runtime.outputDir, `.obsidian-debug/${jobId}`), {
    jobId,
    platform,
  });
  const pluginId = stringValue(runtime.pluginId, '');
  const testVaultPluginDir = stringValue(runtime.testVaultPluginDir, '');
  const useCdp = stringValue(reload.mode, 'cli').toLowerCase() === 'cdp' || booleanValue(reload.useCdp, false);
  const watchSeconds = enabled(logWatch, true) ? numberValue(logWatch.seconds, 20) : 0;
  const captureEnabled = enabled(capture, true);

  if (!pluginId) {
    warnings.push('runtime.pluginId is empty; run mode requires a plugin id.');
  }
  if (!testVaultPluginDir) {
    warnings.push('runtime.testVaultPluginDir is empty; run mode requires a test vault plugin directory.');
  }

  if (platform === 'windows') {
    const args = [
      '-NoProfile',
      '-ExecutionPolicy',
      'Bypass',
      '-File',
      path.join(scriptDir, 'obsidian_plugin_debug_cycle.ps1'),
    ];
    addValue(args, '-PluginId', pluginId);
    addValue(args, '-TestVaultPluginDir', testVaultPluginDir);
    addValue(args, '-VaultName', runtime.vaultName);
    addValue(args, '-ObsidianCommand', runtime.obsidianCommand);
    addValue(args, '-DeployFrom', stringValue(deploy.from, 'dist'));
    addValue(args, '-OutputDir', outputDir);
    const buildCommand = asArray(build.command);
    if (buildCommand.length > 0) {
      args.push('-BuildCommand', ...buildCommand);
    }
    addValue(args, '-WatchSeconds', watchSeconds);
    addValue(args, '-PollIntervalMs', numberValue(logWatch.pollIntervalMs, 1000));
    addValue(args, '-ConsoleLimit', numberValue(logWatch.consoleLimit, 200));
    addValue(args, '-DomSelector', stringValue(assertions.domSelector, '.workspace-leaf.mod-active'));
    addSwitch(args, '-UseCdp', useCdp);
    addValue(args, '-CdpHost', reload.cdp?.host);
    addValue(args, '-CdpPort', reload.cdp?.port);
    addValue(args, '-CdpTargetTitleContains', reload.cdp?.targetTitleContains);
    addValue(args, '-CdpReloadDelayMs', reload.cdp?.reloadDelayMs);
    addValue(args, '-CdpEvalAfterReload', reload.cdp?.evalAfterReload);
    if (enabled(scenario, false)) {
      addValue(args, '-ScenarioName', scenario.name);
      addValue(args, '-ScenarioPath', scenario.path);
      addValue(args, '-ScenarioCommandId', scenario.commandId);
      addValue(args, '-SurfaceProfilePath', scenario.surfaceProfile);
      addValue(args, '-ScenarioSleepMs', numberValue(scenario.sleepMs, 2000));
    }
    addValue(args, '-AssertionsPath', assertions.path);
    addValue(args, '-CompareDiagnosisPath', comparison.baselineDiagnosisPath);
    addSwitch(args, '-DomText', booleanValue(assertions.domText, false));
    addSwitch(args, '-SkipBuild', !enabled(build, true));
    addSwitch(args, '-SkipDeploy', !enabled(deploy, true));
    addSwitch(args, '-SkipReload', !enabled(reload, true));
    addSwitch(args, '-SkipScreenshot', !captureEnabled || capture.screenshot === false);
    addSwitch(args, '-SkipDom', !captureEnabled || capture.dom === false);
    return commandFor({
      phase: 'debug-cycle',
      executable: 'powershell',
      args,
      cwd,
      platform,
      summary: 'Run the Windows PowerShell build/deploy/reload/watch cycle.',
    });
  }

  const args = [path.join(scriptDir, 'obsidian_plugin_debug_cycle.sh')];
  addValue(args, '--plugin-id', pluginId);
  addValue(args, '--test-vault-plugin-dir', testVaultPluginDir);
  addValue(args, '--vault-name', runtime.vaultName);
  addValue(args, '--obsidian-command', runtime.obsidianCommand);
  addValue(args, '--deploy-from', stringValue(deploy.from, 'dist'));
  addValue(args, '--output-dir', outputDir);
  const buildCommand = asArray(build.command);
  if (buildCommand.length > 0) {
    addValue(args, '--build-command', buildCommand.join(' '));
  }
  addValue(args, '--watch-seconds', watchSeconds);
  addValue(args, '--poll-interval-ms', numberValue(logWatch.pollIntervalMs, 1000));
  addValue(args, '--console-limit', numberValue(logWatch.consoleLimit, 200));
  addValue(args, '--dom-selector', stringValue(assertions.domSelector, '.workspace-leaf.mod-active'));
  addValue(args, '--cdp-host', reload.cdp?.host);
  addValue(args, '--cdp-port', reload.cdp?.port);
  addValue(args, '--cdp-target-title-contains', reload.cdp?.targetTitleContains);
  addValue(args, '--cdp-reload-delay-ms', reload.cdp?.reloadDelayMs);
  addValue(args, '--cdp-eval-after-reload', reload.cdp?.evalAfterReload);
  if (enabled(scenario, false)) {
    addValue(args, '--scenario-name', scenario.name);
    addValue(args, '--scenario-path', scenario.path);
    addValue(args, '--scenario-command-id', scenario.commandId);
    addValue(args, '--surface-profile', scenario.surfaceProfile);
    addValue(args, '--scenario-sleep-ms', numberValue(scenario.sleepMs, 2000));
  }
  addValue(args, '--assertions', assertions.path);
  addValue(args, '--compare-diagnosis', comparison.baselineDiagnosisPath);
  addSwitch(args, '--dom-text', booleanValue(assertions.domText, false));
  addSwitch(args, '--use-cdp', useCdp);
  addSwitch(args, '--skip-build', !enabled(build, true));
  addSwitch(args, '--skip-deploy', !enabled(deploy, true));
  addSwitch(args, '--skip-reload', !enabled(reload, true));
  addSwitch(args, '--skip-screenshot', !captureEnabled || capture.screenshot === false);
  addSwitch(args, '--skip-dom', !captureEnabled || capture.dom === false);
  return commandFor({
    phase: 'debug-cycle',
    executable: 'bash',
    args,
    cwd,
    platform,
    summary: 'Run the Bash build/deploy/reload/watch cycle.',
  });
}

function buildStateCommands({ spec, platform, cwd, warnings }) {
  const state = asObject(spec.state);
  const runtime = asObject(spec.runtime);
  const commands = [];
  const vaultSnapshotConfig = state.vaultSnapshot;
  const pluginResetConfig = state.pluginReset;
  const vaultSnapshot = asObject(vaultSnapshotConfig);
  const pluginReset = asObject(pluginResetConfig);
  const pluginId = stringValue(runtime.pluginId, '');

  if (enabled(vaultSnapshotConfig, false)) {
    const targets = asArray(vaultSnapshot.targets);
    if (targets.length === 0) {
      warnings.push('state.vaultSnapshot.enabled is true but no targets are configured.');
    } else {
      commands.push(commandFor({
        phase: 'state-snapshot',
        executable: 'node',
        args: [
          path.join(scriptDir, 'obsidian_debug_vault_state.mjs'),
          '--mode',
          'snapshot',
          '--snapshot-dir',
          stringValue(vaultSnapshot.snapshotDir, '.obsidian-debug/vault-state'),
          '--targets',
          targets.join('|'),
          '--allow-missing',
          String(booleanValue(vaultSnapshot.allowMissing, true)),
        ],
        cwd,
        platform,
        summary: 'Snapshot declared vault/plugin state before the debug cycle.',
      }));
    }
  }

  if (enabled(pluginResetConfig, false)) {
    const args = [
      path.join(scriptDir, 'obsidian_debug_reset_state.mjs'),
      '--mode',
      stringValue(pluginReset.mode, 'preview'),
      '--snapshot-dir',
      stringValue(pluginReset.snapshotDir, '.obsidian-debug/plugin-state-reset'),
    ];
    addValue(args, '--state-plan', pluginReset.statePlan);
    addValue(args, '--vault-root', pluginReset.vaultRoot);
    addValue(args, '--plugin-id', pluginId);
    addValue(args, '--plugin-dir', pluginReset.pluginDir);
    const targets = asArray(pluginReset.targets);
    if (targets.length > 0) {
      addValue(args, '--targets', targets.join('|'));
    }
    const recreateFiles = asArray(pluginReset.recreateFiles);
    if (recreateFiles.length > 0) {
      addValue(args, '--recreate-files', recreateFiles.join('|'));
    }
    const recreateDirs = asArray(pluginReset.recreateDirs);
    if (recreateDirs.length > 0) {
      addValue(args, '--recreate-dirs', recreateDirs.join('|'));
    }
    commands.push(commandFor({
      phase: 'state-reset',
      executable: 'node',
      args,
      cwd,
      platform,
      summary: 'Preview or apply declared plugin-local state reset rules.',
    }));
  }

  return commands;
}

function buildRestoreCommands({ spec, platform, cwd }) {
  const state = asObject(spec.state);
  const commands = [];
  const vaultSnapshotConfig = state.vaultSnapshot;
  const pluginResetConfig = state.pluginReset;
  const vaultSnapshot = asObject(vaultSnapshotConfig);
  const pluginReset = asObject(pluginResetConfig);

  if (state.restoreAfterRun === true && enabled(pluginResetConfig, false)) {
    commands.push(commandFor({
      phase: 'state-reset-restore',
      executable: 'node',
      args: [
        path.join(scriptDir, 'obsidian_debug_reset_state.mjs'),
        '--mode',
        'restore',
        '--snapshot-dir',
        stringValue(pluginReset.snapshotDir, '.obsidian-debug/plugin-state-reset'),
      ],
      cwd,
      platform,
      summary: 'Restore plugin-local state after the debug cycle.',
    }));
  }

  if (state.restoreAfterRun === true && enabled(vaultSnapshotConfig, false)) {
    commands.push(commandFor({
      phase: 'state-snapshot-restore',
      executable: 'node',
      args: [
        path.join(scriptDir, 'obsidian_debug_vault_state.mjs'),
        '--mode',
        'restore',
        '--snapshot-dir',
        stringValue(vaultSnapshot.snapshotDir, '.obsidian-debug/vault-state'),
      ],
      cwd,
      platform,
      summary: 'Restore vault/plugin state after the debug cycle.',
    }));
  }

  return commands;
}

function buildProfileCommand({ spec, platform, cwd, cycleCommand }) {
  const profile = asObject(spec.profile);
  if (!enabled(profile, false)) {
    return null;
  }

  return commandFor({
    phase: 'profile',
    executable: 'node',
    args: [
      path.join(scriptDir, 'obsidian_debug_profile.mjs'),
      '--runs',
      String(numberValue(profile.runs, 3)),
      '--cwd',
      cwd,
      '--root-output',
      stringValue(profile.rootOutput, '.obsidian-debug/profile'),
      '--label',
      stringValue(profile.label, 'default'),
      '--mode',
      stringValue(profile.mode, 'warm'),
      '--command',
      cycleCommand.rendered,
    ],
    cwd,
    platform,
    summary: 'Run the configured debug cycle repeatedly and summarize timing variance.',
  });
}

function buildReportCommand({ spec, platform, cwd, cycleOutputDir }) {
  const report = asObject(spec.report);
  if (!enabled(report, false)) {
    return null;
  }

  const profile = asObject(spec.profile);
  const comparison = asObject(spec.comparison);
  const diagnosisPath = stringValue(report.diagnosis, path.join(cycleOutputDir, 'diagnosis.json'));
  const args = [
    path.join(scriptDir, 'obsidian_debug_report.mjs'),
    '--diagnosis',
    diagnosisPath,
    '--output',
    stringValue(report.output, path.join(cycleOutputDir, 'report.html')),
  ];
  const profileSummary = stringValue(report.profile, enabled(profile, false)
    ? path.join(stringValue(profile.rootOutput, '.obsidian-debug/profile'), 'profile-summary.json')
    : '');
  if (profileSummary) {
    addValue(args, '--profile', profileSummary);
  }
  const comparisonPath = stringValue(report.comparison, stringValue(comparison.baselineDiagnosisPath, '')
    ? path.join(cycleOutputDir, 'comparison.json')
    : '');
  if (comparisonPath) {
    addValue(args, '--comparison', comparisonPath);
  }

  return commandFor({
    phase: 'report',
    executable: 'node',
    args,
    cwd,
    platform,
    summary: 'Generate an HTML report from diagnosis, comparison, and profile artifacts.',
  });
}

function buildPlan(spec) {
  const warnings = [];
  const job = asObject(spec.job);
  const runtime = asObject(spec.runtime);
  const profile = asObject(spec.profile);
  const jobId = stringValue(job.id, 'obsidian-debug-job');
  const cwd = path.resolve(cwdOverride || stringValue(runtime.cwd, process.cwd()));
  const profileEnabled = enabled(profile, false);
  const cycleCommand = buildCycleCommand({
    spec,
    platform,
    cwd,
    warnings,
    outputDirOverride: profileEnabled ? '{{outputDir}}' : outputDirOverride,
  });
  const profileCommand = buildProfileCommand({ spec, platform, cwd, cycleCommand });
  const outputDir = outputDirOverride || interpolate(stringValue(runtime.outputDir, `.obsidian-debug/${jobId}`), {
    jobId,
    platform,
  });
  const cycleOutputDir = profileEnabled
    ? path.join(stringValue(profile.rootOutput, '.obsidian-debug/profile'), 'run-01')
    : outputDir;
  const commands = [
    ...buildStateCommands({ spec, platform, cwd, warnings }),
    profileCommand ?? cycleCommand,
  ];
  const reportCommand = buildReportCommand({ spec, platform, cwd, cycleOutputDir });
  if (reportCommand) {
    commands.push(reportCommand);
  }
  commands.push(...buildRestoreCommands({ spec, platform, cwd }));

  return {
    generatedAt: nowIso(),
    jobPath,
    jobId,
    label: stringValue(job.label, jobId),
    platform,
    mode,
    cwd,
    commandCount: commands.length,
    warnings,
    commands,
  };
}

function validateRunPlan(plan) {
  const placeholderPattern = /(your-|\/path\/to|<[^>]+>|\{\{[^}]+\}\})/i;
  const rendered = plan.commands
    .map((command) => {
      if (command.phase !== 'profile') {
        return command.rendered;
      }
      return command.rendered
        .replaceAll('{{outputDir}}', '.obsidian-debug/profile/run-01')
        .replaceAll('{{run}}', '1');
    })
    .join('\n');
  if (placeholderPattern.test(rendered)) {
    throw new Error('Run mode refused a job plan that still contains placeholder values.');
  }
}

function runCommand(command) {
  return new Promise((resolve, reject) => {
    console.error(`\n== ${command.phase} ==`);
    console.error(command.rendered);
    const child = spawn(command.executable, command.args, {
      cwd: command.cwd,
      shell: false,
      windowsHide: true,
      stdio: 'inherit',
    });
    child.on('error', reject);
    child.on('close', (code) => {
      resolve(code ?? 0);
    });
  });
}

async function runPlan(plan) {
  validateRunPlan(plan);
  for (const command of plan.commands) {
    const exitCode = await runCommand(command);
    if (exitCode !== 0) {
      throw new Error(`${command.phase} failed with exit code ${exitCode}`);
    }
  }
}

const plan = buildPlan(jobSpec);
if (outputPath) {
  const resolvedOutput = path.resolve(outputPath);
  await ensureParentDirectory(resolvedOutput);
  await fs.writeFile(resolvedOutput, `${JSON.stringify(plan, null, 2)}\n`, 'utf8');
}

console.log(JSON.stringify(plan, null, 2));

if (mode === 'run') {
  await runPlan(plan);
}
