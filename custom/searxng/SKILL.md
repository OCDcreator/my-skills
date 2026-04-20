---
name: searxng
description: >-
  Search the internet using your self-hosted SearXNG instance. Use this when
  you need to search for current information, news, documentation, or any web
  content. Triggers: "search for", "look up", "find information about", "what
  is", "how to" when web search is needed.
---

# SearXNG Search

Search the internet using your self-hosted SearXNG instance.

## Deployment Info

| Item | Value |
|------|-------|
| **Primary** | `http://192.168.31.147:9900` (飞牛 NAS Docker) |
| **Fallback** | `http://192.168.31.98:9900` (备用) |
| **Host** | 飞牛 NAS `192.168.31.147` (letian, SSH port 22) |
| **Container** | `searxng` / `searxng/searxng:latest` |
| **Config** | `/vol1/docker/searxng/settings.yml` (NAS 上) |
| **Proxy** | 所有出站流量经 `http://192.168.31.148:7897` (Mihomo/Clash Verge) |

> ⚠️ 飞牛 NAS 没有直连外网出口，搜索引擎流量依赖 `192.168.31.148:7897` 代理。
> 若搜索超时，检查用户电脑 (192.168.31.148) 是否开机且 Clash Verge 在运行。

## Endpoint

```
http://192.168.31.147:9900/search?q={query}&format=json
```

## Usage

### Basic Search

```bash
curl -s "http://192.168.31.147:9900/search?q=你的搜索词&format=json" | jq .
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
curl -s "http://192.168.31.147:9900/search?q=AI新闻&format=json&language=zh-CN&time_range=day" | jq '.results[:3]'
```

### Search specific engines

```bash
curl -s "http://192.168.31.147:9900/search?q=Python&format=json&engines=github,stackoverflow" | jq '.results[:5]'
```

### Get documentation

```bash
curl -s "http://192.168.31.147:9900/search?q=FastAPI+tutorial&format=json&engines=google" | jq '.results[:3]'
```

## Troubleshooting

### All engines timeout / 0 results

Likely cause: proxy (`192.168.31.148:7897`) unreachable.

```bash
# From NAS, test proxy
ssh letian@192.168.31.147
curl -s -o /dev/null -w '%{http_code}' --max-time 10 -x http://192.168.31.148:7897 https://www.google.com

# Check container status
sudo docker ps --filter name=searxng
sudo docker logs searxng --tail 20
```

### Restart container

```bash
ssh letian@192.168.31.147
echo '1q2w3e4r5t=q' | sudo -S docker restart searxng
```

### Update proxy address in settings.yml

If the user's PC IP or Mihomo port changes, update `/vol1/docker/searxng/settings.yml`:

```yaml
outgoing:
  proxies:
    all://:
      - http://NEW_IP:NEW_PORT
```

Then restart: `sudo docker restart searxng`

## Integration Tips

1. **Use jq for parsing**: Pipe results through `jq` to extract specific fields
2. **Limit results**: Use `.results[:N]` to get top N results
3. **Combine with defuddle**: Search first, then use defuddle to read full content
4. **Cache searches**: Store frequently needed information to avoid repeated searches

## Workflow

```
User asks question → Check if web search needed → Call SearXNG API → Parse JSON → Present results
```
