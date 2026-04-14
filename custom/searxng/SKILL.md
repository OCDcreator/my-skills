---
name: searxng
description: >-
  Search the internet using your self-hosted SearXNG instance at
  http://192.168.31.98:9900. Use this when you need to search for current
  information, news, documentation, or any web content. Triggers: "search for",
  "look up", "find information about", "what is", "how to" when web search
  is needed.
---

# SearXNG Search

Search the internet using your self-hosted SearXNG instance.

## Endpoint

```
http://192.168.31.98:9900/search?q={query}&format=json
```

## Usage

### Basic Search

```bash
curl -s "http://192.168.31.98:9900/search?q=你的搜索词&format=json" | jq .
```

### Search and Extract Results

```bash
# 使用封装脚本
~/.config/opencode/skills/searxng/scripts/search.sh "你的搜索词" 5
```

### Python Script (Recommended)

```bash
python3 ~/.config/opencode/skills/searxng/scripts/search.py "你的搜索词" --num 5
```

## API Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `q` | Search query | `q=Python+tutorial` |
| `format` | Response format | `format=json` |
| `engines` | Specific engines | `engines=google,bing` |
| `language` | Result language | `language=zh-CN` |
| `pageno` | Page number | `pageno=2` |
| `time_range` | Time filter | `time_range=day/week/month/year` |

## Response Format

```json
{
  "query": "search term",
  "number_of_results": 100,
  "results": [
    {
      "url": "https://example.com",
      "title": "Result Title",
      "content": "Result snippet...",
      "engine": "google"
    }
  ]
}
```

## Examples

### Search for news

```bash
curl -s "http://192.168.31.98:9900/search?q=AI新闻&format=json&language=zh-CN&time_range=day" | jq '.results[:3]'
```

### Search specific engines

```bash
curl -s "http://192.168.31.98:9900/search?q=Python&format=json&engines=github,stackoverflow" | jq '.results[:5]'
```

### Get documentation

```bash
curl -s "http://192.168.31.98:9900/search?q=FastAPI+tutorial&format=json&engines=google" | jq '.results[:3]'
```

## Integration Tips

1. **Use jq for parsing**: Pipe results through `jq` to extract specific fields
2. **Limit results**: Use `.results[:N]` to get top N results
3. **Combine with defuddle**: Search first, then use defuddle to read full content
4. **Cache searches**: Store frequently needed information to avoid repeated searches

## Workflow

```
User asks question → Check if web search needed → Call SearXNG API → Parse JSON → Present results
```
