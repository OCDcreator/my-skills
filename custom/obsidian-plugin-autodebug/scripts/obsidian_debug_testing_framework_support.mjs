import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';

const DEFAULT_MODULE_NAME = 'obsidian-testing-framework';
const DEPENDENCY_FIELDS = ['dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies'];

function uniqueStrings(values) {
  return [...new Set(
    values
      .map((entry) => String(entry ?? '').trim())
      .filter((entry) => entry.length > 0),
  )];
}

function requireFromDirectory(baseDir) {
  return createRequire(path.join(path.resolve(baseDir), 'package.json'));
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

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

function buildModuleCandidates(moduleName = '') {
  return uniqueStrings([moduleName, DEFAULT_MODULE_NAME]);
}

function collectDeclaredDependencies(packageJson, moduleCandidates) {
  const findings = [];
  for (const field of DEPENDENCY_FIELDS) {
    const dependencies = packageJson?.[field];
    if (!dependencies || typeof dependencies !== 'object' || Array.isArray(dependencies)) {
      continue;
    }

    for (const moduleName of moduleCandidates) {
      if (typeof dependencies[moduleName] === 'string' && dependencies[moduleName].trim().length > 0) {
        findings.push({
          field,
          moduleName,
          version: dependencies[moduleName].trim(),
        });
      }
    }
  }

  return findings;
}

function rankScript(script) {
  return [
    script.matchesModule ? 0 : 1,
    script.name.toLowerCase().includes('obsidian') ? 0 : 1,
    script.name.toLowerCase().includes('quality') ? 0 : 1,
    script.name.toLowerCase().includes('smoke') ? 0 : 1,
    script.name.toLowerCase().includes('e2e') ? 0 : 1,
    script.name.toLowerCase(),
  ];
}

function compareRank(left, right) {
  const leftRank = rankScript(left);
  const rightRank = rankScript(right);
  for (let index = 0; index < Math.max(leftRank.length, rightRank.length); index += 1) {
    const leftValue = leftRank[index] ?? 0;
    const rightValue = rightRank[index] ?? 0;
    if (leftValue < rightValue) {
      return -1;
    }
    if (leftValue > rightValue) {
      return 1;
    }
  }
  return 0;
}

function collectRelevantScripts(packageJson, moduleCandidates) {
  const scripts = packageJson?.scripts && typeof packageJson.scripts === 'object' && !Array.isArray(packageJson.scripts)
    ? packageJson.scripts
    : {};

  return Object.entries(scripts)
    .filter(([, body]) => typeof body === 'string' && body.trim().length > 0)
    .map(([name, body]) => {
      const normalizedBody = body.trim();
      const matchesModule = moduleCandidates.some((moduleName) => normalizedBody.includes(moduleName));
      const tags = uniqueStrings([
        matchesModule ? 'module' : '',
        /obsidian/i.test(name) ? 'obsidian' : '',
        /(quality|gate)/i.test(name) ? 'quality-gate' : '',
        /(smoke|e2e|integration)/i.test(name) ? 'e2e' : '',
      ]);
      return {
        name,
        body: normalizedBody,
        matchesModule,
        tags,
      };
    })
    .filter((entry) => entry.matchesModule)
    .sort(compareRank);
}

async function findNearestPackageJson(startPath, stopDir) {
  let currentDir = path.dirname(startPath);
  const resolvedStopDir = path.resolve(stopDir);

  while (currentDir.startsWith(resolvedStopDir)) {
    const packageJsonPath = path.join(currentDir, 'package.json');
    if (await exists(packageJsonPath)) {
      return packageJsonPath;
    }

    const nextDir = path.dirname(currentDir);
    if (nextDir === currentDir) {
      break;
    }
    currentDir = nextDir;
  }

  return null;
}

export async function detectTestingFrameworkSupport({
  repoDir = process.cwd(),
  moduleName = '',
} = {}) {
  const resolvedRepoDir = path.resolve(repoDir);
  const packageJsonPath = path.join(resolvedRepoDir, 'package.json');
  const packageJson = await readJsonIfExists(packageJsonPath);
  const moduleCandidates = buildModuleCandidates(moduleName);
  const declaredDependencies = collectDeclaredDependencies(packageJson, moduleCandidates);
  const scripts = collectRelevantScripts(packageJson, moduleCandidates);
  const requireFromRepo = requireFromDirectory(resolvedRepoDir);
  const errors = [];

  for (const candidate of moduleCandidates) {
    try {
      const resolvedPath = requireFromRepo.resolve(candidate);
      const detectedPackageJsonPath = await findNearestPackageJson(resolvedPath, resolvedRepoDir);
      const detectedPackageJson = await readJsonIfExists(detectedPackageJsonPath);
      const installedVersion = typeof detectedPackageJson?.version === 'string' ? detectedPackageJson.version : null;
      const declared = declaredDependencies.find((entry) => entry.moduleName === candidate) ?? declaredDependencies[0] ?? null;
      return {
        available: true,
        declared: declaredDependencies.length > 0,
        repoDir: resolvedRepoDir,
        packageJsonPath,
        moduleName: candidate,
        resolvedPath,
        installedPackageJsonPath: detectedPackageJsonPath,
        version: installedVersion ?? declared?.version ?? null,
        declaredDependencies,
        scripts,
        detail: installedVersion
          ? `${candidate} ${installedVersion} is installed and resolvable from ${resolvedRepoDir}.`
          : `${candidate} is installed and resolvable from ${resolvedRepoDir}.`,
        errors: [],
      };
    } catch (error) {
      errors.push(`${candidate}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  if (declaredDependencies.length > 0) {
    const declared = declaredDependencies[0];
    return {
      available: false,
      declared: true,
      repoDir: resolvedRepoDir,
      packageJsonPath,
      moduleName: declared.moduleName,
      resolvedPath: null,
      installedPackageJsonPath: null,
      version: declared.version,
      declaredDependencies,
      scripts,
      detail: `${declared.moduleName} is declared in package.json (${declared.field}: ${declared.version}) but is not currently installed.`,
      errors,
    };
  }

  return {
    available: false,
    declared: false,
    repoDir: resolvedRepoDir,
    packageJsonPath,
    moduleName: moduleName || DEFAULT_MODULE_NAME,
    resolvedPath: null,
    installedPackageJsonPath: null,
    version: null,
    declaredDependencies,
    scripts,
    detail: `${moduleName || DEFAULT_MODULE_NAME} is not declared in package.json and remains optional for local-only smoke workflows.`,
    errors,
  };
}
