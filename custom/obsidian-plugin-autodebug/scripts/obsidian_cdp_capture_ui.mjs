import fs from 'node:fs/promises';
import path from 'node:path';
import {
  connectToCdp,
  ensureParentDirectory,
  getBooleanOption,
  getStringOption,
  hasHelpOption,
  nowIso,
  parseArgs,
  printHelpAndExit,
} from './obsidian_cdp_common.mjs';

const options = parseArgs(process.argv.slice(2));
if (hasHelpOption(options)) {
  printHelpAndExit(`
Usage: node scripts/obsidian_cdp_capture_ui.mjs [options]

Options:
  --host <host> --port <n>            CDP endpoint. Defaults to 127.0.0.1:9222.
  --target-title-contains <text>      Attach to a matching Obsidian window.
  --selector <css>                    DOM selector to capture.
  --html-output <path>                Save matched HTML.
  --text-output <path>                Save matched text.
  --screenshot-output <path>          Save screenshot PNG.
  --summary <path>                    Capture summary JSON output.
  --all <true|false>                  Capture all matches or first match.
`);
}

const host = getStringOption(options, 'host', '127.0.0.1');
const port = Number(getStringOption(options, 'port', '9222'));
const targetUrl = getStringOption(options, 'target-url', 'app://obsidian.md/index.html');
const targetTitleContains = getStringOption(options, 'target-title-contains', '').trim();
const selector = getStringOption(options, 'selector', '.workspace-leaf.mod-active').trim();
const htmlOutput = getStringOption(options, 'html-output');
const textOutput = getStringOption(options, 'text-output');
const screenshotOutput = getStringOption(options, 'screenshot-output');
const summaryPath = getStringOption(
  options,
  'summary',
  path.resolve('.obsidian-debug/cdp-capture-ui.summary.json'),
);
const allMatches = getBooleanOption(options, 'all', true);

const session = await connectToCdp({
  host,
  port,
  targetUrl,
  targetTitleContains,
});

const result = await session.evaluate(`(() => {
  const selector = ${JSON.stringify(selector)};
  const nodes = Array.from(document.querySelectorAll(selector));
  const picked = ${allMatches ? 'nodes' : 'nodes.slice(0, 1)'};
  return {
    count: nodes.length,
    matches: picked.map((node) => ({
      outerHTML: node.outerHTML,
      textContent: node.textContent ?? '',
      display: globalThis.getComputedStyle(node).display,
      visibility: globalThis.getComputedStyle(node).visibility,
      opacity: globalThis.getComputedStyle(node).opacity,
      pointerEvents: globalThis.getComputedStyle(node).pointerEvents,
      computedStyle: {
        display: globalThis.getComputedStyle(node).display,
        visibility: globalThis.getComputedStyle(node).visibility,
        opacity: globalThis.getComputedStyle(node).opacity,
        'pointer-events': globalThis.getComputedStyle(node).pointerEvents,
      },
    })),
  };
})()`);

const value = result?.result?.value ?? { count: 0, matches: [] };

if (htmlOutput) {
  await ensureParentDirectory(htmlOutput);
  await fs.writeFile(
    htmlOutput,
    `${value.matches.map((entry) => entry.outerHTML).join('\n')}\n`,
    'utf8',
  );
}

if (textOutput) {
  await ensureParentDirectory(textOutput);
  await fs.writeFile(
    textOutput,
    `${value.matches.map((entry) => entry.textContent).join('\n\n')}\n`,
    'utf8',
  );
}

if (screenshotOutput) {
  await session.send('Page.bringToFront');
  const shot = await session.send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: true,
  });
  await ensureParentDirectory(screenshotOutput);
  await fs.writeFile(screenshotOutput, Buffer.from(shot.data, 'base64'));
}

await ensureParentDirectory(summaryPath);
await fs.writeFile(
  summaryPath,
  `${JSON.stringify(
    {
      capturedAt: nowIso(),
      host,
      port,
      targetUrl,
      targetTitleContains,
      selector,
      count: value.count,
      matches: value.matches.slice(0, 50).map((entry) => ({
        textContent: String(entry.textContent ?? '').slice(0, 1000),
        display: entry.display,
        visibility: entry.visibility,
        opacity: entry.opacity,
        pointerEvents: entry.pointerEvents,
        computedStyle: entry.computedStyle ?? {},
      })),
      matchesTruncated: value.matches.length > 50,
      htmlOutput: htmlOutput || null,
      textOutput: textOutput || null,
      screenshotOutput: screenshotOutput || null,
    },
    null,
    2,
  )}\n`,
  'utf8',
);

await session.close();
