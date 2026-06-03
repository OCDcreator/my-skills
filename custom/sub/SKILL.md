---
name: sub
description: Diagnose and maintain the local OpenClash subscription-conversion chain built from OpenClash, `sub-web`, `subconverter`, and the `wallrule` preset on this machine. Use when requests mention OpenClash, 订阅转换, `sub-web`, `subconverter`, `wallrule`, 自定义模板, `25500`, `25502`, `IPRoyal`, `emoji=true`, `No nodes were found!`, `proxy group ... not found`, or when you need to confirm which template, proxy definitions, and generated config are actually active.
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

## Known Failure Patterns

### `proxy group ... 'IPRoyal' not found`

- Usually happens when `emoji=true` renamed the proxy to `🔒 IPRoyal`, but the active template still references bare `IPRoyal`
- Fix the runtime template, not just the repo preset
- Re-check generated names in the landed router config after refresh

### IPRoyal timeout or test failure

- Confirm the SOCKS5 port is `12324`
- Do not confuse it with the HTTP/HTTPS port `12323`
- Verify both the repo config and the runtime `iproyal_proxy.yaml`

### OpenClash says download succeeded but kernel test failed

- The YAML was downloaded, but the active template or runtime proxy fragment is inconsistent
- Check proxy names, ports, and group references before blaming the upstream subscription

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
2. Sync the runtime copies under `/Users/dht/sub-service/subconverter/base/config/custom/`
3. Apply the runtime changes with either:
   - `docker cp ... subconverter:/base/config/custom/...`
   - `docker compose up -d --build subconverter`
4. Refresh OpenClash
5. Verify `/etc/openclash/config/wget.yaml` on the router before declaring success

## Guardrails

- Do not claim the GitHub raw template is active unless the log shows OpenClash is fetching that URL directly
- Do not assume the repo file and the runtime file are the same; verify both
- Do not blame `wallrule` first when the generator returns no nodes
- Do not assume fnOS or other hosts are automatically proxied; test the actual network path when upstream fetches are flaky
