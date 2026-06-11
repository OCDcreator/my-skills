---
name: sub
description: Diagnose and maintain the local OpenClash subscription-conversion chain built from OpenClash, `sub-web`, `subconverter`, and the `wallrule` preset on this machine. Use when requests mention OpenClash, 订阅转换, `sub-web`, `subconverter`, `wallrule`, 自定义模板, `25500`, `25502`, `IPRoyal`, `dialer-proxy`, 链式代理, `IPRoyal-中转`, `emoji=true`, `No nodes were found!`, `proxy group ... not found`, `loop is detected`, or when you need to confirm which template, proxy definitions, and generated config are actually active.
---

# Sub

## Overview

Use this skill to debug the real subscription-conversion path for the local QWRT/OpenClash setup instead of guessing from the repo copy alone. Treat `wallrule` as the editable source, then verify which template and proxy fragments are actually active inside the running `sub-web` and `subconverter` chain.

## Environment Map

- Router: `root@192.168.31.204` runs OpenClash and writes the landed config to `/etc/openclash/config/wget.yaml`
- Mac Mini: `dht@192.168.31.215` runs `sub-web` on `:25502` and `subconverter` on `:25500`
- Source preset repo: `/Volumes/SDD2T/obsidian-vault-write/custom-project/wallrule`
- Runtime template path: `/Users/dht/sub-service/subconverter/base/config/custom/wallrule_hybrid_main.ini`
- Runtime IPRoyal fragment: `/Users/dht/sub-service/subconverter/base/config/custom/iproyal_proxy.yaml`
- Native chain in this environment: `OpenClash -> http://192.168.31.215:25502/api/sub -> subconverter:25500 -> upstream subscription`

## Native Workflow

- Keep the OpenClash subscription conversion service address on the local API: `http://192.168.31.215:25502/api/sub`
- Use `config=config/custom/wallrule_hybrid_main.ini` in the conversion query for the native path
- Treat `wallrule/presets/wallrule_hybrid_main.ini` as the human-edited source preset
- Treat `/Users/dht/sub-service/subconverter/base/config/custom/wallrule_hybrid_main.ini` as the deployed runtime artifact
- If the repo preset changes, sync or rebuild the runtime copy before expecting OpenClash to see it

## Why The Native Path Does Not Use GitHub Raw INI

1. The current OpenClash path points to the local conversion service, not to a remote template URL.
2. In this setup, `config=config/custom/wallrule_hybrid_main.ini` resolves inside the local `sub-web` / `subconverter` runtime under `/base/config/custom/`.
3. `sub-web` and `subconverter` have no volume mounts, so editing the repo file does not update the running container automatically.
4. Private GitHub raw access, anti-bot pages, and short-lived upstream subscription windows add noise. They can fail independently from the local template mechanism.
5. Rule lists inside the preset can still use GitHub raw URLs. This section only explains why the template INI itself is not the active runtime input in the native local path.

## Auto Sync Modes

### Current default: no auto sync

- The current `docker-compose.yml` exposes ports only and does not mount any template files
- Result: repo edits do not reach the running `subconverter` automatically
- Required action after repo edits: `docker cp` or `docker compose up -d --build subconverter`

### Recommended future mode: keep the native built-in path, add bind mounts

- This still counts as using the built-in native path because OpenClash continues to call `config=config/custom/wallrule_hybrid_main.ini`
- The only change is that the internal path `/base/config/custom/...` is backed by files from the `wallrule` repo
- Add mounts like:

```yaml
services:
  subconverter:
    volumes:
      - /Volumes/SDD2T/obsidian-vault-write/custom-project/wallrule/presets/wallrule_hybrid_main.ini:/base/config/custom/wallrule_hybrid_main.ini:ro
      - /Volumes/SDD2T/obsidian-vault-write/custom-project/wallrule/configs/Iproyal_config.yaml:/base/config/custom/iproyal_proxy.yaml:ro
```

- After the compose change, rebuild or recreate `subconverter` once
- Later edits to the repo files flow into the container path automatically; if behavior appears sticky, restart `subconverter` before retesting

### Alternative: scripted sync, not true auto sync

- If bind mounts are undesirable, keep a small sync script that copies the repo preset into `/Users/dht/sub-service/subconverter/base/config/custom/` and then recreates `subconverter`
- This is safer than ad hoc manual copying, but it is still not automatic in the same sense as bind mounts

## Chain Proxy Architecture (链式代理)

The IPRoyal SOCKS5 proxy uses a **dialer-proxy chain** to route through subscription nodes for better reliability and IP diversity.

### Proxy Chain Flow

```
🔒 IPRoyal (socks5 proxy)
  └─ dialer-proxy → IPRoyal-中转 (fallback group)
       └─ regex-matched subscription nodes (香港 01, 日本 01, 新加坡 01, ...)
```

### Template Definitions

**iproyal_proxy.yaml** — the SOCKS5 proxy with chain:
```yaml
proxies:
  - name: "IPRoyal"
    type: socks5
    server: 86.104.161.165
    port: 12324
    username: <redacted>
    password: <redacted>
    udp: true
    dialer-proxy: "IPRoyal-中转"
```

**wallrule_hybrid_main.ini** — the select group and fallback group:
```ini
custom_proxy_group=🛡️ IPRoyal代理`select`[]🔒 IPRoyal
custom_proxy_group=IPRoyal-中转`fallback`(香港 0[123]|台湾 0[123]|新加坡 0[123]|日本 0[123]|美国 0[123]|俄罗斯 01|加拿大 01|印尼 01|印度 01|土耳其 01|巴西 01|德国 01|泰国 01|澳大利亚 01|英国 01|荷兰 01|菲律宾 01|韩国 01|马来西亚 01)`http://www.gstatic.com/generate_204`300,,50
```

### Naming Convention (Critical)

When `emoji=true` (the QWRT default), subconverter renames the proxy:
- Source name in `iproyal_proxy.yaml`: `IPRoyal` (no emoji)
- Output name after emoji processing: `🔒 IPRoyal` (with lock emoji)

**The select group MUST use a different name from the proxy node to avoid circular references.** Current convention:
- Proxy node (after emoji): `🔒 IPRoyal`
- Select group: `🛡️ IPRoyal代理`
- Fallback group: `IPRoyal-中转` (no emoji, referenced by `dialer-proxy` field)

### IPRoyal-中转 Fallback Regex

The regex matches subscription node names containing region keywords:
- `香港 0[123]` matches `🇭🇰 香港 01`, `🇭🇰 香港 02`, `🇭🇰 香港 03`
- Same pattern for 台湾, 新加坡, 日本, 美国 (numbered 01-03)
- Single nodes for other regions: `俄罗斯 01`, `加拿大 01`, etc.

When subscription is expired or empty, the group falls back to `DIRECT` only — the chain proxy becomes non-functional. User must reopen the upstream subscription window.

## Known Failure Patterns

### `proxy group ... 'IPRoyal' not found`

- Usually happens when `emoji=true` renamed the proxy to `🔒 IPRoyal`, but the active template still references bare `IPRoyal`
- Fix the runtime template, not just the repo preset
- Re-check generated names in the landed router config after refresh

### `loop is detected in ProxyGroup`

- The select group name is the same as the proxy node name (both `🔒 IPRoyal`)
- `emoji=true` adds emoji to the proxy name, which collides with a group using the same name
- **Fix:** Rename the select group to something different (e.g. `🛡️ IPRoyal代理`)
- Ensure the group references the emoji-ed proxy name (`[]🔒 IPRoyal`), not the raw name

### IPRoyal timeout or test failure

- Confirm the SOCKS5 port is `12324`
- Do not confuse it with the HTTP/HTTPS port `12323`
- Verify both the repo config and the runtime `iproyal_proxy.yaml`
- If `IPRoyal-中转` group only has `DIRECT`, the upstream subscription has expired — ask user to reopen it

### OpenClash says download succeeded but kernel test failed

- The YAML was downloaded, but the active template or runtime proxy fragment is inconsistent
- Most common cause: proxy name mismatch between group references and actual node names after emoji processing
- Check proxy names, ports, and group references before blaming the upstream subscription
- Run `/etc/openclash/core/clash_meta -t -f <config>` on the router for the exact error message

### `No nodes were found!` or region groups collapse to one node or `DIRECT`

- The upstream subscription window may have expired, or the upstream fetch returned too few nodes
- Confirm the generator can still return nodes before changing the template
- In this environment, some upstream subscriptions require manual opening and only stay usable for a short window

### Repo preset looks right but router still shows old content

- The running container is still using the old internal file
- Sync the runtime file with `docker cp` or rebuild `subconverter`
- Refresh OpenClash again only after the runtime copy is confirmed

## Triage Checklist

1. Confirm the plugin log is really using `http://192.168.31.215:25502/api/sub`
2. Confirm the local containers and their mount model:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker inspect sub-web subconverter --format '{{.Name}} {{json .Mounts}}'
```

3. Inspect the active runtime template and runtime IPRoyal fragment:

```bash
docker exec subconverter sh -lc "sed -n '30,38p' /base/config/custom/wallrule_hybrid_main.ini"
docker exec subconverter sh -lc "sed -n '1,16p' /base/config/custom/iproyal_proxy.yaml"
```

4. If `emoji=true`, compare proxy names in the generated YAML with the group references in the active template
5. Verify the landed router config directly:

```bash
ssh root@192.168.31.204 "grep -n 'IPRoyal\\|12323\\|12324\\|🧠 Claude\\|🤖 OpenAI' /etc/openclash/config/wget.yaml | head -n 40"
```

6. If the generator says `No nodes were found!`, ask the user to manually reopen the upstream subscription page and refresh during the short active window
7. Only call the issue fixed after the router-side landed config matches the expected proxy name and port

## Change Procedure

1. Edit the source files in the `wallrule` repo:
   - `presets/wallrule_hybrid_main.ini`
   - `configs/Iproyal_config.yaml`
2. Decide whether this environment is in manual-sync mode or bind-mount auto-sync mode
3. If still in manual-sync mode, sync the runtime copies under `/Users/dht/sub-service/subconverter/base/config/custom/`
4. Apply the runtime changes with either:
   - `docker cp ... subconverter:/base/config/custom/...`
   - `docker compose up -d --build subconverter`
5. Refresh OpenClash
6. Verify `/etc/openclash/config/wget.yaml` on the router before declaring success

## Guardrails

- Do not claim the GitHub raw template is active unless the log shows OpenClash is fetching that URL directly
- Do not assume the repo file and the runtime file are the same; verify both
- Do not call bind-mounted native files "GitHub raw mode"; they are still the built-in native path
- Do not blame `wallrule` first when the generator returns no nodes
- Do not assume fnOS or other hosts are automatically proxied; test the actual network path when upstream fetches are flaky
- Do not give a select group the same name as a proxy node — Mihomo will detect a loop and reject the config
- Do not reference proxy nodes by their raw name when `emoji=true` — always use the emoji-ed name in group references
- Do not test chain proxy functionality when the upstream subscription is expired — the fallback group will only contain `DIRECT`
