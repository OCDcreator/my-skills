import fs from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import {
  connectToCdp,
  ensureParentDirectory,
  getBooleanOption,
  getNumberOption,
  getStringOption,
  nowIso,
  parseArgs,
} from './obsidian_cdp_common.mjs';
import {
  buildSettingsTabOpenExpression,
  buildWorkspaceViewOpenExpression,
  discoverSurface,
  selectSurfaceOpenStrategy,
} from './obsidian_debug_surface_discovery.mjs';

const options = parseArgs(process.argv.slice(2));
const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const scenarioName = getStringOption(options, 'scenario-name', '').trim();
const explicitScenarioPath = getStringOption(options, 'scenario-path', '').trim();
const pluginId = getStringOption(options, 'plugin-id', '').trim();
const vaultName = getStringOption(options, 'vault-name', '').trim();
const obsidianCommand = getStringOption(options, 'obsidian-command', '').trim();
const scenarioCommandId = getStringOption(options, 'scenario-command-id', '').trim();
const scenarioSleepMs = getNumberOption(options, 'scenario-sleep-ms', 2000);
const surfaceProfilePath = getStringOption(options, 'surface-profile', '').trim();
const cdpHost = getStringOption(options, 'cdp-host', '127.0.0.1').trim();
const cdpPort = getNumberOption(options, 'cdp-port', 0);
const cdpTargetTitleContains = getStringOption(options, 'cdp-target-title-contains', '').trim();
const dryRun = getBooleanOption(options, 'dry-run', false);
const outputPath = getStringOption(
  options,
  'output',
  path.resolve('.obsidian-debug/scenario-report.json'),
);

if (!obsidianCommand && !dryRun) {
  throw new Error('--obsidian-command is required');
}

function resolveScenarioPath() {
  if (explicitScenarioPath) {
    return path.resolve(explicitScenarioPath);
  }
  if (!scenarioName) {
    throw new Error('Either --scenario-name or --scenario-path is required');
  }

  return path.resolve(scriptDirectory, '..', 'scenarios', `${scenarioName}.json`);
}

function substituteTemplate(value, context) {
  if (typeof value !== 'string') {
    return value;
  }

  return value.replace(/\$\{([^}]+)\}/g, (_, key) => {
    const resolved = context[key];
    return resolved === undefined || resolved === null ? '' : String(resolved);
  });
}

function normalizeArgs(args, context) {
  if (!Array.isArray(args)) {
    return [];
  }

  return args.map((entry) => substituteTemplate(entry, context)).filter((entry) => entry.length > 0);
}

function runObsidianCli(command, args) {
  const cliArgs = [];
  if (vaultName) {
    cliArgs.push(`vault=${vaultName}`);
  }
  cliArgs.push(command, ...args);

  const startedAt = nowIso();
  const result = spawnSync(obsidianCommand, cliArgs, {
    encoding: 'utf8',
    windowsHide: true,
  });
  const finishedAt = nowIso();

  return {
    type: 'obsidian-cli',
    command,
    args,
    startedAt,
    finishedAt,
    exitCode: result.status ?? 0,
    stdout: result.stdout ?? '',
    stderr: result.stderr ?? '',
    ok: (result.status ?? 0) === 0,
  };
}

const scenarioPath = resolveScenarioPath();
const scenario = JSON.parse(await fs.readFile(scenarioPath, 'utf8'));
const fallbackCommandId = scenarioCommandId || (pluginId ? `${pluginId}:open-view` : '');
const surfaceDiscovery = await discoverSurface({
  surfaceProfilePath,
  pluginId,
  commandId: scenarioCommandId,
  cdpHost,
  cdpPort: dryRun ? 0 : cdpPort,
  cdpTargetTitleContains,
});
const selectedSurfaceStrategy = selectSurfaceOpenStrategy(surfaceDiscovery.strategies, {
  cliAvailable: obsidianCommand.length > 0,
  cdpAvailable: !dryRun && cdpPort > 0,
  preferFirst: dryRun,
});
const variableContext = {
  pluginId,
  vaultName,
  commandId:
    selectedSurfaceStrategy.strategy?.kind === 'obsidian-command'
      ? selectedSurfaceStrategy.strategy.commandId
      : fallbackCommandId,
  sleepAfterMs: scenarioSleepMs,
  surfaceProfilePath,
};

const executedSteps = [];
let success = true;
let cdpSession = null;

async function getCdpSession() {
  if (cdpSession) {
    return cdpSession;
  }
  if (cdpPort <= 0) {
    throw new Error('CDP execution requires --cdp-port');
  }

  cdpSession = await connectToCdp({
    host: cdpHost,
    port: cdpPort,
    targetTitleContains: cdpTargetTitleContains,
  });
  return cdpSession;
}

async function runSurfaceOpenStep() {
  const startedAt = nowIso();
  const strategy = selectedSurfaceStrategy.strategy;
  if (!strategy) {
    return {
      type: 'surface-open',
      startedAt,
      finishedAt: nowIso(),
      ok: false,
      error: `No executable surface-open strategy was resolved (${selectedSurfaceStrategy.reason}).`,
      selectedStrategy: null,
    };
  }

  if (dryRun) {
    return {
      type: 'surface-open',
      startedAt,
      finishedAt: nowIso(),
      ok: true,
      dryRun: true,
      strategyId: strategy.id,
      strategyKind: strategy.kind,
      strategySource: strategy.source,
      selectedStrategy: strategy,
      selectionReason: selectedSurfaceStrategy.reason,
    };
  }

  if (strategy.kind === 'obsidian-command') {
    const result = runObsidianCli('command', [`id=${strategy.commandId}`]);
    return {
      ...result,
      type: 'surface-open',
      strategyId: strategy.id,
      strategyKind: strategy.kind,
      strategySource: strategy.source,
      selectedStrategy: strategy,
      selectionReason: selectedSurfaceStrategy.reason,
    };
  }

  if (strategy.kind === 'workspace-view-type') {
    try {
      const session = await getCdpSession();
      const response = await session.evaluate(buildWorkspaceViewOpenExpression(strategy.viewType));
      const value = response?.result?.value ?? null;
      return {
        type: 'surface-open',
        startedAt,
        finishedAt: nowIso(),
        ok: value?.ok === true,
        exitCode: value?.ok === true ? 0 : 1,
        result: value,
        strategyId: strategy.id,
        strategyKind: strategy.kind,
        strategySource: strategy.source,
        selectedStrategy: strategy,
        selectionReason: selectedSurfaceStrategy.reason,
      };
    } catch (error) {
      return {
        type: 'surface-open',
        startedAt,
        finishedAt: nowIso(),
        ok: false,
        error: error instanceof Error ? error.message : String(error),
        strategyId: strategy.id,
        strategyKind: strategy.kind,
        strategySource: strategy.source,
        selectedStrategy: strategy,
        selectionReason: selectedSurfaceStrategy.reason,
      };
    }
  }

  if (strategy.kind === 'settings-tab') {
    try {
      const session = await getCdpSession();
      const response = await session.evaluate(buildSettingsTabOpenExpression({
        settingsTabName: strategy.settingsTabName ?? '',
        settingsTabId: strategy.settingsTabId ?? '',
      }));
      const value = response?.result?.value ?? null;
      return {
        type: 'surface-open',
        startedAt,
        finishedAt: nowIso(),
        ok: value?.ok === true,
        exitCode: value?.ok === true ? 0 : 1,
        result: value,
        strategyId: strategy.id,
        strategyKind: strategy.kind,
        strategySource: strategy.source,
        selectedStrategy: strategy,
        selectionReason: selectedSurfaceStrategy.reason,
      };
    } catch (error) {
      return {
        type: 'surface-open',
        startedAt,
        finishedAt: nowIso(),
        ok: false,
        error: error instanceof Error ? error.message : String(error),
        strategyId: strategy.id,
        strategyKind: strategy.kind,
        strategySource: strategy.source,
        selectedStrategy: strategy,
        selectionReason: selectedSurfaceStrategy.reason,
      };
    }
  }

  return {
    type: 'surface-open',
    startedAt,
    finishedAt: nowIso(),
    ok: false,
    error: `Unsupported surface-open strategy kind: ${strategy.kind}`,
    strategyId: strategy.id,
    strategyKind: strategy.kind,
    strategySource: strategy.source,
    selectedStrategy: strategy,
    selectionReason: selectedSurfaceStrategy.reason,
  };
}

try {
  for (const step of scenario.steps ?? []) {
    if (step.type === 'sleep') {
      const ms = Number(substituteTemplate(String(step.ms ?? 0), variableContext)) || 0;
      const startedAt = nowIso();
      if (dryRun) {
        executedSteps.push({
          type: 'sleep',
          ms,
          startedAt,
          finishedAt: nowIso(),
          ok: true,
          dryRun: true,
        });
        continue;
      }
      await new Promise((resolve) => setTimeout(resolve, Math.max(0, ms)));
      executedSteps.push({
        type: 'sleep',
        ms,
        startedAt,
        finishedAt: nowIso(),
        ok: true,
      });
      continue;
    }

    if (step.type === 'obsidian-cli') {
      const command = substituteTemplate(step.command ?? '', variableContext);
      const args = normalizeArgs(step.args, variableContext);
      if (dryRun) {
        executedSteps.push({
          type: 'obsidian-cli',
          command,
          args,
          startedAt: nowIso(),
          finishedAt: nowIso(),
          ok: true,
          dryRun: true,
        });
        continue;
      }
      const result = runObsidianCli(command, args);
      executedSteps.push(result);
      if (!result.ok) {
        success = false;
        break;
      }
      continue;
    }

    if (step.type === 'surface-open') {
      const result = await runSurfaceOpenStep();
      executedSteps.push(result);
      if (!result.ok) {
        success = false;
        break;
      }
      continue;
    }

    executedSteps.push({
      type: step.type ?? 'unknown',
      ok: false,
      error: `Unsupported scenario step type: ${step.type ?? 'unknown'}`,
      startedAt: nowIso(),
      finishedAt: nowIso(),
    });
    success = false;
    break;
  }
} finally {
  if (cdpSession) {
    await cdpSession.close();
  }
}

const report = {
  generatedAt: nowIso(),
  success,
  scenarioName: scenario.name ?? scenarioName ?? path.basename(scenarioPath, '.json'),
  description: scenario.description ?? '',
  scenarioPath,
  obsidianCommand,
  vaultName: vaultName || null,
  pluginId: pluginId || null,
  dryRun,
  variables: variableContext,
  steps: executedSteps,
  surfaceDiscovery: {
    surfaceProfilePath: surfaceDiscovery.surfaceProfilePath,
    selectionReason: selectedSurfaceStrategy.reason,
    selectedStrategy: selectedSurfaceStrategy.strategy,
    strategies: surfaceDiscovery.strategies,
    rootSelectors: surfaceDiscovery.discovery.rootSelectors,
    headings: surfaceDiscovery.discovery.headings,
    settingsSurfaces: surfaceDiscovery.discovery.settingsSurfaces,
    errorBanners: surfaceDiscovery.discovery.errorBanners,
    emptyStates: surfaceDiscovery.discovery.emptyStates,
    domSource: surfaceDiscovery.discovery.domSource,
    elementCount: surfaceDiscovery.discovery.elementCount,
  },
};

await ensureParentDirectory(outputPath);
await fs.writeFile(outputPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
console.log(JSON.stringify(report, null, 2));

if (!success) {
  throw new Error(`Scenario failed: ${report.scenarioName}`);
}
