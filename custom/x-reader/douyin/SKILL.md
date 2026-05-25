---
name: x-reader/douyin
description: Use when user sends Douyin or 抖音 share text, v.douyin.com links, douyin.com video links, or asks to transcribe, summarize, digest, download, or save a Douyin short video.
---

# Douyin Video Digest

## Overview

Turn Douyin share text or links into transcript + structured summary, then save to the x-reader Obsidian output directory.

Core rule: **do not rely on yt-dlp as the main Douyin path**. Use Douyin-specific tools first.

## When to Use

Use for:
- `v.douyin.com/...`
- `douyin.com/video/...`
- share text containing `复制打开抖音`
- requests like “抖音链接转写”, “总结这个抖音”, “保存这个抖音视频内容”

Do not use for TikTok international URLs unless the tool explicitly supports them.

## Quick Reference

| Goal | Preferred tool | Command |
| --- | --- | --- |
| Direct transcript | `dyt` | `dyt --local --language zh -o /tmp/douyin_transcript.txt "URL"` |
| No-install parse/download | `douyin-mcp-server` via `uvx` | See fallback pipeline |
| Download-only fallback | `dy-cli` via `uvx` | `uvx --from dy-cli dy download "URL" -o /tmp/douyin` |
| Last resort | `yt-dlp` | Not recommended; often fails with `Fresh cookies needed` |

## Pipeline

### Step 0: Extract the URL from share text

```bash
DOUYIN_URL=$(python3 - <<'PY'
import re
text = '''PASTE_SHARE_TEXT_HERE'''
m = re.search(r'https?://[^\s]+', text)
if not m:
    raise SystemExit('No URL found in Douyin share text')
print(m.group(0).rstrip('，。,.;；'))
PY
)
echo "$DOUYIN_URL"
```

### Step 1: Fast path with dyt, if installed

```bash
if command -v dyt >/dev/null 2>&1; then
  dyt --local --language zh \
    --model-path /opt/homebrew/opt/whisper-cpp/models/ggml-small.bin \
    -o /tmp/douyin_transcript.txt \
    "$DOUYIN_URL"
fi
```

If `/tmp/douyin_transcript.txt` exists and is non-empty, skip to Step 4.

### Step 2: No-install fallback with douyin-mcp-server

Use this when `dyt` is absent or fails.

```bash
uvx --from douyin-mcp-server python - <<PY
from douyin_mcp_server.server import get_douyin_download_link
import json
url = "$DOUYIN_URL"
data = json.loads(get_douyin_download_link(url))
if data.get('status') != 'success':
    raise SystemExit(data)
open('/tmp/douyin_info.json', 'w').write(json.dumps(data, ensure_ascii=False, indent=2))
print(data['title'])
print(data['download_url'])
PY
```

Download and extract audio:

```bash
AUDIO_URL=$(python3 - <<'PY'
import json
print(json.load(open('/tmp/douyin_info.json'))['download_url'])
PY
)

curl -L --fail --retry 2 \
  -A 'Mozilla/5.0' \
  -e 'https://www.douyin.com/' \
  -o /tmp/douyin_video.mp4 \
  "$AUDIO_URL"

ffmpeg -y -i /tmp/douyin_video.mp4 -vn -acodec libmp3lame -q:a 5 /tmp/douyin_audio.mp3
```

Transcribe locally:

```bash
/opt/homebrew/bin/whisper-cli \
  -m /opt/homebrew/opt/whisper-cpp/models/ggml-small.bin \
  -l zh \
  --output-txt \
  --output-file /tmp/douyin_transcript \
  /tmp/douyin_audio.mp3
```

### Step 3: Download-only fallback with dy-cli

Use only if Step 2 fails to download media.

```bash
rm -rf /tmp/douyin_download
mkdir -p /tmp/douyin_download
uvx --from dy-cli dy download "$DOUYIN_URL" -o /tmp/douyin_download

VIDEO_FILE=$(python3 - <<'PY'
from pathlib import Path
files = list(Path('/tmp/douyin_download').glob('*.mp4'))
if not files:
    raise SystemExit('No mp4 downloaded by dy-cli')
print(files[0])
PY
)

ffmpeg -y -i "$VIDEO_FILE" -vn -acodec libmp3lame -q:a 5 /tmp/douyin_audio.mp3

/opt/homebrew/bin/whisper-cli \
  -m /opt/homebrew/opt/whisper-cpp/models/ggml-small.bin \
  -l zh \
  --output-txt \
  --output-file /tmp/douyin_transcript \
  /tmp/douyin_audio.mp3
```

Before continuing, verify the transcript exists:

```bash
if [ ! -s /tmp/douyin_transcript.txt ]; then
  echo "❌ Douyin transcription failed: dyt, douyin-mcp-server, and dy-cli paths did not produce /tmp/douyin_transcript.txt"
  echo "Ask the user for a fresh share link, or try opening the link in a browser to confirm it is still available."
  exit 1
fi
```

### Step 4: Summarize and save

Read `/tmp/douyin_transcript.txt` produced by `dyt` or `whisper.cpp`, then produce the standard x-reader video digest. Get the title from `/tmp/douyin_info.json` when available; otherwise use the Douyin share text title or the downloaded filename.

```markdown
## 📱 Douyin Digest

**Title**: [title]

**Source**: [Douyin URL]

### Overview
[1-2 sentence summary]

### Key Points
1. ...

### Action Items
- ...

---

## 原始转录

[transcript]
```

Save to:

```bash
OUTPUT_DIR="/Volumes/SDD2T/obsidian-vault-write/技术学习/转录总结"
mkdir -p "$OUTPUT_DIR"
```

Use Obsidian-compatible frontmatter with `source_url`, `platform: Douyin`, and `tags: [转录, douyin]`.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Sending Douyin to generic `x-reader/video` yt-dlp flow | Use this skill instead |
| Assuming Chrome cookies solve Douyin | Cookies may be present and yt-dlp can still fail |
| Forgetting share text contains noise around the URL | Extract the first `https://...` URL before running tools |
| Running Whisper on stale `/tmp/media_audio.*` | Use `/tmp/douyin_*` paths and verify file timestamps/sizes |
| Treating `douyin-mcp-server` ASR as required | Only use it for parsing/download; local `whisper.cpp` handles transcription |

## Verified Local Result

The `v.douyin.com` share-link path was verified with:
- `douyin-mcp-server` via `uvx` for title + download URL
- `curl` download of the MP4
- `ffmpeg` MP3 extraction
- `whisper.cpp` local Chinese transcription
- `dy-cli` via `uvx` as download fallback
- `dyt` from source with `--local --language zh`
