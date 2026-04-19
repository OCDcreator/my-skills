import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repoDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const manifestPath = path.join(repoDir, 'manifest.json');
const residuePatterns = [
  /\{\{[^}]+\}\}/,
  /<%=?[\s\S]*?%>/,
  /\bTODO\b/i,
  /\bPLUGIN_(?:ID|NAME|DESCRIPTION)\b/,
];

function collectResidue(value, pointer = '$', findings = []) {
  if (typeof value === 'string') {
    if (residuePatterns.some((pattern) => pattern.test(value))) {
      findings.push(`${pointer}: ${value}`);
    }
    return findings;
  }

  if (Array.isArray(value)) {
    value.forEach((entry, index) => collectResidue(entry, `${pointer}[${index}]`, findings));
    return findings;
  }

  if (value && typeof value === 'object') {
    for (const [key, entry] of Object.entries(value)) {
      collectResidue(entry, `${pointer}.${key}`, findings);
    }
  }

  return findings;
}

const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'));
const findings = collectResidue(manifest);
if (findings.length > 0) {
  console.error('Manifest template residue found before build:');
  for (const finding of findings) {
    console.error(`- ${finding}`);
  }
  process.exit(1);
}

console.log('No manifest template residue found.');
