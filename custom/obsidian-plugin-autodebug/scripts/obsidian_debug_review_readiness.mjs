import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  ensureParentDirectory,
  getStringOption,
  hasHelpOption,
  parseArgs,
  printHelpAndExit,
} from './obsidian_cdp_common.mjs';

const SCAN_EXTENSIONS = new Set([
  '.js',
  '.mjs',
  '.cjs',
  '.ts',
  '.mts',
  '.cts',
  '.jsx',
  '.tsx',
  '.json',
  '.md',
]);
const SKIP_DIRS = new Set([
  '.git',
  'node_modules',
  '.obsidian',
  '.obsidian-debug',
  '.cache',
  '.tmp',
]);
const SAMPLE_PATTERNS = [
  /\bsample[-_ ]plugin\b/i,
  /\bexample[-_ ]plugin\b/i,
  /\brename[-_ ]me\b/i,
  /\byour[-_ ]plugin\b/i,
  /\bhello[-_ ]world\b/i,
  /\btodo\b/i,
  /\bplaceholder\b/i,
];
const CONSOLE_NOISE_PATTERNS = [
  /\bconsole\.(log|info|debug|trace)\s*\(/i,
];
const DANGEROUS_DOM_PATTERNS = [
  /\.innerHTML\s*=/i,
  /\.outerHTML\s*=/i,
  /\binsertAdjacentHTML\s*\(/i,
  /\bdocument\.write\s*\(/i,
];
const NETWORK_PATTERNS = [
  /\bfetch\s*\(/i,
  /\baxios\s*\(/i,
  /\bXMLHttpRequest\b/i,
  /\bWebSocket\s*\(/i,
  /\bhttps?:\/\/[^\s'"`]+/i,
];
const TELEMETRY_PATTERNS = [
  /\btelemetry\b/i,
  /\banalytics\b/i,
  /\btrack(?:ing)?\b/i,
  /\bsentry\b/i,
  /\bposthog\b/i,
  /\bmixpanel\b/i,
  /\bamplitude\b/i,
  /\bsendBeacon\b/i,
];
const DESKTOP_API_PATTERNS = [
  /from\s+['"]node:(child_process|fs|os|path)['"]/i,
  /require\(['"]node:(child_process|fs|os|path)['"]\)/i,
  /from\s+['"]electron['"]/i,
  /require\(['"]electron['"]\)/i,
  /\bprocess\.platform\b/i,
];
const MANIFEST_REQUIRED_FIELDS = ['id', 'name', 'version', 'minAppVersion'];

function normalizePath(value) {
  return String(value ?? '').replaceAll('\\', '/');
}

function toRelativePath(repoDir, filePath) {
  const relativePath = path.relative(repoDir, filePath);
  return normalizePath(relativePath.startsWith('..') ? filePath : relativePath);
}

function asRegex(pattern) {
  if (pattern instanceof RegExp) {
    return new RegExp(pattern.source, pattern.flags.includes('i') ? pattern.flags : `${pattern.flags}i`);
  }
  return new RegExp(String(pattern), 'i');
}

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function readJsonIfExists(filePath) {
  try {
    return JSON.parse((await fs.readFile(filePath, 'utf8')).replace(/^\uFEFF/, ''));
  } catch {
    return null;
  }
}

function firstPatternHit(text, patterns) {
  for (const pattern of patterns) {
    const regex = asRegex(pattern);
    const match = regex.exec(text);
    if (match) {
      return {
        pattern: regex.toString(),
        index: match.index,
        match: String(match[0] ?? '').slice(0, 140),
      };
    }
  }
  return null;
}

function linePreview(text, index) {
  if (!Number.isFinite(index) || index < 0) {
    return { line: null, preview: null };
  }

  const source = String(text ?? '');
  let line = 1;
  let lineStart = 0;
  for (let cursor = 0; cursor < source.length && cursor < index; cursor += 1) {
    if (source[cursor] === '\n') {
      line += 1;
      lineStart = cursor + 1;
    }
  }
  let lineEnd = source.indexOf('\n', lineStart);
  if (lineEnd < 0) {
    lineEnd = source.length;
  }
  const preview = source.slice(lineStart, lineEnd).trim().slice(0, 220);
  return {
    line,
    preview: preview.length > 0 ? preview : null,
  };
}

function matchesSemver(value) {
  return /^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/.test(String(value ?? '').trim());
}

async function collectFiles(rootDir, { maxFiles = 240 } = {}) {
  const files = [];

  async function walk(currentDir) {
    if (files.length >= maxFiles) {
      return;
    }

    let entries = [];
    try {
      entries = await fs.readdir(currentDir, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      if (files.length >= maxFiles) {
        return;
      }

      const absolutePath = path.join(currentDir, entry.name);
      if (entry.isDirectory()) {
        if (SKIP_DIRS.has(entry.name)) {
          continue;
        }
        await walk(absolutePath);
        continue;
      }

      if (!entry.isFile()) {
        continue;
      }

      const extension = path.extname(entry.name).toLowerCase();
      if (!SCAN_EXTENSIONS.has(extension) && !['manifest.json', 'package.json'].includes(entry.name.toLowerCase())) {
        continue;
      }

      files.push(absolutePath);
    }
  }

  await walk(rootDir);
  return files;
}

function createCheck(id, status, detail, {
  heuristic = true,
  severity = status,
  hits = 0,
  evidence = [],
  guidance = [],
} = {}) {
  return {
    id,
    status,
    severity,
    heuristic,
    detail,
    hits,
    evidence,
    guidance,
  };
}

async function scanPatterns({
  repoDir,
  files,
  patterns,
  id,
  errors,
  maxEvidence = 20,
}) {
  const evidence = [];
  let filesRead = 0;

  for (const filePath of files) {
    if (evidence.length >= maxEvidence) {
      break;
    }

    let text = '';
    try {
      const stat = await fs.stat(filePath);
      if (!stat.isFile() || stat.size > 512 * 1024) {
        continue;
      }
      text = await fs.readFile(filePath, 'utf8');
      filesRead += 1;
    } catch (error) {
      errors.push(`Skipped ${toRelativePath(repoDir, filePath)} during ${id}: ${error instanceof Error ? error.message : String(error)}`);
      continue;
    }

    const hit = firstPatternHit(text, patterns);
    if (!hit) {
      continue;
    }

    const preview = linePreview(text, hit.index);
    evidence.push({
      heuristic: true,
      source: toRelativePath(repoDir, filePath),
      pattern: hit.pattern,
      match: hit.match,
      line: preview.line,
      preview: preview.preview,
    });
  }

  return {
    filesRead,
    hits: evidence.length,
    evidence,
  };
}

function collectManifestBasics(manifest) {
  const missingFields = MANIFEST_REQUIRED_FIELDS.filter((field) => {
    const value = manifest?.[field];
    if (typeof value === 'string') {
      return value.trim().length === 0;
    }
    return value === null || value === undefined;
  });

  const versionLooksSemver = matchesSemver(manifest?.version);
  const minAppVersionLooksSemver = matchesSemver(manifest?.minAppVersion);
  const idLooksSample = Boolean(firstPatternHit(String(manifest?.id ?? ''), SAMPLE_PATTERNS));
  const nameLooksSample = Boolean(firstPatternHit(String(manifest?.name ?? ''), SAMPLE_PATTERNS));

  const warnings = [];
  if (missingFields.length > 0) {
    warnings.push(`Missing required manifest fields: ${missingFields.join(', ')}`);
  }
  if (manifest && !versionLooksSemver) {
    warnings.push('manifest.version does not look like semver.');
  }
  if (manifest && !minAppVersionLooksSemver) {
    warnings.push('manifest.minAppVersion does not look like semver.');
  }
  if (idLooksSample || nameLooksSample) {
    warnings.push('Manifest id/name still look sample/template-like.');
  }

  return {
    status: warnings.length > 0 ? 'warn' : 'info',
    detail: warnings.length > 0
      ? `Heuristic manifest-basics warnings: ${warnings.join(' ')}`
      : 'Manifest basics look complete in this heuristic pass.',
    missingFields,
    warnings,
    manifest: {
      id: manifest?.id ?? null,
      name: manifest?.name ?? null,
      version: manifest?.version ?? null,
      minAppVersion: manifest?.minAppVersion ?? null,
      isDesktopOnly: typeof manifest?.isDesktopOnly === 'boolean' ? manifest.isDesktopOnly : null,
      versionLooksSemver,
      minAppVersionLooksSemver,
    },
  };
}

export async function detectReviewReadiness({
  repoDir = process.cwd(),
  maxFiles = 240,
} = {}) {
  const resolvedRepoDir = path.resolve(repoDir);
  const manifestPath = path.join(resolvedRepoDir, 'manifest.json');
  const manifest = await readJsonIfExists(manifestPath);
  const files = await collectFiles(resolvedRepoDir, { maxFiles });
  const errors = [];

  const manifestBasics = collectManifestBasics(manifest);
  const sampleResidue = await scanPatterns({
    repoDir: resolvedRepoDir,
    files,
    patterns: SAMPLE_PATTERNS,
    id: 'sample-residue',
    errors,
  });
  const consoleNoise = await scanPatterns({
    repoDir: resolvedRepoDir,
    files,
    patterns: CONSOLE_NOISE_PATTERNS,
    id: 'console-noise',
    errors,
  });
  const dangerousDomApis = await scanPatterns({
    repoDir: resolvedRepoDir,
    files,
    patterns: DANGEROUS_DOM_PATTERNS,
    id: 'dangerous-dom',
    errors,
  });
  const networkHints = await scanPatterns({
    repoDir: resolvedRepoDir,
    files,
    patterns: NETWORK_PATTERNS,
    id: 'network-hints',
    errors,
  });
  const telemetryHints = await scanPatterns({
    repoDir: resolvedRepoDir,
    files,
    patterns: TELEMETRY_PATTERNS,
    id: 'telemetry-hints',
    errors,
  });
  const desktopOnlyApiHints = await scanPatterns({
    repoDir: resolvedRepoDir,
    files,
    patterns: DESKTOP_API_PATTERNS,
    id: 'desktop-only-hints',
    errors,
  });

  const manifestMissing = !manifest;
  const sampleStatus = sampleResidue.hits > 0 ? 'warn' : 'info';
  const consoleStatus = consoleNoise.hits >= 3 ? 'warn' : 'info';
  const domStatus = dangerousDomApis.hits > 0 ? 'warn' : 'info';
  const networkStatus = telemetryHints.hits > 0 ? 'warn' : networkHints.hits > 0 ? 'info' : 'info';
  const desktopStatus = desktopOnlyApiHints.hits > 0 && manifest?.isDesktopOnly !== true ? 'warn' : 'info';

  const checks = [
    createCheck(
      'manifest-basics',
      manifestMissing ? 'warn' : manifestBasics.status,
      manifestMissing
        ? 'manifest.json is missing or unreadable; heuristic readiness cannot verify basic review metadata.'
        : manifestBasics.detail,
      {
        heuristic: true,
        hits: manifestMissing ? 1 : manifestBasics.warnings.length,
        evidence: manifestMissing ? [] : [{
          heuristic: true,
          source: 'manifest.json',
          missingFields: manifestBasics.missingFields,
          manifest: manifestBasics.manifest,
          warnings: manifestBasics.warnings,
        }],
        guidance: [
          'Heuristic only: this does not represent official Obsidian acceptance.',
          'Keep manifest id/name/version/minAppVersion complete and intentional.',
        ],
      },
    ),
    createCheck(
      'sample-residue',
      sampleStatus,
      sampleResidue.hits > 0
        ? `Heuristic sample/template residue hints detected (${sampleResidue.hits}).`
        : 'No obvious sample/template residue was detected in scanned files.',
      {
        hits: sampleResidue.hits,
        evidence: sampleResidue.evidence,
        guidance: [
          'Replace sample/template placeholders before release submission.',
        ],
      },
    ),
    createCheck(
      'console-logging-noise',
      consoleStatus,
      consoleNoise.hits >= 3
        ? `Heuristic console logging noise appears high (${consoleNoise.hits} file-level hits).`
        : consoleNoise.hits > 0
          ? `Heuristic console logging is present (${consoleNoise.hits} file-level hits); consider keeping release logs minimal.`
          : 'No obvious console logging noise pattern was detected.',
      {
        hits: consoleNoise.hits,
        evidence: consoleNoise.evidence,
        guidance: [
          'Prefer debug flags or gated logging over unconditional noisy logs.',
        ],
      },
    ),
    createCheck(
      'dangerous-dom-html-apis',
      domStatus,
      dangerousDomApis.hits > 0
        ? `Heuristic risky DOM HTML API usage detected (${dangerousDomApis.hits}).`
        : 'No risky DOM HTML API heuristics were detected.',
      {
        hits: dangerousDomApis.hits,
        evidence: dangerousDomApis.evidence,
        guidance: [
          'Prefer safer DOM construction patterns over raw HTML insertion APIs.',
        ],
      },
    ),
    createCheck(
      'network-telemetry-hints',
      networkStatus,
      telemetryHints.hits > 0
        ? `Heuristic telemetry/analytics hints detected (${telemetryHints.hits}); review transparency and consent expectations.`
        : networkHints.hits > 0
          ? `Heuristic network access hints detected (${networkHints.hits}); ensure behavior is intentional and documented.`
          : 'No network/telemetry heuristics were detected in scanned files.',
      {
        hits: networkHints.hits + telemetryHints.hits,
        evidence: [...telemetryHints.evidence, ...networkHints.evidence].slice(0, 20),
        guidance: [
          'Network and telemetry heuristics are advisory only, not policy verdicts.',
        ],
      },
    ),
    createCheck(
      'desktop-only-api-hints',
      desktopStatus,
      desktopOnlyApiHints.hits > 0
        ? manifest?.isDesktopOnly === true
          ? `Desktop-only API heuristics detected (${desktopOnlyApiHints.hits}) and manifest.isDesktopOnly is true.`
          : `Desktop-only API heuristics detected (${desktopOnlyApiHints.hits}) while manifest.isDesktopOnly is not true.`
        : 'No desktop-only API heuristics were detected.',
      {
        hits: desktopOnlyApiHints.hits,
        evidence: desktopOnlyApiHints.evidence,
        guidance: [
          'If desktop-only APIs are required, keep manifest.isDesktopOnly explicit.',
        ],
      },
    ),
  ];

  const warningCount = checks.filter((entry) => entry.status === 'warn').length;
  const infoCount = checks.filter((entry) => entry.status === 'info').length;
  const heuristicHitCount = checks.reduce((count, entry) => count + (entry.hits ?? 0), 0);
  const highRiskCheckIds = checks
    .filter((entry) => entry.id === 'dangerous-dom-html-apis' || entry.id === 'network-telemetry-hints')
    .filter((entry) => entry.status === 'warn')
    .map((entry) => entry.id);

  return {
    generatedAt: new Date().toISOString(),
    heuristicsDisclaimer: 'Heuristic review-readiness hints only; this output is not an official Obsidian acceptance or compliance decision.',
    repoDir: resolvedRepoDir,
    manifestPath,
    scan: {
      maxFiles,
      candidateFiles: files.length,
      scannedExtensions: [...SCAN_EXTENSIONS],
      skippedDirectories: [...SKIP_DIRS],
    },
    checks,
    summary: {
      status: warningCount > 0 ? 'warn' : 'info',
      warningCount,
      infoCount,
      heuristicHitCount,
      highRiskCheckIds,
      notOfficialAcceptance: true,
    },
    errors: errors.slice(0, 50),
  };
}

async function runCli() {
  const options = parseArgs(process.argv.slice(2));
  if (hasHelpOption(options)) {
    printHelpAndExit(`
Usage: node scripts/obsidian_debug_review_readiness.mjs [options]

Options:
  --repo-dir <path>                 Plugin repo directory. Defaults to cwd.
  --output <path>                   Optional JSON output path.
`);
  }

  const repoDir = path.resolve(getStringOption(options, 'repo-dir', process.cwd()));
  const outputPath = getStringOption(options, 'output', '').trim();
  const report = await detectReviewReadiness({
    repoDir,
  });

  if (outputPath) {
    const resolvedOutput = path.resolve(outputPath);
    await ensureParentDirectory(resolvedOutput);
    await fs.writeFile(resolvedOutput, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  }

  console.log(JSON.stringify(report, null, 2));
}

const isDirectRun = process.argv[1]
  && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
if (isDirectRun) {
  await runCli();
}
