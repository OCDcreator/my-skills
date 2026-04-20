import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

function uniqueStrings(values) {
  return [...new Set(
    values
      .map((entry) => String(entry ?? '').trim())
      .filter((entry) => entry.length > 0),
  )];
}

function asPackageSpecifier(value) {
  return typeof value === 'string'
    && value.length > 0
    && !value.startsWith('.')
    && !path.isAbsolute(value);
}

async function readJsonIfExists(filePath) {
  if (!filePath) {
    return null;
  }

  try {
    return JSON.parse((await fs.readFile(filePath, 'utf8')).replace(/^\uFEFF/, ''));
  } catch {
    return null;
  }
}

function requireFromDirectory(baseDir) {
  return createRequire(path.join(path.resolve(baseDir), 'package.json'));
}

function mergeModuleNamespace(moduleNamespace) {
  const defaultExport = moduleNamespace?.default;
  if (defaultExport && typeof defaultExport === 'object') {
    return {
      ...defaultExport,
      ...moduleNamespace,
    };
  }
  return moduleNamespace;
}

function quoteToken(token) {
  const text = String(token ?? '');
  return /\s|["']/.test(text)
    ? JSON.stringify(text)
    : text;
}

function renderCommand(tokens = []) {
  return tokens.map((entry) => quoteToken(entry)).join(' ').trim();
}

function tokenizeCommand(commandText) {
  return String(commandText ?? '').match(/"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`|\S+/g) ?? [];
}

function stripOuterQuotes(token) {
  const text = String(token ?? '').trim();
  if (text.length < 2) {
    return text;
  }

  const quote = text[0];
  return quote === text[text.length - 1] && ['"', '\'', '`'].includes(quote)
    ? text.slice(1, -1)
    : text;
}

function normalizeCommandTokens(command) {
  if (Array.isArray(command)) {
    return command.map((entry) => String(entry ?? '').trim()).filter((entry) => entry.length > 0);
  }
  return tokenizeCommand(command).map(stripOuterQuotes).filter((entry) => entry.length > 0);
}

function systemCommand(command) {
  if (process.platform !== 'win32') {
    return command;
  }
  return /\.[a-z0-9]+$/i.test(command) ? command : `${command}.cmd`;
}

function versionFromText(text) {
  const match = String(text ?? '').match(/\b(\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?)\b/);
  return match?.[1] ?? null;
}

async function runCommand(executable, args = [], {
  cwd = process.cwd(),
  env = process.env,
  timeoutMs = 60000,
} = {}) {
  return new Promise((resolve) => {
    const isWindowsCmd = process.platform === 'win32' && /\.cmd$/i.test(executable);
    const child = spawn(
      isWindowsCmd ? (process.env.ComSpec || 'cmd.exe') : executable,
      isWindowsCmd ? ['/d', '/s', '/c', renderCommand([executable, ...args])] : args,
      {
      cwd,
      env,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
      },
    );

    let stdout = '';
    let stderr = '';
    let timedOut = false;
    const timeout = timeoutMs > 0
      ? setTimeout(() => {
        timedOut = true;
        child.kill();
      }, timeoutMs)
      : null;

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    child.on('error', (error) => {
      if (timeout) {
        clearTimeout(timeout);
      }
      resolve({
        ok: false,
        code: null,
        stdout,
        stderr,
        timedOut,
        error: error instanceof Error ? error.message : String(error),
      });
    });
    child.on('close', (code) => {
      if (timeout) {
        clearTimeout(timeout);
      }
      resolve({
        ok: !timedOut && code === 0,
        code,
        stdout,
        stderr,
        timedOut,
        error: '',
      });
    });
  });
}

async function detectPlaywrightModuleSupport({
  repoDir,
  moduleName = '',
} = {}) {
  const resolvedRepoDir = path.resolve(repoDir);
  const requireFromRepo = requireFromDirectory(resolvedRepoDir);
  const errors = [];

  for (const candidate of buildPlaywrightModuleCandidates(moduleName)) {
    try {
      const resolvedPath = requireFromRepo.resolve(candidate);
      const packageJsonPath = asPackageSpecifier(candidate)
        ? requireFromRepo.resolve(`${candidate}/package.json`)
        : null;
      const packageJson = await readJsonIfExists(packageJsonPath);
      const version = typeof packageJson?.version === 'string' ? packageJson.version : null;
      return {
        available: true,
        mode: 'module',
        driverLabel: 'playwright-module',
        repoDir: resolvedRepoDir,
        moduleName: candidate,
        resolvedPath,
        packageJsonPath,
        version,
        via: moduleName && candidate === moduleName ? 'explicit' : 'auto',
        command: [],
        commandText: '',
        detail: version ? `${candidate} ${version}` : `Resolved ${candidate} from ${resolvedPath}`,
        errors: [],
      };
    } catch (error) {
      errors.push(`${candidate}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  return {
    available: false,
    mode: 'module',
    driverLabel: 'playwright-module',
    repoDir: resolvedRepoDir,
    moduleName: moduleName || null,
    resolvedPath: null,
    packageJsonPath: null,
    version: null,
    via: moduleName ? 'explicit' : 'auto',
    command: [],
    commandText: '',
    detail: `No Playwright module could be resolved from ${resolvedRepoDir}.`,
    errors,
  };
}

function buildPlaywrightCliCandidates({
  cliCommand = '',
  allowBootstrap = true,
} = {}) {
  const explicitCommand = normalizeCommandTokens(cliCommand);
  if (explicitCommand.length > 0) {
    return [
      {
        via: 'explicit',
        command: explicitCommand,
      },
    ];
  }

  const candidates = [
    {
      via: 'path',
      command: [systemCommand('playwright-cli')],
    },
    {
      via: 'npx-local',
      command: [systemCommand('npx'), '--no-install', 'playwright-cli'],
    },
  ];

  if (allowBootstrap) {
    candidates.push({
      via: 'npm-exec',
      command: [systemCommand('npm'), 'exec', '--yes', '--package=@playwright/cli@latest', '--', 'playwright-cli'],
    });
  }

  return candidates;
}

async function detectPlaywrightCliSupport({
  repoDir,
  cliCommand = '',
  allowBootstrap = true,
} = {}) {
  const resolvedRepoDir = path.resolve(repoDir);
  const candidates = buildPlaywrightCliCandidates({
    cliCommand,
    allowBootstrap,
  });
  const errors = [];

  for (const candidate of candidates) {
    const [executable, ...args] = candidate.command;
    const probe = await runCommand(executable, [...args, '--version'], {
      cwd: resolvedRepoDir,
    });

    if (probe.ok) {
      const version = versionFromText(`${probe.stdout}\n${probe.stderr}`);
      return {
        available: true,
        mode: 'cli',
        driverLabel: 'playwright-cli',
        repoDir: resolvedRepoDir,
        moduleName: null,
        resolvedPath: null,
        packageJsonPath: null,
        version,
        via: candidate.via,
        command: candidate.command,
        commandText: renderCommand(candidate.command),
        detail: version
          ? `Playwright CLI ${version} is available via ${candidate.via}.`
          : `Playwright CLI is available via ${candidate.via}.`,
        errors: [],
      };
    }

    const detail = [
      renderCommand(candidate.command),
      probe.timedOut ? 'timed out' : '',
      probe.error,
      probe.stderr.trim(),
      probe.stdout.trim(),
    ].filter(Boolean).join(' :: ');
    errors.push(detail);
  }

  return {
    available: false,
    mode: 'cli',
    driverLabel: 'playwright-cli',
    repoDir: resolvedRepoDir,
    moduleName: null,
    resolvedPath: null,
    packageJsonPath: null,
    version: null,
    via: cliCommand ? 'explicit' : (allowBootstrap ? 'auto+bootstrap' : 'auto'),
    command: cliCommand ? normalizeCommandTokens(cliCommand) : [],
    commandText: cliCommand ? renderCommand(normalizeCommandTokens(cliCommand)) : '',
    detail: cliCommand
      ? `Explicit Playwright CLI command is unavailable from ${resolvedRepoDir}.`
      : `No Playwright CLI command is available from ${resolvedRepoDir}.`,
    errors,
  };
}

export function normalizeScenarioAdapter(value, fallback = 'cli') {
  const normalized = String(value ?? '').trim().toLowerCase();
  if (!normalized || normalized === 'auto' || normalized === 'default') {
    return fallback;
  }
  if (normalized === 'cli') {
    return 'cli';
  }
  if (normalized === 'playwright') {
    return 'playwright';
  }
  throw new Error(`Unsupported scenario adapter: ${value}`);
}

export function buildPlaywrightModuleCandidates(moduleName = '') {
  return uniqueStrings([
    moduleName,
    'playwright',
    'playwright-core',
    '@playwright/test',
  ]);
}

export function resolvePlaywrightArtifactPaths({
  outputPath,
  tracePath = '',
  screenshotPath = '',
} = {}) {
  const resolvedOutputPath = path.resolve(outputPath || '.obsidian-debug/scenario-report.json');
  const outputDir = path.dirname(resolvedOutputPath);
  return {
    tracePath: path.resolve(tracePath || path.join(outputDir, 'playwright-trace.zip')),
    screenshotPath: path.resolve(screenshotPath || path.join(outputDir, 'playwright-scenario.png')),
  };
}

export async function detectPlaywrightSupport({
  repoDir = process.cwd(),
  moduleName = '',
  cliCommand = '',
  allowBootstrap = true,
} = {}) {
  const moduleSupport = await detectPlaywrightModuleSupport({
    repoDir,
    moduleName,
  });
  if (moduleSupport.available) {
    return moduleSupport;
  }

  const cliSupport = await detectPlaywrightCliSupport({
    repoDir,
    cliCommand,
    allowBootstrap,
  });
  if (cliSupport.available) {
    return {
      ...cliSupport,
      moduleErrors: moduleSupport.errors,
    };
  }

  const preferCli = normalizeCommandTokens(cliCommand).length > 0;
  return {
    ...moduleSupport,
    mode: preferCli ? 'cli' : 'module',
    driverLabel: preferCli ? 'playwright-cli' : moduleSupport.driverLabel,
    via: preferCli ? cliSupport.via : moduleSupport.via,
    command: cliSupport.command,
    commandText: cliSupport.commandText,
    detail: preferCli
      ? [cliSupport.detail, ...cliSupport.errors].filter(Boolean).join(' ')
      : [moduleSupport.detail, ...moduleSupport.errors].filter(Boolean).join(' '),
    errors: preferCli
      ? [...cliSupport.errors, ...moduleSupport.errors]
      : [...moduleSupport.errors, ...cliSupport.errors],
    moduleErrors: moduleSupport.errors,
    cliErrors: cliSupport.errors,
  };
}

export async function loadPlaywrightSupport(options = {}) {
  const detection = await detectPlaywrightSupport(options);
  if (!detection.available) {
    const detail = [detection.detail, ...detection.errors].filter(Boolean).join(' ');
    throw new Error(detail || 'Playwright is unavailable.');
  }

  if (detection.mode === 'cli') {
    return detection;
  }

  const moduleNamespace = mergeModuleNamespace(
    await import(pathToFileURL(detection.resolvedPath).href),
  );
  const chromium = moduleNamespace?.chromium;
  if (!chromium || typeof chromium.connectOverCDP !== 'function') {
    throw new Error(
      `Resolved ${detection.moduleName ?? 'Playwright'} does not expose chromium.connectOverCDP.`,
    );
  }

  return {
    ...detection,
    moduleNamespace,
    chromium,
  };
}

export async function runPlaywrightCliCommand({
  support,
  args = [],
  repoDir = process.cwd(),
  sessionName = '',
  env = process.env,
  timeoutMs = 60000,
} = {}) {
  if (!support || support.mode !== 'cli' || !Array.isArray(support.command) || support.command.length === 0) {
    throw new Error('Playwright CLI support is unavailable.');
  }

  const [executable, ...baseArgs] = support.command;
  const sessionArgs = sessionName ? [`-s=${sessionName}`] : [];
  const result = await runCommand(executable, [...baseArgs, ...sessionArgs, ...args], {
    cwd: path.resolve(repoDir),
    env,
    timeoutMs,
  });

  if (!result.ok) {
    const attempted = renderCommand([executable, ...baseArgs, ...sessionArgs, ...args]);
    const detail = [
      attempted,
      result.timedOut ? 'timed out' : '',
      result.error,
      result.stderr.trim(),
      result.stdout.trim(),
    ].filter(Boolean).join(' :: ');
    throw new Error(`Playwright CLI command failed: ${detail}`);
  }

  return result;
}

export async function selectPlaywrightPage({
  browser,
  targetTitleContains = '',
  targetUrlPrefix = 'app://obsidian.md',
} = {}) {
  const candidates = [];

  for (const context of browser.contexts()) {
    for (const page of context.pages()) {
      const title = await page.title().catch(() => '');
      const url = page.url();
      candidates.push({
        context,
        page,
        title,
        url,
      });
    }
  }

  const filteredByUrl = candidates.filter((entry) => (
    !targetUrlPrefix
    || typeof entry.url === 'string'
    && entry.url.startsWith(targetUrlPrefix)
  ));
  const scopedCandidates = filteredByUrl.length > 0 ? filteredByUrl : candidates;

  if (targetTitleContains) {
    const titled = scopedCandidates.find((entry) => entry.title.includes(targetTitleContains));
    if (titled) {
      return titled;
    }
  }

  if (scopedCandidates.length > 0) {
    return scopedCandidates[0];
  }

  throw new Error('No existing Playwright page matched the current Obsidian session.');
}
