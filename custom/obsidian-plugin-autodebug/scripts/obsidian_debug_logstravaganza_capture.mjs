import fs from 'node:fs/promises';
import {
  ensureParentDirectory,
  getStringOption,
  hasHelpOption,
  parseArgs,
  printHelpAndExit,
} from './obsidian_cdp_common.mjs';
import { discoverLogstravaganzaCapture } from './obsidian_debug_logstravaganza.mjs';

const options = parseArgs(process.argv.slice(2));
if (hasHelpOption(options)) {
  printHelpAndExit(`
Usage: node scripts/obsidian_debug_logstravaganza_capture.mjs [options]

Options:
  --test-vault-plugin-dir <path>    Target vault plugin directory used to derive the vault root.
  --vault-root <path>               Explicit vault root override.
  --output <path>                   Optional JSON output path.
`);
}

const testVaultPluginDir = getStringOption(options, 'test-vault-plugin-dir', '').trim();
const vaultRoot = getStringOption(options, 'vault-root', '').trim();
const outputPath = getStringOption(options, 'output', '').trim();

const capture = await discoverLogstravaganzaCapture({
  testVaultPluginDir,
  vaultRoot,
});

if (outputPath) {
  await ensureParentDirectory(outputPath);
  await fs.writeFile(outputPath, `${JSON.stringify(capture, null, 2)}\n`, 'utf8');
}

console.log(JSON.stringify(capture, null, 2));
