import fs from 'node:fs/promises';
import path from 'node:path';
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
        repoDir: resolvedRepoDir,
        moduleName: candidate,
        resolvedPath,
        packageJsonPath,
        version,
        via: moduleName && candidate === moduleName ? 'explicit' : 'auto',
        detail: version ? `${candidate} ${version}` : `Resolved ${candidate} from ${resolvedPath}`,
        errors: [],
      };
    } catch (error) {
      errors.push(`${candidate}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  return {
    available: false,
    repoDir: resolvedRepoDir,
    moduleName: moduleName || null,
    resolvedPath: null,
    packageJsonPath: null,
    version: null,
    via: moduleName ? 'explicit' : 'auto',
    detail: `No Playwright module could be resolved from ${resolvedRepoDir}.`,
    errors,
  };
}

export async function loadPlaywrightSupport(options = {}) {
  const detection = await detectPlaywrightSupport(options);
  if (!detection.available || !detection.resolvedPath) {
    const detail = [detection.detail, ...detection.errors].filter(Boolean).join(' ');
    throw new Error(detail || 'Playwright is unavailable.');
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
