---
name: x-reader
description: Content processing skill pack for video/podcast transcription and multi-dimensional content analysis. Triggers when user shares media URLs (YouTube, Bilibili, X/Twitter, Xiaoyuzhou, Apple Podcasts) or requests content analysis. Use for transcription workflows, content digestion, and extracting actionable insights from any content source.
---

# x-reader Skill Pack

> Media URLs → transcripts → structured analysis → actionable insights

A unified skill pack combining video/podcast transcription with content analysis.

## Sub-skills

| Skill | Trigger | Output |
|-------|---------|--------|
| `x-reader/video` | Media URL detected | Transcript + structured summary |
| `x-reader/analyzer` | `/analyze`, "analyze this", or post-transcription | Multi-dimensional analysis report |

## Workflow

```
Media URL ──→ x-reader/video ──→ Transcript + Summary
                                      │
                                      ▼
                             x-reader/analyzer ──→ Deep analysis + Action items
```

## When to Use

**Use `x-reader/video` when:**
- User sends a YouTube/Bilibili/Xiaoyuzhou/Apple Podcasts URL
- User sends direct audio/video links (mp3/mp4/m3u8)
- User asks to "transcribe" or "get summary of this video/podcast"

**Use `x-reader/analyzer` when:**
- User says `/analyze [URL]` or "analyze this article"
- User asks "what are the key takeaways?"
- After video transcription completes (auto-triggered)

## Quick Reference

- **Video transcription**: See `video/SKILL.md` for platform support and whisper pipeline
- **Content analysis**: See `analyzer/SKILL.md` for analysis dimensions and output formats

## Output Directory

Transcripts are automatically saved to:
```
/Volumes/SDD2T/obsidian-vault-write/技术学习/转录总结
```
