---
name: x-reader/browser-fetch
description: Use when a web URL cannot be read by normal fetch tools, appears blocked by Cloudflare/reCAPTCHA/bot detection, needs JavaScript rendering, login state, browser interaction, or a stealth browser fallback before analysis.
---

# Browser Fetch

## Overview

Use CloakBrowser as x-reader's browser-rendered fallback for web pages that normal fetch tools cannot read. This skill extracts page content; `x-reader/analyzer` handles analysis afterward.

Core rule: **try lightweight readers first; use CloakBrowser only when rendering, login state, or anti-bot blocking makes it necessary.**

## When to Use

Use when:
- `webfetch`, `defuddle`, Jina Reader, or `web-reader` returns empty/garbled content
- the page shows Cloudflare, reCAPTCHA, Turnstile, DataDome, bot detection, or “enable JavaScript”
- the content appears only after JavaScript rendering, clicking, scrolling, or logging in
- the user explicitly says “用浏览器打开”, “网页登录后读取”, “被风控拦了”, or “页面读不到”

Do not use for direct audio/video transcription, PDFs, or simple public pages that normal readers already handle.

## Quick Reference

| Situation | Action |
| --- | --- |
| Normal article page | Use `defuddle` / `webfetch` first |
| JS-rendered page | Use CloakBrowser page render |
| Agent/browser-use workflow | Start CloakBrowser with local CDP |
| Needs login/session | Use persistent context profile |
| Cloudflare/challenge page returned | Retry through CloakBrowser, then inspect visible text |

## Pipeline

### Step 0: Confirm fallback is needed

Use this skill only after a lightweight reader fails or the user explicitly asks for browser rendering.

Failure signs:
- content contains `Cloudflare`, `Just a moment`, `captcha`, `Turnstile`, `DataDome`
- content is mostly navigation, empty shell, or “enable JavaScript”
- expected article/body text is missing

### Step 1: Install dependencies when missing

```bash
python3 -m venv /tmp/x-reader-browser-fetch-venv
source /tmp/x-reader-browser-fetch-venv/bin/activate
pip install cloakbrowser beautifulsoup4 markdownify
```

First CloakBrowser launch downloads a Chromium binary. This can take time and disk space.

### Step 2: Render page and extract Markdown

```bash
source /tmp/x-reader-browser-fetch-venv/bin/activate
URL="PASTE_URL_HERE"
python3 - <<'PY'
from pathlib import Path
import os
from cloakbrowser import launch
from markdownify import markdownify as md

URL = os.environ.get('URL') or "PASTE_URL_HERE"
OUT = Path('/tmp/x_reader_browser_fetch.md')

browser = launch(headless=True, humanize=True)
page = browser.new_page()
page.goto(URL, wait_until='networkidle', timeout=60000)
html = page.content()
title = page.title()
text = md(html, heading_style='ATX')
browser.close()

OUT.write_text(f"# {title}\n\nSource: {URL}\n\n{text}", encoding='utf-8')
print(OUT)
PY
```

Then read `/tmp/x_reader_browser_fetch.md` and pass the content to `x-reader/analyzer`.

Before analysis, verify extraction is not still a challenge page:

```bash
python3 - <<'PY'
from pathlib import Path
text = Path('/tmp/x_reader_browser_fetch.md').read_text(errors='ignore')
markers = ['Cloudflare', 'Just a moment', 'captcha', 'reCAPTCHA', 'Turnstile', 'DataDome', 'enable JavaScript']
hits = [m for m in markers if m.lower() in text.lower()]
if len(text.strip()) < 500 or hits:
    raise SystemExit(f'Browser fetch did not produce usable content. Markers={hits}, length={len(text)}')
print('Browser fetch content looks usable:', len(text), 'chars')
PY
```

If CloakBrowser still returns a challenge page, stop and tell the user the page requires manual browser access, valid login state, or a different source URL. Do not analyze the challenge page.

### Step 3: CDP mode for browser-use or Crawl4AI

Use CDP when another tool needs to control the browser.

```python
from cloakbrowser import launch_async

browser = await launch_async(
    headless=True,
    args=["--remote-debugging-port=9243", "--remote-debugging-address=127.0.0.1"],
)

# Connect Crawl4AI/browser-use/Playwright to http://127.0.0.1:9243
```

Security rule: keep CDP bound to `127.0.0.1`; never expose it to public networks.

### Step 4: Persistent login profile

Use this only when the user confirms a logged-in browsing context is needed.

```python
from cloakbrowser import launch_persistent_context

context = launch_persistent_context('/tmp/x-reader-browser-profile', headless=False, humanize=True)
page = context.new_page()
page.goto('PASTE_URL_HERE')
# User may log in manually in headed mode, then rerun extraction later.
context.close()
```

Do not store sensitive profile directories in shared or synced folders unless the user explicitly asks.

## Save Output

For analyzed outputs, save final notes to:

```bash
/Volumes/SDD2T/obsidian-vault-write/技术学习/转录总结
```

Use Obsidian frontmatter with `source_url`, `content_type: WebPage`, `fetch_method: CloakBrowser`, and appropriate tags.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Using CloakBrowser for every URL | Try lightweight readers first |
| Analyzing a challenge page | Check for Cloudflare/captcha markers before analysis |
| Exposing CDP on `0.0.0.0` | Bind to `127.0.0.1` only |
| Saving login profiles in synced folders | Keep profiles in local temp/private paths |
| Expecting CloakBrowser to transcribe videos | Use `x-reader/video` or `x-reader/douyin` |

## Local References

- CloakBrowser repo: `/Volumes/SDD2T/obsidian-vault-write/open-source-project/AI-tools-agents/CloakBrowser`
- Integration research: `/Volumes/SDD2T/obsidian-vault-write/open-source-project/AI-tools-agents/CloakBrowser-x-reader集成研究.md`
