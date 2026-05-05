---
name: x-reader/video
description: Video and podcast transcription with structured summaries. Auto-triggered when a media URL is detected (YouTube, Bilibili, X/Twitter, Xiaoyuzhou, Apple Podcasts, or direct mp3/mp4/m3u8 links). Extracts subtitles or transcribes via Whisper, then outputs formatted digest with key points and timestamps.
---

# Video & Podcast Digest

> Send a video/podcast link → get full transcript + structured summary

## Supported Platforms

| Platform | Type | Subtitles | Whisper Transcription |
|----------|------|-----------|----------------------|
| YouTube | Video | ✅ | ✅ |
| Bilibili | Video | ✅ | ✅ |
| X/Twitter | Video | ❌ | ✅ |
| Xiaoyuzhou (小宇宙) | Podcast | ❌ | ✅ |
| Apple Podcasts | Podcast | ❌ | ✅ |
| Direct links (mp3/mp4/m3u8) | Any | ❌ | ✅ |

## Trigger

Auto-triggered when a media URL is detected:
- YouTube: `youtube.com`, `youtu.be`
- Bilibili: `bilibili.com`, `b23.tv`
- X/Twitter: `x.com`, `twitter.com` (tweets with video)
- Xiaoyuzhou: `xiaoyuzhoufm.com`
- Apple Podcasts: `podcasts.apple.com`
- Direct: `.mp3`, `.mp4`, `.m3u8`, `.m4a`, `.webm`

## Pipeline

```
Step 0: Detect Media Type
    ↓
Step 1: Extract Audio/Subtitles
    ↓
Step 2: Transcribe (if needed)
    ↓
Step 3: Generate Structured Summary
    ↓
Step 4: Save to Output Directory ← 自动保存到 /Volumes/SDD2T/obsidian-vault-write/技术学习/转录总结
```

### Step 0: Detect Media Type

| URL Pattern | Type | Pipeline |
|-------------|------|----------|
| `xiaoyuzhoufm.com/episode/` | Podcast | → Step 1b (Xiaoyuzhou) |
| `podcasts.apple.com` | Podcast | → Step 1c (Apple) |
| `bilibili.com`, `b23.tv` | Video | → Step 1d (Bilibili API) |
| `.mp3`, `.m4a` direct link | Audio | → Step 2b (direct download) |
| Other | Video | → Step 1a (subtitle extraction) |

### Step 1a: Video — Extract Subtitles

```bash
# Clean up temp files
rm -f /tmp/media_sub*.vtt /tmp/media_audio.* /tmp/media_transcript*.txt /tmp/media_segment_*.mp3 /tmp/fresh_audio.* 2>/dev/null || true

# YouTube (prefer English, fallback Chinese)
yt-dlp --skip-download --write-auto-sub --sub-lang "en,zh-Hans" -o "/tmp/media_sub" "VIDEO_URL"

# Bilibili
yt-dlp --skip-download --write-auto-sub --sub-lang "zh-Hans,zh" -o "/tmp/media_sub" "VIDEO_URL"
```

Check for subtitles:
```bash
ls /tmp/media_sub*.vtt 2>/dev/null
```
- **Has subtitles** → Read VTT content, skip to Step 3
- **No subtitles** → Step 2a (download audio)

### Step 1b: Xiaoyuzhou (小宇宙) — Extract Audio URL

```bash
# Extract CDN direct link from __NEXT_DATA__
# Xiaoyuzhou is a Next.js SPA, but initial HTML contains audio URL in __NEXT_DATA__
AUDIO_URL=$(curl -sL -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  "EPISODE_URL" \
  | grep -oE 'https://media\.xyzcdn\.net/[^"]+\.(m4a|mp3)' \
  | head -1)

echo "Audio URL: $AUDIO_URL"

# Download audio
curl -L -o /tmp/media_audio.mp3 "$AUDIO_URL"
```

> If curl extraction is empty (rare), fallback: use Puppeteer/browser to get rendered page and extract.

→ Step 2b (check size & transcribe)

### Step 1c: Apple Podcasts — via yt-dlp

```bash
yt-dlp -f "ba[ext=m4a]/ba/b" --extract-audio --audio-format mp3 --audio-quality 5 \
  -o "/tmp/media_audio.%(ext)s" "APPLE_PODCAST_URL"
```

→ Step 2b (check size & transcribe)

### Step 1d: Bilibili — API Direct Audio Stream

yt-dlp returns 412 for Bilibili even with cookies. Use Bilibili's API instead:

```bash
# 1. Extract BV number from URL
BV="BV1xxxxx"  # Replace with actual BV number

# 2. Get video info (title, duration, CID)
curl -s "https://api.bilibili.com/x/web-interface/view?bvid=$BV" \
  -H "User-Agent: Mozilla/5.0" -H "Referer: https://www.bilibili.com/" \
  | python3 -c "import json,sys; d=json.load(sys.stdin)['data']; print(f\"Title: {d['title']}\nDuration: {d['duration']}s\nCID: {d['cid']}\")"

# 3. Get audio stream URL
CID=<CID from previous step>
AUDIO_URL=$(curl -s "https://api.bilibili.com/x/player/playurl?bvid=$BV&cid=$CID&fnval=16&qn=64" \
  -H "User-Agent: Mozilla/5.0" -H "Referer: https://www.bilibili.com/" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data']['dash']['audio'][0]['baseUrl'])")

# 4. Download audio (Referer header required, otherwise 403)
curl -L -o /tmp/media_audio.m4s \
  -H "User-Agent: Mozilla/5.0" -H "Referer: https://www.bilibili.com/" "$AUDIO_URL"

# 5. Convert to mp3
ffmpeg -y -i /tmp/media_audio.m4s -acodec libmp3lame -q:a 5 /tmp/media_audio.mp3
```

→ Step 2b (check size & transcribe)

### Step 2a: Video — Download Audio (when no subtitles)

```bash
# YouTube may need --cookies-from-browser chrome to bypass bot detection
yt-dlp --cookies-from-browser chrome -f "ba[ext=m4a]/ba/b" --extract-audio --audio-format mp3 --audio-quality 5 \
  -o "/tmp/media_audio.%(ext)s" "VIDEO_URL"
```

### Step 2b: Check Audio Size & Segment

```bash
FILE_SIZE=$(stat -f%z /tmp/media_audio.* 2>/dev/null || stat -c%s /tmp/media_audio.* 2>/dev/null)
echo "File size: $FILE_SIZE bytes"
```

- **≤ 100MB (100000000)** → Step 2c (transcribe directly)
- **> 100MB** → Split first, then transcribe each segment

**Splitting large audio (>100MB)**:
```bash
# Get total duration
DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 /tmp/media_audio.* | head -1)

# Split into 30-minute segments
SEGMENT_SEC=1800
SEGMENTS=$(python3 -c "import math; print(math.ceil(float('$DURATION')/$SEGMENT_SEC))")

# Cut segments
for i in $(seq 0 $((SEGMENTS-1))); do
  START=$((i * SEGMENT_SEC))
  ffmpeg -y -i /tmp/media_audio.* -ss $START -t $SEGMENT_SEC -acodec libmp3lame -q:a 5 \
    "/tmp/media_segment_${i}.mp3" 2>/dev/null
done
```

→ Call Step 2c for each segment, concatenate results

### Step 2b-verify: Audio Integrity Check

> ⚠️ Critical: Verify the downloaded audio matches the video metadata before transcribing.
> Without this, a stale or incorrect audio file will waste the full transcription run.

```bash
# 1. Get API-declared duration from Step 1
API_DURATION=<duration from Step 1 (seconds)>

# 2. Check file exists
if [ ! -f /tmp/media_audio.m4s ]; then
  echo "❌ Download failed: /tmp/media_audio.m4s not found!"
  exit 1
fi

# 3. Check file timestamp — reject files older than 5 minutes
CURRENT_TS=$(date +%s)
FILE_TS=$(stat -f %m /tmp/media_audio.m4s 2>/dev/null || stat -c %Y /tmp/media_audio.m4s 2>/dev/null)
FILE_AGE=$((CURRENT_TS - FILE_TS))
echo "File created: $(date -r $FILE_TS '+%Y-%m-%d %H:%M:%S')"
echo "File age: ${FILE_AGE}s"
if [ $FILE_AGE -gt 300 ]; then
  echo "❌ File is not freshly downloaded (${FILE_AGE}s old)! Possible stale file."
  exit 1
fi

# 4. Compare audio duration vs API declaration (allow 10% tolerance)
ACTUAL_DURATION=$(ffprobe -v error -show_entries format=duration -of csv=p=0 /tmp/media_audio.m4s 2>/dev/null | head -1)
ACTUAL_DURATION_INT=$(echo "$ACTUAL_DURATION" | cut -d. -f1)
echo "API duration: ${API_DURATION}s"
echo "Audio duration: ${ACTUAL_DURATION_INT}s"

THRESHOLD=$(python3 -c "print(int($API_DURATION * 0.9))")
if [ "$ACTUAL_DURATION_INT" -lt "$THRESHOLD" ]; then
  echo "❌ Audio duration (${ACTUAL_DURATION_INT}s) doesn't match API (${API_DURATION}s)!"
  echo "   Possible: stale CDN cache / wrong file / incomplete download"
  exit 1
fi
echo "✅ Audio integrity check passed"
```

**On failure**: Interrupt immediately, don't waste transcription time.

**On pass** → Continue to Step 2c

### Step 2c: Transcription (Priority Order)

> **重要**: 基于 M4 Mac 性能测试，推荐以下优先级顺序

#### 优先级 1: whisper.cpp (推荐 ⭐⭐⭐⭐⭐)

**性能**: 31.6x 实时速度 (base), 18.9x (small) | **稳定性**: ⭐⭐⭐⭐⭐

```bash
# 安装 (首次)
brew install whisper-cpp

# 下载模型 (首次)
mkdir -p /opt/homebrew/opt/whisper-cpp/models
curl -L -o /opt/homebrew/opt/whisper-cpp/models/ggml-small.bin \
  "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"

# 转写
/opt/homebrew/Cellar/whisper-cpp/*/bin/whisper-cli \
  -m /opt/homebrew/opt/whisper-cpp/models/ggml-small.bin \
  -l zh \
  --output-txt \
  --output-file /tmp/media_transcript \
  /tmp/media_audio.mp3

# 读取结果
cat /tmp/media_transcript.txt
```

**模型选择**:
| 模型 | 文件大小 | 实时倍速 | 准确度 | 推荐场景 |
|------|---------|---------|--------|---------|
| `ggml-tiny.bin` | 75MB | ~50x | 良好 | 快速草稿 |
| `ggml-base.bin` | 142MB | ~32x | 很好 | **默认推荐** |
| `ggml-small.bin` | 466MB | ~19x | 优秀 | 高质量需求 |
| `ggml-medium.bin` | 1.5GB | ~10x | 极佳 | 专业用途 |

#### 优先级 2: PyTorch Nightly + openai-whisper MPS (备选 ⭐⭐⭐⭐)

**性能**: ~7x 实时速度 (MPS 加速) | **稳定性**: ⭐⭐⭐⭐

> ✅ **已验证**: PyTorch Nightly (2.12.0.dev) 完全解决了 Apple Silicon MPS NaN 问题

```bash
# 创建独立环境 (首次)
mkdir -p ~/projects/whisper-mps
cd ~/projects/whisper-mps
python3 -m venv venv
source venv/bin/activate

# 安装 PyTorch Nightly (首次)
pip install --pre torch torchaudio --index-url https://download.pytorch.org/whl/nightly/cpu

# 安装 whisper (首次)
pip install openai-whisper -i https://pypi.tuna.tsinghua.edu.cn/simple

# 转写 (使用 MPS 加速)
source ~/projects/whisper-mps/venv/bin/activate
whisper /tmp/media_audio.mp3 \
  --model small \
  --device mps \
  --output_dir /tmp \
  --output_format txt \
  --language zh

# 读取结果
cat /tmp/media_audio.txt
```

#### 优先级 3: mlx-whisper (备选 ⭐⭐⭐⭐)

**性能**: 6.4x 实时速度 | **稳定性**: ⭐⭐⭐⭐

```bash
# 安装 (首次)
pip3 install --break-system-packages mlx-whisper

# 转写
python3 -c "
import mlx_whisper
result = mlx_whisper.transcribe(
    '/tmp/media_audio.mp3',
    path_or_hf_repo='mlx-community/whisper-small-mlx',
    language='zh'
)
print(result['text'])
with open('/tmp/media_transcript.txt', 'w') as f:
    for seg in result.get('segments', []):
        f.write(seg['text'] + '\n')
"
```

#### 优先级 4: openai-whisper CPU Fallback (最后备选 ⭐⭐⭐)

**性能**: ~7x 实时速度 | **稳定性**: ⭐⭐⭐⭐⭐

> ⚠️ **警告**: brew 安装的 openai-whisper (PyTorch 2.10 稳定版) 在 MPS 上有 NaN 问题，**必须使用 CPU**

```bash
# 安装 (首次)
brew install openai-whisper

# 转写 (强制 CPU，避免 MPS NaN 错误)
whisper /tmp/media_audio.mp3 \
  --model small \
  --device cpu \
  --output_dir /tmp \
  --output_format txt \
  --language zh

# 读取结果
cat /tmp/media_audio.txt
```

### Step 2d: Fallback Chain (自动切换)

```bash
#!/bin/bash
AUDIO_FILE="/tmp/media_audio.mp3"

# 1. 尝试 whisper.cpp (首选)
if command -v /opt/homebrew/Cellar/whisper-cpp/*/bin/whisper-cli &> /dev/null; then
  echo "Using whisper.cpp..."
  /opt/homebrew/Cellar/whisper-cpp/*/bin/whisper-cli \
    -m /opt/homebrew/opt/whisper-cpp/models/ggml-small.bin \
    -l zh --output-txt --output-file /tmp/media_transcript \
    "$AUDIO_FILE" 2>/dev/null && exit 0
fi

# 2. 尝试 PyTorch Nightly + whisper MPS (需独立环境)
if [ -d "$HOME/projects/whisper-mps/venv" ]; then
  echo "Using PyTorch Nightly + whisper MPS..."
  source ~/projects/whisper-mps/venv/bin/activate
  whisper "$AUDIO_FILE" --model small --device mps --output_dir /tmp --output_format txt --language zh 2>/dev/null && exit 0
fi

# 3. 尝试 mlx-whisper
if python3 -c "import mlx_whisper" 2>/dev/null; then
  echo "Using mlx-whisper..."
  python3 -c "
import mlx_whisper
result = mlx_whisper.transcribe('$AUDIO_FILE', path_or_hf_repo='mlx-community/whisper-small-mlx', language='zh')
with open('/tmp/media_transcript.txt', 'w') as f:
    f.write(result['text'])
" && exit 0
fi

# 4. Fallback to openai-whisper CPU
echo "Using openai-whisper CPU fallback..."
whisper "$AUDIO_FILE" --model small --device cpu --output_dir /tmp --output_format txt --language zh
```

### Step 3: Structured Summary

Choose output format based on media type:

**Video (≤20 min)**:
1. **Overview** (1-2 sentences)
2. **Key Points** (3-5 bullet points)
3. **Notable Quotes** (if any)
4. **Action Items** (if applicable)

**Podcast (>20 min)**:
1. **Overview** (2-3 sentences: who discussed what)
2. **Chapter Summary** (segmented by topic, 2-3 sentences each)
3. **Key Points** (5-8 bullet points)
4. **Notable Quotes**
5. **Action Items** (if applicable)

### Step 4: Save to Output Directory

**Output Directory**: `/Volumes/SDD2T/obsidian-vault-write/技术学习/转录总结`

After generating the structured summary, automatically save it to the output directory:

1. **Generate filename**: Use media title, sanitize for filesystem
   - Remove special characters: `< > : " / \ | ? *`
   - Replace spaces with underscores or keep as-is
   - Limit to 100 characters
   - Format: `[Title].md`

2. **Create Obsidian-compatible markdown file** with frontmatter:

```markdown
---
created: [YYYY-MM-DD]
source_url: [Original URL]
media_type: [Video/Podcast]
duration: [Duration]
platform: [YouTube/Bilibili/Xiaoyuzhou/Apple Podcasts/etc.]
tags:
  - 转录
  - [platform-name]
---

[Full structured summary content from Step 3]

---

## 原始转录

[Full transcript text, if available]
```

3. **Write file**:
```bash
OUTPUT_DIR="/Volumes/SDD2T/obsidian-vault-write/技术学习/转录总结"
FILENAME="[sanitized-title].md"
FILE_PATH="$OUTPUT_DIR/$FILENAME"

# Ensure directory exists
mkdir -p "$OUTPUT_DIR"

# Write content to file
cat > "$FILE_PATH" << 'ENDOFFILE'
[markdown content]
ENDOFFILE

echo "✅ Saved to: $FILE_PATH"
```

4. **Report to user**: After saving, inform user of file location

## Output Format

### Video

```
## 📺 Video Digest

**Title**: [Video Title]
**Duration**: [x minutes]
**Language**: [Chinese/English]

### Overview
[1-2 sentence summary]

### Key Points
1. [Point 1]
2. [Point 2]
...

### Notable Quotes
> "xxx" — [timestamp]

### Action Items
- [if applicable]
```

### Podcast

```
## 🎙️ Podcast Digest

**Show**: [Podcast Name]
**Episode**: [Episode Title]
**Duration**: [x minutes]
**Guests**: [if any]

### Overview
[2-3 sentences: who discussed what, core conclusions]

### Chapter Summary
#### 1. [Topic] (~xx:xx-xx:xx)
[2-3 sentences of core content]

#### 2. [Topic] (~xx:xx-xx:xx)
[2-3 sentences of core content]
...

### Key Points
1. [Point 1]
2. [Point 2]
...

### Notable Quotes
> "xxx"

### Action Items
- [if applicable]
```

## Error Handling

| Situation | Action |
|-----------|--------|
| whisper.cpp not installed | `brew install whisper-cpp` |
| Model not downloaded | Download from HuggingFace |
| mlx-whisper not installed | `pip install mlx-whisper` |
| ffmpeg not found | `brew install ffmpeg` |
| yt-dlp not found | `brew install yt-dlp` |
| Xiaoyuzhou curl extraction empty | Use Puppeteer/browser to get rendered HTML |
| Audio >100MB | ffmpeg segment (30min/segment), transcribe each |
| Podcast >2 hours | Warn user about duration, confirm before proceeding |
| yt-dlp Bilibili 412 | Use Bilibili API instead (Step 1d) |
| yt-dlp YouTube bot detection | Add `--cookies-from-browser chrome` |
| Network timeout | Retry once |
| Spotify links | Inform user: not supported (DRM protected) |
| Out of memory | Use tiny/base model |

## Performance Comparison (M4 Mac)

| Tool | Model | Realtime Speed | Stability | Memory | Notes |
|------|-------|---------------|-----------|--------|-------|
| **whisper.cpp** | base | **31.6x** | ⭐⭐⭐⭐⭐ | 150MB | 首选 |
| **whisper.cpp** | small | **18.9x** | ⭐⭐⭐⭐⭐ | 500MB | 首选 |
| **PyTorch Nightly + whisper** | small (MPS) | ~7x | ⭐⭐⭐⭐ | 500MB | 需独立环境 |
| **mlx-whisper** | small | 6.4x | ⭐⭐⭐⭐ | 500MB | 备选 |
| **openai-whisper** | small (CPU) | ~7x | ⭐⭐⭐⭐⭐ | 1GB | 最后备选 |
| openai-whisper (brew) | small (MPS) | ❌ | ⭐ | - | NaN Error |

> **注意**: brew 安装的 openai-whisper 使用 PyTorch 2.10 稳定版，在 MPS 上有 NaN 问题。
> PyTorch Nightly (2.12.0.dev) 已修复此问题，但需要创建独立环境。

## Dependencies

**Required**:
- `ffmpeg`: audio conversion + segmentation (`brew install ffmpeg`)
- `yt-dlp`: video download + subtitle extraction (`brew install yt-dlp`)
- `curl`: HTTP requests (built-in)

**Recommended**:
- `whisper-cpp`: fastest transcription (`brew install whisper-cpp`)
- `PyTorch Nightly + whisper`: MPS accelerated transcription (独立环境)
- `mlx-whisper`: alternative transcription (`pip install mlx-whisper`)

**Optional**:
- `openai-whisper`: CPU fallback (`brew install openai-whisper`)

## Related

- [[Whisper 部署测试报告]] - M4 Mac 性能测试详细报告
- [[x-reader-Skills部署记录]] - 完整部署文档
