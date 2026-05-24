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
| **Proxy** | 所有出站流量经 `http://Clash:<OpenClash password>@192.168.31.204:7893` (飞牛 Docker QWRT/OpenClash) |
| **Host route** | `/etc/systemd/system/qwrt-macvlan-shim.service` keeps host access to the QWRT macvlan container |
| **Default engines** | `bing`, `google`; additional stable engines are enabled for explicit `engines=` use |

> ⚠️ 飞牛 NAS 没有直连外网出口，搜索引擎流量依赖飞牛 Docker 里的 QWRT/OpenClash。
> QWRT 是 macvlan 容器，宿主机需要 `qwrt-macvlan-shim.service` 提供 `qwrt-shim`
> 路由，才能从飞牛宿主机或 bridge 容器访问 `192.168.31.204:7893`。
> 泛搜索默认结果主要来自 `google,bing`。已启用并验证可按需指定的稳定引擎包括
> `github`, `stackoverflow`, `docker hub`, `arxiv`, `pubmed`, `semantic scholar`,
> `crossref`, `openalex`。DuckDuckGo 容易 CAPTCHA，Brave/Mojeek 容易限流或拒绝访问。

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

### Search academic sources

```bash
curl -s "http://192.168.31.147:9900/search?q=large%20language%20models&format=json&engines=arxiv,pubmed,semantic%20scholar,crossref,openalex" | jq '.results[:5]'
```

### Get documentation

```bash
curl -s "http://192.168.31.147:9900/search?q=FastAPI+tutorial&format=json&engines=google" | jq '.results[:3]'
```

## Troubleshooting

### All engines timeout / 0 results

Likely cause: proxy (`192.168.31.204:7893`) unreachable or the macvlan shim route is missing.

```bash
# From NAS, test proxy
ssh letian@192.168.31.147
curl -s -o /dev/null -w '%{http_code}' --max-time 10 -x 'http://Clash:<OpenClash password>@192.168.31.204:7893' https://www.google.com

# Check the QWRT macvlan host route
systemctl is-active qwrt-macvlan-shim.service
ip route get 192.168.31.204

# Check container status
sudo docker ps --filter name=searxng
sudo docker logs searxng --tail 20
```

### Restart container

```bash
ssh letian@192.168.31.147
sudo docker restart searxng
```

### Update proxy address in settings.yml

If the user's PC IP or Mihomo port changes, update `/vol1/docker/searxng/settings.yml`:

```yaml
outgoing:
  proxies:
    all://:
      - http://USER:PASSWORD@NEW_IP:NEW_PORT
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
