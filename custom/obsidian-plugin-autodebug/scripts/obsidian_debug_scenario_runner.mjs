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
  hasHelpOption,
  nowIso,
  parseArgs,
  printHelpAndExit,
  resolveObsidianCliCommand,
  withRefreshedWindowsPath,
} from './obsidian_cdp_common.mjs';
import {
  buildSettingsTabOpenExpression,
  buildWorkspaceViewOpenExpression,
  discoverSurface,
  selectSurfaceOpenStrategy,
} from './obsidian_debug_surface_discovery.mjs';
import {
  detectPlaywrightSupport,
  loadPlaywrightSupport,
  normalizeScenarioAdapter,
  resolvePlaywrightArtifactPaths,
  runPlaywrightCliCommand,
  selectPlaywrightPage,
} from './obsidian_debug_playwright_support.mjs';

const options = parseArgs(process.argv.slice(2));
if (hasHelpOption(options)) {
  printHelpAndExit(`
Usage: node scripts/obsidian_debug_scenario_runner.mjs [options]

Common options:
  --scenario-name <name>             Built-in scenario name.
  --scenario-path <path>             Scenario JSON path.
  --plugin-id <id>                   Plugin id for substitutions.
  --obsidian-command <cmd>           Required for CLI-backed steps.
  --vault-name <name>                Vault name for CLI commands.
  --surface-profile <path>           Plugin surface metadata.
  --control-backend <id>             Backend id alias: obsidian-cli, bundled-cdp, playwright-script.
  --adapter <cli|playwright>         Scenario adapter when supported.
  --playwright-cli-command <cmd>     Explicit Playwright CLI command override.
  --playwright-no-bootstrap          Disable npm-based Playwright CLI bootstrap fallback.
  --dry-run                          Resolve strategy without touching Obsidian.
  --output <path>                    Scenario report JSON output.
`);
}

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const scenarioName = getStringOption(options, 'scenario-name', '').trim();
const explicitScenarioPath = getStringOption(options, 'scenario-path', '').trim();
const pluginId = getStringOption(options, 'plugin-id', '').trim();
const vaultName = getStringOption(options, 'vault-name', '').trim();
const obsidianCommand = resolveObsidianCliCommand(getStringOption(options, 'obsidian-command', '').trim());
const scenarioCommandId = getStringOption(options, 'scenario-command-id', '').trim();
const scenarioSleepMs = getNumberOption(options, 'scenario-sleep-ms', 2000);
const surfaceProfilePath = getStringOption(options, 'surface-profile', '').trim();
const cdpHost = getStringOption(options, 'cdp-host', '127.0.0.1').trim();
const cdpPort = getNumberOption(options, 'cdp-port', 0);
const cdpTargetTitleContains = getStringOption(options, 'cdp-target-title-contains', '').trim();
const dryRun = getBooleanOption(options, 'dry-run', false);
const cliAvailable = getBooleanOption(options, 'cli-available', obsidianCommand.length > 0);
const controlBackendOption = getStringOption(options, 'control-backend', '').trim();
const scenarioAdapterOption = getStringOption(
  options,
  'scenario-adapter',
  getStringOption(options, 'adapter', ''),
).trim();
const playwrightModuleNameOption = getStringOption(options, 'playwright-module', '').trim();
const playwrightCliCommandOption = getStringOption(options, 'playwright-cli-command', '').trim();
const playwrightAllowBootstrap = !getBooleanOption(options, 'playwright-no-bootstrap', false);
const playwrightTraceOption = getBooleanOption(options, 'playwright-trace', false);
const playwrightTracePathOption = getStringOption(options, 'playwright-trace-path', '').trim();
const playwrightScreenshotPathOption = getStringOption(options, 'playwright-screenshot-path', '').trim();
const playwrightSelectorTimeoutOption = getNumberOption(options, 'playwright-selector-timeout-ms', 5000);
const outputPath = getStringOption(
  options,
  'output',
  path.resolve('.obsidian-debug/scenario-report.json'),
);

if (!obsidianCommand && cliAvailable && !dryRun) {
  throw new Error('--obsidian-command is required when CLI-backed scenario steps are enabled');
}

function asObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function stringValue(value, fallback = '') {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : fallback;
}

function numberValue(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function booleanValue(value, fallback = false) {
  return typeof value === 'boolean' ? value : fallback;
}

function jsStringLiteral(value) {
  return JSON.stringify(String(value ?? ''));
}

function buildPlaywrightCliSessionName() {
  const segments = [
    'obsidian-debug',
    pluginId || 'session',
    process.pid,
    Date.now().toString(36),
  ];
  return segments.join('-').replace(/[^a-zA-Z0-9._-]+/g, '-');
}

function wrapPlaywrightCliCode(code) {
  const text = String(code ?? '').trim();
  if (/^(async\s+)?\(?\s*page\b/.test(text)) {
    return text;
  }
  return `async page => {\n${text}\n}`;
}

function resolvePlaywrightCliTimeout(actionTimeoutMs = 60000) {
  const parsed = Number(actionTimeoutMs);
  const baseTimeout = Number.isFinite(parsed) ? parsed : 0;
  return Math.max(60000, baseTimeout + 10000);
}

function adapterFromControlBackend(backendId) {
  const normalized = String(backendId ?? '').trim().toLowerCase();
  switch (normalized) {
    case 'obsidian-cli':
    case 'cli':
      return 'cli';
    case 'bundled-cdp':
    case 'cdp':
      return 'cli';
    case 'playwright-script':
    case 'playwright':
      return 'playwright';
    default:
      return '';
  }
}

function defaultBackendForAdapter(adapter) {
  switch (adapter) {
    case 'cli':
      return 'obsidian-cli';
    case 'cdp':
      return 'bundled-cdp';
    case 'playwright':
      return 'playwright-script';
    default:
      return null;
  }
}

async function pathExists(filePath) {
  if (!filePath) {
    return false;
  }

  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
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
  if (!obsidianCommand) {
    throw new Error('Obsidian CLI is unavailable for obsidian-cli scenario steps.');
  }

  const cliArgs = [];
  if (vaultName) {
    cliArgs.push(`vault=${vaultName}`);
  }
  cliArgs.push(command, ...args);

  const startedAt = nowIso();
  const result = spawnSync(obsidianCommand, cliArgs, {
    encoding: 'utf8',
    env: withRefreshedWindowsPath(),
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
const scenarioPlaywright = asObject(scenario.playwright);
const controlBackendAdapter = adapterFromControlBackend(controlBackendOption);
const scenarioAdapter = normalizeScenarioAdapter(
  scenarioAdapterOption
    || controlBackendAdapter
    || stringValue(scenario.adapter)
    || (Object.keys(scenarioPlaywright).length > 0 ? 'playwright' : 'cli'),
);
const selectedControlBackend = controlBackendOption || defaultBackendForAdapter(scenarioAdapter);
const playwrightArtifacts = resolvePlaywrightArtifactPaths({
  outputPath,
  tracePath: playwrightTracePathOption || stringValue(scenarioPlaywright.tracePath),
  screenshotPath: playwrightScreenshotPathOption || stringValue(scenarioPlaywright.screenshotPath),
});
const resolvedPlaywrightModuleName = playwrightModuleNameOption || stringValue(scenarioPlaywright.module);
const resolvedPlaywrightTraceRequested = scenarioAdapter === 'playwright'
  && (playwrightTraceOption || booleanValue(scenarioPlaywright.trace, false));
const resolvedPlaywrightTracePath = resolvedPlaywrightTraceRequested
  ? playwrightArtifacts.tracePath
  : null;
const explicitPlaywrightScreenshotPath = playwrightScreenshotPathOption || stringValue(scenarioPlaywright.screenshotPath);
const resolvedPlaywrightScreenshotPath = explicitPlaywrightScreenshotPath
  ? path.resolve(explicitPlaywrightScreenshotPath)
  : null;
const resolvedPlaywrightSelectorTimeoutMs = numberValue(
  options.has('playwright-selector-timeout-ms')
    ? playwrightSelectorTimeoutOption
    : scenarioPlaywright.selectorTimeoutMs,
  playwrightSelectorTimeoutOption,
);
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
  cliAvailable,
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
  scenarioAdapter,
};

const executedSteps = [];
let success = true;
let cdpSession = null;
let playwrightSetup = null;
let playwrightSupport = null;
let playwrightRuntime = null;
let playwrightTraceStarted = false;
let playwrightTraceCaptured = false;
let playwrightTraceDetail = resolvedPlaywrightTraceRequested ? 'Trace capture is pending.' : 'Trace was not requested.';
let playwrightScreenshotCaptured = false;
let playwrightScreenshotPath = null;
const warnings = [];
if (controlBackendOption && !controlBackendAdapter) {
  warnings.push(`Control backend ${controlBackendOption} cannot be executed by the local scenario runner; use the agent-native MCP/REST client for that backend or choose obsidian-cli, bundled-cdp, or playwright-script.`);
}

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

async function preparePlaywrightSetup() {
  const startedAt = nowIso();
  const support = await detectPlaywrightSupport({
    repoDir: process.cwd(),
    moduleName: resolvedPlaywrightModuleName,
    cliCommand: playwrightCliCommandOption,
    allowBootstrap: playwrightAllowBootstrap,
  });
  playwrightSupport = support;

  if (!support.available) {
    return {
      type: 'playwright-setup',
      startedAt,
      finishedAt: nowIso(),
      ok: false,
      adapter: scenarioAdapter,
      error: [support.detail, ...support.errors].filter(Boolean).join(' '),
      driver: support,
    };
  }

  if (cdpPort <= 0) {
    return {
      type: 'playwright-setup',
      startedAt,
      finishedAt: nowIso(),
      ok: false,
      adapter: scenarioAdapter,
      error: 'Playwright adapter requires --cdp-port so it can attach to the running Obsidian window.',
      driver: support,
    };
  }

  return {
    type: 'playwright-setup',
    startedAt,
    finishedAt: nowIso(),
    ok: true,
    adapter: scenarioAdapter,
    dryRun,
    driver: support,
    cdp: {
      host: cdpHost,
      port: cdpPort,
      targetTitleContains: cdpTargetTitleContains || null,
    },
  };
}

async function runPlaywrightCli(args, {
  extraEnv = {},
  timeoutMs = 60000,
} = {}) {
  const runtime = await getPlaywrightRuntime();
  return runPlaywrightCliCommand({
    support: runtime.support,
    repoDir: process.cwd(),
    sessionName: runtime.sessionName,
    args,
    timeoutMs,
    env: {
      ...process.env,
      ...extraEnv,
    },
  });
}

async function runPlaywrightCliCode(code, timeoutMs = 60000) {
  await runPlaywrightCli(['run-code', wrapPlaywrightCliCode(code)], {
    timeoutMs: resolvePlaywrightCliTimeout(timeoutMs),
  });
}

async function getPlaywrightRuntime() {
  if (playwrightRuntime) {
    return playwrightRuntime;
  }

  const support = await loadPlaywrightSupport({
    repoDir: process.cwd(),
    moduleName: resolvedPlaywrightModuleName,
    cliCommand: playwrightCliCommandOption,
    allowBootstrap: playwrightAllowBootstrap,
  });
  playwrightSupport = support;
  if (support.mode === 'cli') {
    const sessionName = buildPlaywrightCliSessionName();
    await runPlaywrightCliCommand({
      support,
      repoDir: process.cwd(),
      sessionName,
      args: ['attach', `--cdp=http://${cdpHost}:${cdpPort}`],
    });

    if (resolvedPlaywrightTraceRequested) {
      try {
        await runPlaywrightCliCommand({
          support,
          repoDir: process.cwd(),
          sessionName,
          args: [
            'run-code',
            wrapPlaywrightCliCode(
              'await page.context().tracing.start({ screenshots: true, snapshots: true });',
            ),
          ],
          timeoutMs: resolvePlaywrightCliTimeout(),
        });
        playwrightTraceStarted = true;
        playwrightTraceDetail = resolvedPlaywrightTracePath
          ? `Trace capture is enabled at ${resolvedPlaywrightTracePath}.`
          : 'Trace capture is enabled through Playwright CLI.';
      } catch (error) {
        playwrightTraceDetail = `Playwright trace could not start: ${error instanceof Error ? error.message : String(error)}`;
        warnings.push(playwrightTraceDetail);
      }
    }

    playwrightRuntime = {
      support,
      mode: 'cli',
      sessionName,
      context: null,
      page: null,
      browser: null,
      title: '',
      url: `http://${cdpHost}:${cdpPort}`,
    };
    return playwrightRuntime;
  }

  const browser = await support.chromium.connectOverCDP(`http://${cdpHost}:${cdpPort}`);
  const selectedPage = await selectPlaywrightPage({
    browser,
    targetTitleContains: cdpTargetTitleContains,
  });
  selectedPage.page.setDefaultTimeout(Math.max(1, resolvedPlaywrightSelectorTimeoutMs));

  if (resolvedPlaywrightTraceRequested) {
    if (selectedPage.context?.tracing && typeof selectedPage.context.tracing.start === 'function') {
      try {
        await selectedPage.context.tracing.start({
          screenshots: true,
          snapshots: true,
        });
        playwrightTraceStarted = true;
        playwrightTraceDetail = `Trace capture is enabled at ${resolvedPlaywrightTracePath}.`;
      } catch (error) {
        playwrightTraceDetail = `Playwright trace could not start: ${error instanceof Error ? error.message : String(error)}`;
        warnings.push(playwrightTraceDetail);
      }
    } else {
      playwrightTraceDetail = 'Playwright tracing is unavailable on the connected browser context.';
      warnings.push(playwrightTraceDetail);
    }
  }

  playwrightRuntime = {
    support,
    browser,
    context: selectedPage.context,
    page: selectedPage.page,
    title: selectedPage.title,
    url: selectedPage.url,
  };
  return playwrightRuntime;
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

function resolvePlaywrightSelector(step) {
  const selector = substituteTemplate(step.selector ?? step.locator ?? '', variableContext).trim();
  if (!selector) {
    throw new Error(`Scenario step ${step.type ?? 'unknown'} requires a selector.`);
  }
  return selector;
}

function resolveStepTimeoutMs(step, fallback = resolvedPlaywrightSelectorTimeoutMs) {
  const rawValue = substituteTemplate(String(step.timeoutMs ?? ''), variableContext).trim();
  return rawValue.length > 0
    ? numberValue(rawValue, fallback)
    : fallback;
}

async function capturePlaywrightScreenshot({ page, stepPath = '', fullPage = false }) {
  const targetPath = path.resolve(
    stepPath
      ? substituteTemplate(stepPath, variableContext)
      : resolvedPlaywrightScreenshotPath || playwrightArtifacts.screenshotPath,
  );
  await ensureParentDirectory(targetPath);
  const runtime = await getPlaywrightRuntime();
  if (runtime.support.mode === 'cli') {
    const args = [
      'screenshot',
      `--filename=${targetPath}`,
    ];
    if (fullPage) {
      args.push('--full-page');
    }
    await runPlaywrightCli(args);
  } else {
    await page.screenshot({
      path: targetPath,
      fullPage,
    });
  }
  playwrightScreenshotCaptured = true;
  playwrightScreenshotPath = targetPath;
  return targetPath;
}

async function runPlaywrightStep(step) {
  const runtime = await getPlaywrightRuntime();
  const { page } = runtime;
  const useCliDriver = runtime.support.mode === 'cli';
  const startedAt = nowIso();

  if (step.type === 'locator-wait') {
    const selector = resolvePlaywrightSelector(step);
    const state = stringValue(step.state, 'visible');
    const timeout = resolveStepTimeoutMs(step);
    if (useCliDriver) {
      await runPlaywrightCliCode(`const locator = page.locator(${jsStringLiteral(selector)}).first(); await locator.waitFor({ state: ${jsStringLiteral(state)}, timeout: ${timeout} });`, timeout);
    } else {
      await page.locator(selector).first().waitFor({ state, timeout });
    }
    return {
      type: 'locator-wait',
      selector,
      state,
      timeout,
      startedAt,
      finishedAt: nowIso(),
      ok: true,
    };
  }

  if (step.type === 'locator-click') {
    const selector = resolvePlaywrightSelector(step);
    const timeout = resolveStepTimeoutMs(step);
    const button = stringValue(step.button, 'left');
    if (useCliDriver) {
      await runPlaywrightCliCode(`await page.locator(${jsStringLiteral(selector)}).first().click({ timeout: ${timeout}, button: ${jsStringLiteral(button)} });`, timeout);
    } else {
      await page.locator(selector).first().click({
        timeout,
        button,
      });
    }
    return {
      type: 'locator-click',
      selector,
      timeout,
      startedAt,
      finishedAt: nowIso(),
      ok: true,
    };
  }

  if (step.type === 'locator-fill') {
    const selector = resolvePlaywrightSelector(step);
    const value = substituteTemplate(step.value ?? '', variableContext);
    const timeout = resolveStepTimeoutMs(step);
    if (useCliDriver) {
      await runPlaywrightCliCode(`await page.locator(${jsStringLiteral(selector)}).first().fill(${jsStringLiteral(value)}, { timeout: ${timeout} });`, timeout);
    } else {
      await page.locator(selector).first().fill(value, { timeout });
    }
    return {
      type: 'locator-fill',
      selector,
      timeout,
      value,
      startedAt,
      finishedAt: nowIso(),
      ok: true,
    };
  }

  if (step.type === 'locator-press') {
    const selector = resolvePlaywrightSelector(step);
    const key = substituteTemplate(step.key ?? '', variableContext).trim();
    if (!key) {
      throw new Error('locator-press steps require a key.');
    }
    const timeout = resolveStepTimeoutMs(step);
    if (useCliDriver) {
      await runPlaywrightCliCode(`await page.locator(${jsStringLiteral(selector)}).first().press(${jsStringLiteral(key)}, { timeout: ${timeout} });`, timeout);
    } else {
      await page.locator(selector).first().press(key, { timeout });
    }
    return {
      type: 'locator-press',
      selector,
      timeout,
      key,
      startedAt,
      finishedAt: nowIso(),
      ok: true,
    };
  }

  if (step.type === 'locator-assert') {
    const selector = resolvePlaywrightSelector(step);
    const state = stringValue(step.state, 'visible');
    const timeout = resolveStepTimeoutMs(step);
    const expectedCount = step.count === undefined
      ? null
      : numberValue(substituteTemplate(String(step.count), variableContext), NaN);
    const textIncludes = substituteTemplate(step.textIncludes ?? '', variableContext).trim();
    const textMatches = substituteTemplate(step.textMatches ?? '', variableContext).trim();
    const flags = substituteTemplate(step.regexFlags ?? '', variableContext).trim();
    let actualText = '';
    let resolvedCount = null;
    if (useCliDriver) {
      const cliScript = [
        `const selector = ${jsStringLiteral(selector)};`,
        'const locator = page.locator(selector);',
        `await locator.first().waitFor({ state: ${jsStringLiteral(state)}, timeout: ${timeout} });`,
        'const count = await locator.count();',
        Number.isFinite(expectedCount)
          ? `if (count !== ${expectedCount}) { throw new Error(${jsStringLiteral(`Expected ${selector} count=${expectedCount}.`)} + ' Received ' + count + '.'); }`
          : '',
        "const actualText = count > 0 ? String(await locator.first().innerText()).replace(/\\s+/g, ' ').trim() : '';",
        textIncludes
          ? `if (!actualText.includes(${jsStringLiteral(textIncludes)})) { throw new Error(${jsStringLiteral(`Expected ${selector} text to include ${textIncludes}.`)} + ' Received ' + (actualText || '(empty)') + '.'); }`
          : '',
        textMatches
          ? `if (!(new RegExp(${jsStringLiteral(textMatches)}, ${jsStringLiteral(flags)})).test(actualText)) { throw new Error(${jsStringLiteral(`Expected ${selector} text to match /${textMatches}/${flags}.`)} + ' Received ' + (actualText || '(empty)') + '.'); }`
          : '',
      ].filter(Boolean).join(' ');
      await runPlaywrightCliCode(cliScript, timeout);
    } else {
      const locator = page.locator(selector);
      await locator.first().waitFor({ state, timeout });
      resolvedCount = await locator.count();
      if (Number.isFinite(expectedCount) && resolvedCount !== expectedCount) {
        throw new Error(`Expected ${selector} count=${expectedCount}, received ${resolvedCount}.`);
      }
      actualText = resolvedCount > 0
        ? String(await locator.first().innerText()).replace(/\s+/g, ' ').trim()
        : '';
      if (textIncludes && !actualText.includes(textIncludes)) {
        throw new Error(`Expected ${selector} text to include ${textIncludes}, received ${actualText || '(empty)'}.`);
      }
      if (textMatches) {
        const matcher = new RegExp(textMatches, flags);
        if (!matcher.test(actualText)) {
          throw new Error(`Expected ${selector} text to match /${textMatches}/${flags}, received ${actualText || '(empty)'}.`);
        }
      }
    }
    return {
      type: 'locator-assert',
      selector,
      state,
      timeout,
      count: resolvedCount,
      text: actualText,
      startedAt,
      finishedAt: nowIso(),
      ok: true,
    };
  }

  if (step.type === 'page-screenshot') {
    const targetPath = await capturePlaywrightScreenshot({
      page,
      stepPath: stringValue(step.path),
      fullPage: booleanValue(step.fullPage, false),
    });
    return {
      type: 'page-screenshot',
      path: targetPath,
      fullPage: booleanValue(step.fullPage, false),
      startedAt,
      finishedAt: nowIso(),
      ok: true,
    };
  }

  throw new Error(`Unsupported Playwright scenario step type: ${step.type ?? 'unknown'}`);
}

try {
  if (scenarioAdapter === 'playwright') {
    playwrightSetup = await preparePlaywrightSetup();
    executedSteps.push(playwrightSetup);
    if (!playwrightSetup.ok) {
      success = false;
    } else if (!dryRun) {
      try {
        await getPlaywrightRuntime();
      } catch (error) {
        executedSteps.push({
          type: 'playwright-runtime',
          startedAt: nowIso(),
          finishedAt: nowIso(),
          ok: false,
          error: error instanceof Error ? error.message : String(error),
        });
        success = false;
      }
    }
  }

  for (const step of scenario.steps ?? []) {
    if (!success) {
      break;
    }

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

    if (
      scenarioAdapter === 'playwright'
      && ['locator-wait', 'locator-click', 'locator-fill', 'locator-press', 'locator-assert', 'page-screenshot'].includes(step.type)
    ) {
      if (dryRun) {
        const selector = ['page-screenshot'].includes(step.type) ? null : resolvePlaywrightSelector(step);
        executedSteps.push({
          type: step.type,
          selector,
          path: step.type === 'page-screenshot'
            ? path.resolve(
              stringValue(step.path)
                ? substituteTemplate(step.path, variableContext)
                : resolvedPlaywrightScreenshotPath || playwrightArtifacts.screenshotPath,
            )
            : null,
          startedAt: nowIso(),
          finishedAt: nowIso(),
          ok: true,
          dryRun: true,
        });
        continue;
      }

      try {
        const result = await runPlaywrightStep(step);
        executedSteps.push(result);
      } catch (error) {
        executedSteps.push({
          type: step.type,
          startedAt: nowIso(),
          finishedAt: nowIso(),
          ok: false,
          error: error instanceof Error ? error.message : String(error),
        });
        success = false;
        break;
      }
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
      error: scenarioAdapter === 'playwright'
        ? `Unsupported scenario step type for adapter ${scenarioAdapter}: ${step.type ?? 'unknown'}`
        : `Unsupported scenario step type: ${step.type ?? 'unknown'}`,
      startedAt: nowIso(),
      finishedAt: nowIso(),
    });
    success = false;
    break;
  }
} finally {
  if (
    success
    && scenarioAdapter === 'playwright'
    && !dryRun
    && resolvedPlaywrightScreenshotPath
    && !playwrightScreenshotCaptured
  ) {
    try {
      const runtime = await getPlaywrightRuntime();
      await capturePlaywrightScreenshot({
        page: runtime.page,
        stepPath: resolvedPlaywrightScreenshotPath,
      });
    } catch (error) {
      warnings.push(`Playwright screenshot capture failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  if (playwrightRuntime?.support?.mode === 'cli' && playwrightTraceStarted && resolvedPlaywrightTracePath) {
    try {
      await ensureParentDirectory(resolvedPlaywrightTracePath);
      await runPlaywrightCliCode(
        `await page.context().tracing.stop({ path: ${jsStringLiteral(resolvedPlaywrightTracePath)} });`,
      );
      playwrightTraceCaptured = await pathExists(resolvedPlaywrightTracePath);
      playwrightTraceDetail = playwrightTraceCaptured
        ? `Captured Playwright trace at ${resolvedPlaywrightTracePath}.`
        : `Playwright trace stop completed, but ${resolvedPlaywrightTracePath} was not written.`;
    } catch (error) {
      playwrightTraceCaptured = false;
      playwrightTraceDetail = `Playwright trace capture failed: ${error instanceof Error ? error.message : String(error)}`;
      warnings.push(playwrightTraceDetail);
    }
  } else if (playwrightRuntime?.context && playwrightTraceStarted && resolvedPlaywrightTracePath) {
    try {
      await ensureParentDirectory(resolvedPlaywrightTracePath);
      await playwrightRuntime.context.tracing.stop({
        path: resolvedPlaywrightTracePath,
      });
      playwrightTraceCaptured = await pathExists(resolvedPlaywrightTracePath);
      playwrightTraceDetail = playwrightTraceCaptured
        ? `Captured Playwright trace at ${resolvedPlaywrightTracePath}.`
        : `Playwright trace stop completed, but ${resolvedPlaywrightTracePath} was not written.`;
    } catch (error) {
      playwrightTraceCaptured = false;
      playwrightTraceDetail = `Playwright trace capture failed: ${error instanceof Error ? error.message : String(error)}`;
      warnings.push(playwrightTraceDetail);
    }
  }

  if (playwrightRuntime?.support?.mode === 'cli') {
    try {
      await runPlaywrightCli(['close']);
    } catch (error) {
      warnings.push(`Playwright CLI close reported: ${error instanceof Error ? error.message : String(error)}`);
    }
  } else if (playwrightRuntime?.browser) {
    try {
      await playwrightRuntime.browser.close();
    } catch (error) {
      warnings.push(`Playwright browser close reported: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  if (cdpSession) {
    await cdpSession.close();
  }
}

if (playwrightScreenshotPath && !playwrightScreenshotCaptured) {
  playwrightScreenshotCaptured = await pathExists(playwrightScreenshotPath);
}

const report = {
  generatedAt: nowIso(),
  success,
  adapter: scenarioAdapter,
  controlBackend: selectedControlBackend,
  scenarioName: scenario.name ?? scenarioName ?? path.basename(scenarioPath, '.json'),
  description: scenario.description ?? '',
  scenarioPath,
  obsidianCommand,
  vaultName: vaultName || null,
  pluginId: pluginId || null,
  dryRun,
  warnings,
  variables: variableContext,
  steps: executedSteps,
  artifacts: {
    playwrightTrace: resolvedPlaywrightTracePath,
    playwrightScreenshot: playwrightScreenshotPath,
  },
  playwright: scenarioAdapter === 'playwright'
    ? {
        driver: playwrightSupport
          ? {
              available: playwrightSupport.available,
              mode: playwrightSupport.mode ?? null,
              label: playwrightSupport.driverLabel ?? null,
              version: playwrightSupport.version,
              via: playwrightSupport.via,
              command: playwrightSupport.commandText || null,
              detail: playwrightSupport.detail,
              errors: playwrightSupport.errors ?? [],
            }
          : null,
        module: playwrightSupport
          && playwrightSupport.mode === 'module'
          ? {
              available: playwrightSupport.available,
              moduleName: playwrightSupport.moduleName,
              version: playwrightSupport.version,
              resolvedPath: playwrightSupport.resolvedPath,
              detail: playwrightSupport.detail,
              via: playwrightSupport.via,
              errors: playwrightSupport.errors ?? [],
            }
          : null,
        cdp: {
          host: cdpHost,
          port: cdpPort,
          targetTitleContains: cdpTargetTitleContains || null,
        },
        page: playwrightRuntime
          ? {
              title: playwrightRuntime.title,
              url: playwrightRuntime.url,
            }
          : null,
        selectorTimeoutMs: resolvedPlaywrightSelectorTimeoutMs,
        trace: {
          requested: resolvedPlaywrightTraceRequested,
          path: resolvedPlaywrightTracePath,
          captured: playwrightTraceCaptured,
          detail: playwrightTraceDetail,
        },
        screenshot: {
          requested: Boolean(resolvedPlaywrightScreenshotPath || playwrightScreenshotCaptured),
          path: playwrightScreenshotPath,
          captured: playwrightScreenshotCaptured,
          detail: playwrightScreenshotCaptured
            ? `Captured Playwright screenshot at ${playwrightScreenshotPath}.`
            : resolvedPlaywrightScreenshotPath
              ? `Playwright screenshot was requested at ${resolvedPlaywrightScreenshotPath}.`
              : 'Playwright screenshot was not requested.',
        },
      }
    : null,
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
  process.exitCode = 1;
}
