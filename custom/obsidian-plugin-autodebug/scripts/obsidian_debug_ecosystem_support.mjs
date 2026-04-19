import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';

const DEPENDENCY_FIELDS = ['dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies'];

const TOOL_DEFINITIONS = {
  obsidianDevUtils: {
    label: 'obsidian-dev-utils',
    packageNames: ['obsidian-dev-utils'],
    namePatterns: [/^(dev|build|lint|test|publish)(:|$)/i, /\bobsidian\b/i],
    bodyPatterns: [/obsidian-dev-utils/i],
    absentDetail: 'obsidian-dev-utils is not declared; keep using repo-owned build/dev scripts or the sample scaffold defaults.',
  },
  eslintObsidianmd: {
    label: 'eslint-plugin-obsidianmd',
    packageNames: ['eslint-plugin-obsidianmd'],
    namePatterns: [/^lint(?::|$)/i, /\beslint\b/i],
    bodyPatterns: [/\beslint\b/i, /obsidianmd/i],
    absentDetail: 'eslint-plugin-obsidianmd is not declared; official Obsidian manifest/template lint checks remain optional.',
  },
  wdioObsidianService: {
    label: 'wdio-obsidian-service',
    packageNames: ['wdio-obsidian-service'],
    namePatterns: [/\bwdio\b/i, /\be2e\b/i, /\bobsidian\b/i],
    bodyPatterns: [/\bwdio\b/i, /wdio-obsidian-service/i, /\bwebdriver/i],
    absentDetail: 'wdio-obsidian-service is not declared; CI-capable browser-level Obsidian E2E remains optional.',
  },
  obsidianE2E: {
    label: 'obsidian-e2e',
    packageNames: ['obsidian-e2e'],
    namePatterns: [/\be2e\b/i, /\bintegration\b/i, /\bobsidian\b/i],
    bodyPatterns: [/obsidian-e2e/i, /createPluginTest/i, /\bvitest\b/i],
    absentDetail: 'obsidian-e2e is not declared; Vitest-first Obsidian integration checks remain optional.',
  },
  semanticReleaseObsidianPlugin: {
    label: 'semantic-release-obsidian-plugin',
    packageNames: ['semantic-release-obsidian-plugin'],
    namePatterns: [/\brelease\b/i, /\bpublish\b/i],
    bodyPatterns: [/semantic-release/i, /obsidian-plugin/i],
    absentDetail: 'semantic-release-obsidian-plugin is not declared; release automation remains outside the local autodebug loop.',
  },
};

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

function asRegex(pattern) {
  if (pattern instanceof RegExp) {
    return pattern;
  }

  return new RegExp(String(pattern), 'i');
}

function matchesAnyPattern(patterns, value) {
  const text = String(value ?? '');
  return patterns.some((pattern) => asRegex(pattern).test(text));
}

function collectDeclaredDependencies(packageJson, packageNames) {
  const findings = [];
  for (const field of DEPENDENCY_FIELDS) {
    const dependencies = packageJson?.[field];
    if (!dependencies || typeof dependencies !== 'object' || Array.isArray(dependencies)) {
      continue;
    }

    for (const packageName of packageNames) {
      if (typeof dependencies[packageName] === 'string' && dependencies[packageName].trim().length > 0) {
        findings.push({
          field,
          packageName,
          version: dependencies[packageName].trim(),
        });
      }
    }
  }

  return findings;
}

function rankScript(script) {
  return [
    script.matchesPackage ? 0 : 1,
    script.name.toLowerCase().includes('obsidian') ? 0 : 1,
    script.name.toLowerCase().includes('lint') ? 0 : 1,
    script.name.toLowerCase().includes('test') ? 0 : 1,
    script.name.toLowerCase().includes('e2e') ? 0 : 1,
    script.name.toLowerCase().includes('release') ? 0 : 1,
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

function collectRelevantScripts(packageJson, {
  packageNames = [],
  namePatterns = [],
  bodyPatterns = [],
  allowLooseMatch = false,
} = {}) {
  const scripts = packageJson?.scripts && typeof packageJson.scripts === 'object' && !Array.isArray(packageJson.scripts)
    ? packageJson.scripts
    : {};

  return Object.entries(scripts)
    .filter(([, body]) => typeof body === 'string' && body.trim().length > 0)
    .map(([name, body]) => {
      const normalizedBody = body.trim();
      const matchesPackage = packageNames.some((packageName) => normalizedBody.includes(packageName));
      const matchesName = matchesAnyPattern(namePatterns, name);
      const matchesBody = matchesAnyPattern(bodyPatterns, normalizedBody);
      return {
        name,
        body: normalizedBody,
        matchesPackage,
        matchesName,
        matchesBody,
        tags: uniqueStrings([
          matchesPackage ? 'package' : '',
          matchesName ? 'name' : '',
          matchesBody ? 'body' : '',
        ]),
      };
    })
    .filter((entry) => entry.matchesPackage || (allowLooseMatch && (entry.matchesName || entry.matchesBody)))
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

async function detectPackageTool({
  repoDir,
  packageJson,
  packageJsonPath,
  label,
  packageNames,
  namePatterns = [],
  bodyPatterns = [],
  absentDetail,
}) {
  const resolvedRepoDir = path.resolve(repoDir);
  const packageCandidates = uniqueStrings(packageNames);
  const declaredDependencies = collectDeclaredDependencies(packageJson, packageCandidates);
  const scripts = collectRelevantScripts(packageJson, {
    packageNames: packageCandidates,
    namePatterns,
    bodyPatterns,
    allowLooseMatch: declaredDependencies.length > 0,
  });
  const requireFromRepo = requireFromDirectory(resolvedRepoDir);
  const errors = [];

  for (const candidate of packageCandidates) {
    try {
      const resolvedPath = requireFromRepo.resolve(candidate);
      const detectedPackageJsonPath = await findNearestPackageJson(resolvedPath, resolvedRepoDir);
      const detectedPackageJson = await readJsonIfExists(detectedPackageJsonPath);
      const installedVersion = typeof detectedPackageJson?.version === 'string' ? detectedPackageJson.version : null;
      const declared = declaredDependencies.find((entry) => entry.packageName === candidate) ?? declaredDependencies[0] ?? null;
      return {
        label,
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
      label,
      available: false,
      declared: true,
      repoDir: resolvedRepoDir,
      packageJsonPath,
      moduleName: declared.packageName,
      resolvedPath: null,
      installedPackageJsonPath: null,
      version: declared.version,
      declaredDependencies,
      scripts,
      detail: `${declared.packageName} is declared in package.json (${declared.field}: ${declared.version}) but is not currently installed.`,
      errors,
    };
  }

  return {
    label,
    available: false,
    declared: false,
    repoDir: resolvedRepoDir,
    packageJsonPath,
    moduleName: packageCandidates[0] ?? label,
    resolvedPath: null,
    installedPackageJsonPath: null,
    version: null,
    declaredDependencies,
    scripts,
    detail: absentDetail,
    errors,
  };
}

function detectScriptProbe({
  packageJson,
  label,
  namePatterns = [],
  bodyPatterns = [],
  detailIfPresent,
  detailIfMissing,
}) {
  const scripts = collectRelevantScripts(packageJson, {
    namePatterns,
    bodyPatterns,
    allowLooseMatch: true,
  });

  return {
    label,
    present: scripts.length > 0,
    scripts,
    detail: scripts.length > 0 ? detailIfPresent(scripts) : detailIfMissing,
  };
}

export async function detectEcosystemSupport({
  repoDir = process.cwd(),
} = {}) {
  const resolvedRepoDir = path.resolve(repoDir);
  const packageJsonPath = path.join(resolvedRepoDir, 'package.json');
  const packageJson = await readJsonIfExists(packageJsonPath);

  const tools = Object.fromEntries(await Promise.all(
    Object.entries(TOOL_DEFINITIONS).map(async ([key, definition]) => [
      key,
      await detectPackageTool({
        repoDir: resolvedRepoDir,
        packageJson,
        packageJsonPath,
        ...definition,
      }),
    ]),
  ));

  const pluginEntryValidation = detectScriptProbe({
    packageJson,
    label: 'plugin-entry-validation',
    namePatterns: [/\bplugin[-:_ ]entry\b/i, /\breviewbot\b/i, /\bvalidate[-:_ ]manifest\b/i, /\bmanifest[-:_ ]validate\b/i],
    bodyPatterns: [/validate-plugin-entry/i, /community-plugins\.json/i, /obsidian-releases/i, /plugin[-:_ ]entry/i, /\breviewbot\b/i],
    detailIfPresent: (scripts) => `Found repo-owned plugin entry validation script(s): ${scripts.map((entry) => entry.name).join(', ')}.`,
    detailIfMissing: 'No repo-owned plugin entry validation script was detected; ReviewBot-style manifest/release checks remain optional.',
  });

  return {
    repoDir: resolvedRepoDir,
    packageJsonPath,
    tools,
    scripts: {
      pluginEntryValidation,
    },
  };
}
