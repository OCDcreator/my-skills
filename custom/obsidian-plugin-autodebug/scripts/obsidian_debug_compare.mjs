import fs from 'node:fs/promises';
import path from 'node:path';
import {
  ensureParentDirectory,
  getStringOption,
  parseArgs,
} from './obsidian_cdp_common.mjs';
import { buildDebugComparison } from './obsidian_debug_compare_core.mjs';

const options = parseArgs(process.argv.slice(2));
const baselinePath = getStringOption(options, 'baseline').trim();
const candidatePath = getStringOption(options, 'candidate').trim();
if (!baselinePath || !candidatePath) {
  throw new Error('--baseline and --candidate are required');
}

const outputPath = path.resolve(getStringOption(
  options,
  'output',
  path.join(path.dirname(path.resolve(candidatePath)), 'comparison.json'),
));

const baseline = JSON.parse((await fs.readFile(baselinePath, 'utf8')).replace(/^\uFEFF/, ''));
const candidate = JSON.parse((await fs.readFile(candidatePath, 'utf8')).replace(/^\uFEFF/, ''));

const comparison = await buildDebugComparison({
  baselinePath,
  baseline,
  candidatePath,
  candidate,
  outputPath,
});

await ensureParentDirectory(outputPath);
await fs.writeFile(outputPath, `${JSON.stringify(comparison, null, 2)}\n`, 'utf8');
console.log(JSON.stringify(comparison, null, 2));
