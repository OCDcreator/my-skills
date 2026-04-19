import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repoDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const manifestPath = path.join(repoDir, 'manifest.json');
const entryPath = path.join(repoDir, 'reviewbot-plugin-entry.json');
const residuePattern = /\{\{[^}]+\}\}|<%=?[\s\S]*?%>|\bTODO\b|\bPLUGIN_(?:ID|NAME|REPO)\b/i;

function hasResidue(value) {
  if (typeof value === 'string') {
    return residuePattern.test(value);
  }
  if (Array.isArray(value)) {
    return value.some(hasResidue);
  }
  if (value && typeof value === 'object') {
    return Object.values(value).some(hasResidue);
  }
  return false;
}

const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'));
const entry = JSON.parse(await fs.readFile(entryPath, 'utf8'));
const issues = [];

for (const field of ['id', 'name', 'repo', 'branch']) {
  if (typeof entry[field] !== 'string' || entry[field].trim().length === 0) {
    issues.push(`reviewbot-plugin-entry.json is missing ${field}`);
  }
}

if (entry.id !== manifest.id) {
  issues.push(`plugin entry id ${entry.id ?? '(missing)'} does not match manifest id ${manifest.id ?? '(missing)'}`);
}

if (entry.name !== manifest.name) {
  issues.push(`plugin entry name ${entry.name ?? '(missing)'} does not match manifest name ${manifest.name ?? '(missing)'}`);
}

if (hasResidue(manifest)) {
  issues.push('manifest.json still contains template residue');
}

if (hasResidue(entry)) {
  issues.push('reviewbot-plugin-entry.json still contains template residue');
}

if (issues.length > 0) {
  console.error('Plugin-entry validation failed before build:');
  for (const issue of issues) {
    console.error(`- ${issue}`);
  }
  process.exit(1);
}

console.log('Plugin-entry validation passed.');
