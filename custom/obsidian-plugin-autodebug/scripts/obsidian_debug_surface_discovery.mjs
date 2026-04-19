import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  connectToCdp,
  ensureParentDirectory,
  getBooleanOption,
  getNumberOption,
  getStringOption,
  hasHelpOption,
  nowIso,
  parseArgs,
  printHelpAndExit,
} from './obsidian_cdp_common.mjs';

function asObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function stringValue(value, fallback = '') {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : fallback;
}

function normalizeText(value) {
  return String(value ?? '').replace(/\s+/g, ' ').trim();
}

function normalizeStringList(...values) {
  const flattened = values.flatMap((entry) => {
    if (Array.isArray(entry)) {
      return entry;
    }
    if (typeof entry === 'string') {
      return [entry];
    }
    return [];
  });

  return [...new Set(
    flattened
      .map((entry) => normalizeText(entry))
      .filter((entry) => entry.length > 0),
  )];
}

function tokenize(value) {
  return normalizeText(value)
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((token) => token.length >= 3);
}

function uniqueBy(list, keyFn) {
  const seen = new Set();
  const result = [];

  for (const item of list) {
    const key = keyFn(item);
    if (!key || seen.has(key)) {
      continue;
    }
    seen.add(key);
    result.push(item);
  }

  return result;
}

async function readJsonOrNull(filePath) {
  if (!filePath) {
    return null;
  }

  try {
    return JSON.parse((await fs.readFile(filePath, 'utf8')).replace(/^\uFEFF/, ''));
  } catch {
    return null;
  }
}

function normalizeAttributes(raw) {
  const source = asObject(raw);
  return Object.fromEntries(
    Object.entries(source)
      .map(([key, value]) => [key, normalizeText(value)])
      .filter(([, value]) => value.length > 0),
  );
}

function normalizeElement(entry, index) {
  const source = asObject(entry);
  const classes = Array.isArray(source.classes)
    ? source.classes
    : typeof source.className === 'string'
      ? source.className.split(/\s+/)
      : [];

  return {
    index,
    tag: stringValue(source.tag, 'div').toLowerCase(),
    id: stringValue(source.id),
    classes: normalizeStringList(classes),
    role: stringValue(source.role),
    text: normalizeText(source.text ?? source.textContent ?? source.label),
    attributes: normalizeAttributes(source.attributes),
  };
}

function buildSelectorFromElement(element) {
  if (element.id) {
    return `#${element.id}`;
  }

  for (const attributeName of ['data-plugin-id', 'data-view-type', 'data-type', 'data-tab', 'aria-label']) {
    const value = element.attributes[attributeName];
    if (value) {
      return `[${attributeName}=${JSON.stringify(value)}]`;
    }
  }

  if (element.classes.length > 0) {
    return `.${element.classes.slice(0, 3).join('.')}`;
  }

  return element.tag;
}

async function collectCdpElements({
  host,
  port,
  targetTitleContains,
  targetUrl = 'app://obsidian.md/index.html',
  selector = 'body *',
  maxElements = 250,
}) {
  const session = await connectToCdp({
    host,
    port,
    targetUrl,
    targetTitleContains,
  });

  try {
    const response = await session.evaluate(`(() => {
      const nodes = Array.from(document.querySelectorAll(${JSON.stringify(selector)})).slice(0, ${Math.max(1, maxElements)});
      return nodes.map((node, index) => {
        const attributes = {};
        for (const name of ['data-type', 'data-view-type', 'data-plugin-id', 'data-tab', 'aria-label']) {
          const value = node.getAttribute?.(name);
          if (value) {
            attributes[name] = value;
          }
        }

        return {
          index,
          tag: node.tagName.toLowerCase(),
          id: node.id || '',
          classes: Array.from(node.classList || []),
          role: node.getAttribute?.('role') || '',
          text: (node.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 240),
          attributes,
        };
      });
    })()`);

    return Array.isArray(response?.result?.value)
      ? response.result.value.map((entry, index) => normalizeElement(entry, index))
      : [];
  } finally {
    await session.close();
  }
}

function containsAnyToken(haystack, tokens) {
  return tokens.some((token) => haystack.includes(token));
}

function inferViewTypesFromElements(elements, pluginTokens) {
  const candidates = [];

  for (const element of elements) {
    for (const attributeName of ['data-view-type', 'data-type']) {
      const value = stringValue(element.attributes[attributeName]);
      if (!value) {
        continue;
      }

      const normalized = value.toLowerCase();
      if (normalized.endsWith('view') || containsAnyToken(normalized, pluginTokens)) {
        candidates.push(value);
      }
    }
  }

  return uniqueBy(candidates, (entry) => entry.toLowerCase());
}

function scoreRootCandidate(element, { pluginTokens, viewTypeTokens, pluginName }) {
  let score = 0;
  const reasons = [];
  const searchable = [
    element.id,
    ...element.classes,
    ...Object.values(element.attributes),
    element.text,
  ]
    .join(' ')
    .toLowerCase();

  if (containsAnyToken(searchable, pluginTokens)) {
    score += 3;
    reasons.push('matched plugin metadata token');
  }

  if (containsAnyToken(searchable, viewTypeTokens)) {
    score += 2;
    reasons.push('matched view type token');
  }

  if (element.attributes['data-plugin-id'] || element.attributes['data-view-type'] || element.attributes['data-type']) {
    score += 2;
    reasons.push('has plugin/view data attribute');
  }

  if (element.classes.some((className) => /(view|panel|container|root|leaf|plugin)/i.test(className))) {
    score += 1;
    reasons.push('container-like class');
  }

  if (pluginName && element.text.toLowerCase().includes(pluginName.toLowerCase())) {
    score += 1;
    reasons.push('visible plugin name text');
  }

  if (['section', 'main', 'div', 'aside'].includes(element.tag) && element.text.length > 0) {
    score += 1;
    reasons.push('container tag with visible text');
  }

  return {
    score,
    reason: reasons.join('; ') || 'generic root-container heuristic',
  };
}

function isHeadingElement(element) {
  return /^h[1-6]$/.test(element.tag)
    || element.role === 'heading'
    || element.classes.some((className) => /(heading|title|setting-item-name|view-header-title)/i.test(className));
}

function isSettingsElement(element, settingsTokens) {
  const searchable = [
    element.id,
    ...element.classes,
    ...Object.values(element.attributes),
    element.text,
  ]
    .join(' ')
    .toLowerCase();
  const hasSettingsShape = element.classes.some((className) => /(setting|tab|preferences|options)/i.test(className))
    || Boolean(element.attributes['data-tab']);

  return hasSettingsShape
    && (containsAnyToken(searchable, settingsTokens) || /(setting|preferences|options)/.test(searchable));
}

function isErrorBannerElement(element) {
  if (!element.text || /^no errors captured/i.test(element.text)) {
    return false;
  }

  const searchable = [
    element.role,
    ...element.classes,
    ...Object.values(element.attributes),
    element.text,
  ]
    .join(' ')
    .toLowerCase();

  return element.role === 'alert'
    || (/(error|warning|notice|banner|callout|alert)/.test(searchable)
      && /(error|failed|warning|unable|unavailable|fatal)/.test(searchable));
}

function isEmptyStateElement(element) {
  const text = element.text.toLowerCase();
  return element.classes.some((className) => /empty/i.test(className))
    || /\b(no\b.+\b(yet|found|available)|nothing to show|empty state|not configured|start by)\b/i.test(text);
}

function createCandidateFromElement(element, extra) {
  return {
    selector: buildSelectorFromElement(element),
    tag: element.tag,
    text: element.text || null,
    attributes: Object.keys(element.attributes).length > 0 ? element.attributes : undefined,
    ...extra,
  };
}

function buildWorkspaceViewOpenExpression(viewType) {
  return `(async () => {
    const workspace = globalThis.app?.workspace;
    if (!workspace) {
      return { ok: false, reason: 'workspace-unavailable' };
    }

    const existing = workspace.getLeavesOfType?.(${JSON.stringify(viewType)})?.[0] ?? null;
    const leaf = existing ?? workspace.getRightLeaf?.(false) ?? null;
    if (!leaf?.setViewState) {
      return { ok: false, reason: 'leaf-unavailable' };
    }

    await leaf.setViewState({ type: ${JSON.stringify(viewType)}, active: true });
    workspace.revealLeaf?.(leaf);
    return {
      ok: true,
      viewType: ${JSON.stringify(viewType)},
      existingLeaf: Boolean(existing),
      leafCount: workspace.getLeavesOfType?.(${JSON.stringify(viewType)})?.length ?? 0,
    };
  })()`;
}

function buildSettingsTabOpenExpression({ settingsTabName = '', settingsTabId = '' }) {
  return `(async () => {
    const setting = globalThis.app?.setting;
    if (!setting?.open) {
      return { ok: false, reason: 'settings-unavailable' };
    }

    setting.open();
    await new Promise((resolve) => setTimeout(resolve, 150));
    const targetId = ${JSON.stringify(settingsTabId)};
    const targetName = ${JSON.stringify(settingsTabName.toLowerCase())};
    const candidates = Array.from(document.querySelectorAll('.vertical-tab-nav-item, [data-tab], .setting-item-name'));
    const matched = candidates.find((node) => {
      const label = (node.textContent ?? '').trim().toLowerCase();
      const tabId = node.getAttribute?.('data-tab') ?? '';
      if (targetId && tabId === targetId) {
        return true;
      }
      return Boolean(targetName) && label.includes(targetName);
    }) ?? null;

    matched?.click?.();
    return {
      ok: Boolean(matched),
      settingsTabId: targetId || null,
      settingsTabName: ${JSON.stringify(settingsTabName)} || null,
      matchedLabel: matched ? (matched.textContent ?? '').trim() : null,
    };
  })()`;
}

function addStrategy(strategies, strategy) {
  const identity = [
    strategy.kind,
    strategy.surface,
    strategy.commandId,
    strategy.viewType,
    strategy.settingsTabId,
    strategy.settingsTabName,
  ]
    .filter(Boolean)
    .join('::')
    .toLowerCase();

  if (!identity || strategies.some((entry) => entry.identity === identity)) {
    return;
  }

  strategies.push({
    identity,
    id: strategy.id || identity.replaceAll('::', ':'),
    priority: strategy.priority,
    kind: strategy.kind,
    source: strategy.source,
    surface: strategy.surface,
    confidence: strategy.confidence,
    description: strategy.description,
    reason: strategy.reason,
    command: strategy.kind === 'obsidian-command' ? 'command' : undefined,
    commandId: strategy.commandId || undefined,
    viewType: strategy.viewType || undefined,
    settingsTabId: strategy.settingsTabId || undefined,
    settingsTabName: strategy.settingsTabName || undefined,
    selector: strategy.selector || undefined,
  });
}

function pushCandidate(list, entry) {
  if (!entry.selector && !entry.text && !entry.settingsTabName && !entry.settingsTabId) {
    return;
  }

  list.push(entry);
}

export async function discoverSurface({
  surfaceProfilePath = '',
  pluginId = '',
  pluginName = '',
  commandId = '',
  cdpHost = '127.0.0.1',
  cdpPort = 0,
  cdpTargetTitleContains = '',
  cdpTargetUrl = 'app://obsidian.md/index.html',
  cdpSelector = 'body *',
  maxCdpElements = 250,
} = {}) {
  const resolvedSurfaceProfilePath = surfaceProfilePath ? path.resolve(surfaceProfilePath) : '';
  const profile = resolvedSurfaceProfilePath
    ? await readJsonOrNull(resolvedSurfaceProfilePath)
    : {};

  if (resolvedSurfaceProfilePath && !profile) {
    throw new Error(`Unable to read surface profile: ${resolvedSurfaceProfilePath}`);
  }

  const plugin = asObject(profile.plugin);
  const metadata = asObject(profile.metadata);
  const commands = Array.isArray(profile.commands) ? profile.commands.map((entry) => asObject(entry)) : [];
  const dom = asObject(profile.dom);

  const resolvedPluginId = stringValue(pluginId, stringValue(plugin.id));
  const resolvedPluginName = stringValue(pluginName, stringValue(plugin.name));
  const explicitCommandId = stringValue(commandId);
  const fallbackCommandId = resolvedPluginId ? `${resolvedPluginId}:open-view` : '';

  const metadataCommandIds = normalizeStringList(
    metadata.preferredOpenCommandIds,
    metadata.openCommandIds,
    metadata.commandIds,
  );
  const metadataViewTypes = normalizeStringList(metadata.viewTypes, metadata.viewType);
  const settingsTabNames = normalizeStringList(metadata.settingsTabNames, metadata.settingsTabName);
  const settingsTabIds = normalizeStringList(metadata.settingsTabIds, metadata.settingsTabId);
  const selectorHints = normalizeStringList(metadata.selectorHints, metadata.rootSelectors);
  const commandEntries = uniqueBy(
    commands
      .map((entry) => ({
        id: stringValue(entry.id),
        label: stringValue(entry.label),
        surface: stringValue(entry.surface, 'view').toLowerCase(),
      }))
      .filter((entry) => entry.id),
    (entry) => entry.id.toLowerCase(),
  );

  let elements = Array.isArray(dom.elements)
    ? dom.elements.map((entry, index) => normalizeElement(entry, index)).filter(Boolean)
    : [];
  let domSource = elements.length > 0 ? 'surface-profile' : 'none';

  if (elements.length === 0 && Number.isFinite(cdpPort) && cdpPort > 0) {
    elements = await collectCdpElements({
      host: cdpHost,
      port: cdpPort,
      targetTitleContains: cdpTargetTitleContains,
      targetUrl: cdpTargetUrl,
      selector: cdpSelector,
      maxElements: maxCdpElements,
    });
    domSource = 'cdp';
  }

  const pluginTokens = uniqueBy(
    [
      ...tokenize(resolvedPluginId),
      ...tokenize(resolvedPluginName),
      ...metadataViewTypes.flatMap((entry) => tokenize(entry)),
      ...selectorHints.flatMap((entry) => tokenize(entry)),
    ],
    (entry) => entry,
  );
  const inferredViewTypes = inferViewTypesFromElements(elements, pluginTokens);
  const viewTypeTokens = uniqueBy(
    [...metadataViewTypes, ...inferredViewTypes].flatMap((entry) => tokenize(entry)),
    (entry) => entry,
  );
  const settingsTokens = uniqueBy(
    [
      ...settingsTabNames.flatMap((entry) => tokenize(entry)),
      ...settingsTabIds.flatMap((entry) => tokenize(entry)),
      ...tokenize(`${resolvedPluginName} settings preferences options`),
    ],
    (entry) => entry,
  );

  const strategies = [];
  for (const declaredCommandId of metadataCommandIds) {
    addStrategy(strategies, {
      priority: 10,
      kind: 'obsidian-command',
      source: 'metadata',
      surface: 'view',
      confidence: 'declared',
      description: `Run declared Obsidian command ${declaredCommandId}.`,
      reason: 'Surface profile metadata declared a preferred open command.',
      commandId: declaredCommandId,
    });
  }

  if (explicitCommandId) {
    addStrategy(strategies, {
      priority: 20,
      kind: 'obsidian-command',
      source: 'scenario',
      surface: 'view',
      confidence: 'explicit',
      description: `Run scenario-provided Obsidian command ${explicitCommandId}.`,
      reason: 'Scenario provided an explicit command id.',
      commandId: explicitCommandId,
    });
  }

  for (const command of commandEntries) {
    const label = `${command.label} ${command.id}`.toLowerCase();
    const surface = command.surface === 'settings' || /settings|preferences|options/.test(label)
      ? 'settings'
      : 'view';
    addStrategy(strategies, {
      priority: surface === 'settings' ? 25 : 30,
      kind: 'obsidian-command',
      source: 'commands',
      surface,
      confidence: 'declared',
      description: `Run catalogued Obsidian command ${command.id}.`,
      reason: 'Surface profile listed an Obsidian command for this plugin surface.',
      commandId: command.id,
    });
  }

  for (const viewType of metadataViewTypes) {
    addStrategy(strategies, {
      priority: 40,
      kind: 'workspace-view-type',
      source: 'metadata',
      surface: 'view',
      confidence: 'declared',
      description: `Open workspace view type ${viewType} through app.workspace.`,
      reason: 'Surface profile metadata declared a view type.',
      viewType,
    });
  }

  for (const inferredViewType of inferredViewTypes) {
    addStrategy(strategies, {
      priority: 80,
      kind: 'workspace-view-type',
      source: domSource === 'cdp' ? 'cdp-dom-heuristic' : 'surface-profile-dom',
      surface: 'view',
      confidence: 'heuristic',
      description: `Open inferred workspace view type ${inferredViewType}.`,
      reason: 'DOM attributes exposed a likely plugin view type.',
      viewType: inferredViewType,
    });
  }

  for (const settingsTabId of settingsTabIds) {
    addStrategy(strategies, {
      priority: 50,
      kind: 'settings-tab',
      source: 'metadata',
      surface: 'settings',
      confidence: 'declared',
      description: `Focus the plugin settings tab ${settingsTabId}.`,
      reason: 'Surface profile metadata declared a settings tab id.',
      settingsTabId,
    });
  }

  for (const settingsTabName of settingsTabNames) {
    addStrategy(strategies, {
      priority: 55,
      kind: 'settings-tab',
      source: 'metadata',
      surface: 'settings',
      confidence: 'declared',
      description: `Focus the plugin settings tab named ${settingsTabName}.`,
      reason: 'Surface profile metadata declared a settings tab name.',
      settingsTabName,
    });
  }

  if (fallbackCommandId) {
    addStrategy(strategies, {
      priority: 70,
      kind: 'obsidian-command',
      source: 'fallback',
      surface: 'view',
      confidence: 'heuristic',
      description: `Try the conventional command id ${fallbackCommandId}.`,
      reason: 'No stronger command metadata existed, so the standard <plugin-id>:open-view pattern is available as a fallback.',
      commandId: fallbackCommandId,
    });
  }

  const rootSelectors = [];
  for (const selector of selectorHints) {
    pushCandidate(rootSelectors, {
      selector,
      source: 'metadata',
      confidence: 'declared',
      reason: 'Surface profile declared a root selector hint.',
    });
  }

  for (const element of elements) {
    const scored = scoreRootCandidate(element, {
      pluginTokens,
      viewTypeTokens,
      pluginName: resolvedPluginName,
    });
    if (scored.score < 3) {
      continue;
    }

    pushCandidate(rootSelectors, createCandidateFromElement(element, {
      source: domSource === 'cdp' ? 'cdp-dom-heuristic' : 'surface-profile-dom',
      confidence: 'heuristic',
      reason: scored.reason,
    }));
  }

  const headings = [];
  for (const element of elements) {
    if (!isHeadingElement(element) || !element.text) {
      continue;
    }

    pushCandidate(headings, {
      selector: buildSelectorFromElement(element),
      text: element.text,
      source: domSource === 'cdp' ? 'cdp-dom-heuristic' : 'surface-profile-dom',
      confidence: 'heuristic',
      reason: 'Heading-like element within the candidate plugin surface.',
    });
  }

  const settingsSurfaces = [];
  for (const settingsTabId of settingsTabIds) {
    pushCandidate(settingsSurfaces, {
      selector: `[data-tab=${JSON.stringify(settingsTabId)}]`,
      settingsTabId,
      source: 'metadata',
      confidence: 'declared',
      reason: 'Surface profile declared a settings tab id.',
    });
  }
  for (const settingsTabName of settingsTabNames) {
    pushCandidate(settingsSurfaces, {
      settingsTabName,
      source: 'metadata',
      confidence: 'declared',
      reason: 'Surface profile declared a settings tab name.',
    });
  }
  for (const element of elements) {
    if (!isSettingsElement(element, settingsTokens)) {
      continue;
    }

    pushCandidate(settingsSurfaces, createCandidateFromElement(element, {
      settingsTabId: stringValue(element.attributes['data-tab']) || undefined,
      settingsTabName: element.text || undefined,
      source: domSource === 'cdp' ? 'cdp-dom-heuristic' : 'surface-profile-dom',
      confidence: 'heuristic',
      reason: 'Settings-like classes, tab ids, or text matched the plugin surface.',
    }));
  }

  const errorBanners = [];
  for (const element of elements) {
    if (!isErrorBannerElement(element)) {
      continue;
    }

    pushCandidate(errorBanners, createCandidateFromElement(element, {
      source: domSource === 'cdp' ? 'cdp-dom-heuristic' : 'surface-profile-dom',
      confidence: 'heuristic',
      reason: 'Error-like banner text or classes were detected.',
    }));
  }

  const emptyStates = [];
  for (const element of elements) {
    if (!isEmptyStateElement(element)) {
      continue;
    }

    pushCandidate(emptyStates, createCandidateFromElement(element, {
      source: domSource === 'cdp' ? 'cdp-dom-heuristic' : 'surface-profile-dom',
      confidence: 'heuristic',
      reason: 'Empty-state-like text or classes were detected.',
    }));
  }

  return {
    generatedAt: nowIso(),
    surfaceProfilePath: resolvedSurfaceProfilePath || null,
    plugin: {
      id: resolvedPluginId || null,
      name: resolvedPluginName || null,
    },
    metadata: {
      fallbackCommandId: fallbackCommandId || null,
      metadataCommandIds,
      metadataViewTypes,
      inferredViewTypes,
      settingsTabIds,
      settingsTabNames,
      selectorHints,
    },
    strategies: [...strategies]
      .sort((left, right) => left.priority - right.priority)
      .map(({ identity, ...strategy }) => strategy),
    discovery: {
      domSource,
      elementCount: elements.length,
      rootSelectors: uniqueBy(rootSelectors, (entry) => entry.selector || entry.text || JSON.stringify(entry)),
      headings: uniqueBy(headings, (entry) => `${entry.selector ?? ''}::${entry.text ?? ''}`),
      settingsSurfaces: uniqueBy(
        settingsSurfaces,
        (entry) => `${entry.selector ?? ''}::${entry.settingsTabId ?? ''}::${entry.settingsTabName ?? ''}`,
      ),
      errorBanners: uniqueBy(errorBanners, (entry) => `${entry.selector ?? ''}::${entry.text ?? ''}`),
      emptyStates: uniqueBy(emptyStates, (entry) => `${entry.selector ?? ''}::${entry.text ?? ''}`),
    },
  };
}

export function selectSurfaceOpenStrategy(
  strategies,
  { cliAvailable = false, cdpAvailable = false, preferFirst = false } = {},
) {
  for (const strategy of strategies) {
    if (strategy.kind === 'obsidian-command') {
      if (cliAvailable || preferFirst) {
        return {
          strategy,
          reason: preferFirst ? 'selected-first-strategy' : 'selected-cli-strategy',
        };
      }
      continue;
    }

    if (strategy.kind === 'workspace-view-type' || strategy.kind === 'settings-tab') {
      if (cdpAvailable || preferFirst) {
        return {
          strategy,
          reason: preferFirst ? 'selected-first-strategy' : 'selected-cdp-strategy',
        };
      }
      continue;
    }
  }

  return {
    strategy: null,
    reason: cliAvailable || cdpAvailable ? 'no-executable-strategy' : 'no-compatible-capability',
  };
}

export { buildWorkspaceViewOpenExpression, buildSettingsTabOpenExpression };

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (hasHelpOption(options)) {
    printHelpAndExit(`
Usage: node scripts/obsidian_debug_surface_discovery.mjs [options]

Options:
  --surface-profile <path>           Surface profile JSON with metadata and DOM hints.
  --plugin-id <id>                   Plugin id for heuristic discovery.
  --plugin-name <name>               Human-readable plugin name.
  --command-id <id>                  Preferred command id hint.
  --cdp-host <host> --cdp-port <n>   Optional CDP DOM discovery endpoint.
  --cli-available true               Allow CLI strategies in selection.
  --dry-run                          Prefer first available strategy without app access.
  --output <path>                    Discovery report JSON output.
`);
  }

  const outputPath = getStringOption(
    options,
    'output',
    path.resolve('.obsidian-debug/surface-discovery.json'),
  );
  const cdpPort = getNumberOption(options, 'cdp-port', 0);
  const dryRun = getBooleanOption(options, 'dry-run', false);
  const discovery = await discoverSurface({
    surfaceProfilePath: getStringOption(options, 'surface-profile', '').trim(),
    pluginId: getStringOption(options, 'plugin-id', '').trim(),
    pluginName: getStringOption(options, 'plugin-name', '').trim(),
    commandId: getStringOption(options, 'command-id', '').trim(),
    cdpHost: getStringOption(options, 'cdp-host', '127.0.0.1'),
    cdpPort,
    cdpTargetTitleContains: getStringOption(options, 'cdp-target-title-contains', '').trim(),
    cdpTargetUrl: getStringOption(options, 'cdp-target-url', 'app://obsidian.md/index.html').trim(),
    cdpSelector: getStringOption(options, 'cdp-selector', 'body *').trim(),
    maxCdpElements: getNumberOption(options, 'max-cdp-elements', 250),
  });

  const selection = selectSurfaceOpenStrategy(discovery.strategies, {
    cliAvailable: getBooleanOption(options, 'cli-available', false),
    cdpAvailable: cdpPort > 0,
    preferFirst: dryRun,
  });
  const report = {
    ...discovery,
    selectedStrategy: selection.strategy,
    selectionReason: selection.reason,
  };

  await ensureParentDirectory(outputPath);
  await fs.writeFile(outputPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  console.log(JSON.stringify(report, null, 2));
}

const directRunPath = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (directRunPath === fileURLToPath(import.meta.url)) {
  await main();
}
