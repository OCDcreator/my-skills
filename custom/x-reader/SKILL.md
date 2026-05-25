---
name: x-reader
description: Use when user shares media URLs, Douyin/抖音, web pages, blocked or JavaScript-rendered URLs, direct audio/video links, or requests transcription, digest, summary, browser extraction, or content analysis.
---

# x-reader Skill Pack

> Media URLs → transcripts → structured analysis → actionable insights

A unified skill pack combining video/podcast transcription with content analysis.

## Sub-skills

| Skill | Trigger | Output |
|-------|---------|--------|
| `x-reader/video` | Media URL detected | Transcript + structured summary |
| `x-reader/douyin` | Douyin/抖音 share text or URL | Douyin transcript + structured summary |
| `x-reader/browser-fetch` | Blocked, JS-rendered, or browser-only web URL | Browser-rendered markdown for analysis |
| `x-reader/analyzer` | `/analyze`, "analyze this", or post-transcription | Multi-dimensional analysis report |

## Workflow

```
Media URL ──→ x-reader/video ──→ Transcript + Summary
                                      │
                                      ▼
                             x-reader/analyzer ──→ Deep analysis + Action items

Blocked/JS URL ──→ x-reader/browser-fetch ──→ Markdown ──→ x-reader/analyzer
```

## When to Use

**Use `x-reader/video` when:**
- User sends a YouTube/Bilibili/Xiaoyuzhou/Apple Podcasts URL
- User sends direct audio/video links (mp3/mp4/m3u8)
- User asks to "transcribe" or "get summary of this video/podcast"

**Use `x-reader/douyin` when:**
- User sends `v.douyin.com`, `douyin.com/video`, or share text containing `复制打开抖音`
- User asks to transcribe, summarize, digest, or save a Douyin/抖音 video

**Use `x-reader/browser-fetch` when:**
- A web URL cannot be read by `webfetch`, `defuddle`, Jina Reader, or `web-reader`
- The page needs JavaScript rendering, login state, browser interaction, or CloakBrowser fallback
- The user says the page is blocked by Cloudflare/reCAPTCHA/bot detection or asks to “用浏览器打开”

**Use `x-reader/analyzer` when:**
- User says `/analyze [URL]` or "analyze this article"
- User asks "what are the key takeaways?"
- After video transcription completes (auto-triggered)

## Quick Reference

- **Video transcription**: See `video/SKILL.md` for platform support and whisper pipeline
- **Douyin transcription**: See `douyin/SKILL.md` for Douyin-specific extraction; do not rely on yt-dlp as the primary path
- **Browser-rendered web fetch**: See `browser-fetch/SKILL.md` for CloakBrowser fallback when normal fetch tools fail
- **Content analysis**: See `analyzer/SKILL.md` for analysis dimensions and output formats

## Output Directory

Transcripts are automatically saved to:
```
/Volumes/SDD2T/obsidian-vault-write/技术学习/转录总结
```
