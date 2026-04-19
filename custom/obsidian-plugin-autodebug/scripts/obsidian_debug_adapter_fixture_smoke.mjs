import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { generateQualityGateTemplates } from './obsidian_debug_ci_templates.mjs';

const toolRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const scriptRoot = path.join(toolRoot, 'scripts');

const FIXTURES = [
  {
    id: 'testing-framework-smoke-plugin',
    doctorCheckId: 'testing-framework-scripts',
    expectedScript: 'test:obsidian',
    expectedDefaultField: 'testingFrameworkScript',
    expectedRepoOwnedPath: 'autodebug/ci/obsidian-testing-framework.config.mjs',
  },
  {
    id: 'obsidian-e2e-smoke-plugin',
    doctorCheckId: 'obsidian-e2e-scripts',
    expectedScript: 'test:obsidian-e2e',
    expectedDefaultField: 'obsidianE2EScript',
    expectedRepoOwnedPath: 'autodebug/ci/obsidian-e2e.vitest.config.mjs',
  },
  {
    id: 'wdio-obsidian-service-smoke-plugin',
    doctorCheckId: 'wdio-obsidian-service-scripts',
    expectedScript: 'test:obsidian-wdio',
    expectedDefaultField: 'wdioScript',
    expectedRepoOwnedPath: 'autodebug/ci/wdio.obsidian.conf.mjs',
  },
];

function runJson(command, args, { cwd } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd,
      windowsHide: true,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    child.on('error', reject);
    child.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Command failed (${code}): ${command} ${args.join(' ')}\n${stderr || stdout}`));
        return;
      }

      try {
        resolve(JSON.parse(stdout));
      } catch (error) {
        reject(new Error(`Expected JSON output from ${command} ${args.join(' ')}\n${stdout}\n${stderr}\n${error}`));
      }
    });
  });
}

async function main() {
  for (const fixture of FIXTURES) {
    const repoDir = path.join(toolRoot, 'fixtures', fixture.id);
    const jobPath = path.join(repoDir, 'autodebug', 'ci', 'debug-job.sample.json');
    const doctorOutputDir = await fs.mkdtemp(path.join(os.tmpdir(), `${fixture.id}-doctor-`));
    const doctorOutputPath = path.join(doctorOutputDir, 'doctor.json');

    const fixtureStat = await fs.stat(repoDir);
    assert.equal(fixtureStat.isDirectory(), true, `${fixture.id} fixture directory is missing`);

    const doctor = await runJson(
      'node',
      [
        path.join(scriptRoot, 'obsidian_debug_doctor.mjs'),
        '--repo-dir',
        repoDir,
        '--output',
        doctorOutputPath,
      ],
      { cwd: repoDir },
    );
    const doctorCheck = doctor.checks.find((entry) => entry.id === fixture.doctorCheckId);
    assert(doctorCheck, `Doctor check ${fixture.doctorCheckId} is missing for ${fixture.id}`);
    assert.equal(doctorCheck.status, 'pass', `${fixture.id} should expose a passing adapter script lane`);
    assert.equal(doctorCheck.script, fixture.expectedScript, `${fixture.id} should select ${fixture.expectedScript}`);
    assert.equal(doctorCheck.runnable, true, `${fixture.id} should expose a runnable adapter lane`);
    assert.deepEqual(
      doctorCheck.missingRepoOwnedPaths ?? [],
      [],
      `${fixture.id} should not report missing repo-owned adapter files`,
    );
    assert(
      (doctorCheck.repoOwnedPaths ?? []).some((entry) => entry.relativePath === fixture.expectedRepoOwnedPath && entry.exists),
      `${fixture.id} should report ${fixture.expectedRepoOwnedPath} as an existing repo-owned adapter file`,
    );

    const templateOutputDir = await fs.mkdtemp(path.join(os.tmpdir(), `${fixture.id}-ci-`));
    const templateReport = await generateQualityGateTemplates({
      repoDir,
      jobPath,
      outputDir: templateOutputDir,
    });

    assert.equal(
      templateReport.defaults[fixture.expectedDefaultField],
      fixture.expectedScript,
      `${fixture.id} should wire ${fixture.expectedScript} into generated CI defaults`,
    );

    for (const defaultField of ['obsidianE2EScript', 'testingFrameworkScript', 'wdioScript']) {
      if (defaultField === fixture.expectedDefaultField) {
        continue;
      }

      assert.equal(
        templateReport.defaults[defaultField],
        '',
        `${fixture.id} should keep ${defaultField} disabled by default`,
      );
    }

    const readme = await fs.readFile(path.join(templateOutputDir, 'README.md'), 'utf8');
    assert(readme.includes(fixture.expectedScript), `Generated README should mention ${fixture.expectedScript}`);
    assert(
      readme.includes(fixture.expectedRepoOwnedPath),
      `Generated README should mention ${fixture.expectedRepoOwnedPath}`,
    );
  }

  console.log(JSON.stringify({ status: 'pass', fixtureCount: FIXTURES.length }, null, 2));
}

await main();
