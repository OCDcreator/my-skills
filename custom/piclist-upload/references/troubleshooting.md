# 排错决策树

SKILL.md 给了快速对照表，本文件按链路层次展开诊断顺序。上传失败时，先判断「失败发生在哪一层」，再针对那层排。

## 链路层次（从本机到远端）

```
[本机 PicList server]  →  [公网 DNS + VPS nginx]  →  [VPS frps]  →  [飞牛 frpc]  →  [飞牛 lsky-pro 容器]  →  [飞牛落盘]
       (1)                    (2)                       (3)            (4)                (5)                  (6)
```

定位原则：**看 HTTP 响应来自哪一层**。
- 连不上本机 36677 → 层 1
- 连得上 36677 但很快返回错误 → 层 1（PicList 自己拒绝）
- 卡很久才返回错误 → 层 2-6（公网链路或图床后端）
- 上传成功但 URL 打不开 → 层 2-4（返回的 URL 是公网链路，可能 frp 或 nginx 挂）

## 层 1：本机 PicList server

### server connection refused（最常见）

PicList 没运行。本机检查：

```powershell
# Windows
netstat -ano | findstr ":36677"      # 有 LISTENING 行说明 PicList server 在
Get-Process piclist -ErrorAction SilentlyContinue
```

```bash
# Mac
nc -z 127.0.0.1 36677 && echo OPEN || echo CLOSED
pgrep -af "[p]iclist"
```

不在 → 启动 PicList（Windows 开始菜单 / Mac `open -a PicList` / 系统托盘图标）。

### server 响应但立刻 `success:false`

PicList 自己拒绝。看 PicList 日志：
- Windows: `C:\Users\<user>\AppData\Roaming\piclist\piclist.log`
- Mac: `~/Library/Logs/piclist/piclist.log`（或从 PicList GUI「日志」按钮打开）

常见原因：
- 默认图床不是 lskyplist（`picBed.current` 应为 `lskyplist`）
- lskyplist 配置缺 `strategyId: "1"`
- token 字段为空或格式错

### 路径错误：`list` 里给了 URL 或别的机器路径

PicList `list` 只吃**本机绝对路径**。给 URL → 报错；给 Mac 路径但在 Windows 调 → 文件不存在。先 `scp` 或走兰空直连 API。

## 层 2-6：公网链路 / 图床后端

### `{"success":false,"message":"服务异常..."}`

PicList 收到请求并转发，但兰空服务端返回错。依次检查：

**飞牛 NAS 是否在线 + 容器是否跑**（ssh 到飞牛 `letian@192.168.31.147`）：
```bash
docker ps | grep -E "lsk|frpc"      # 应看到 lsky-pro / lsky-mysql / frpc 三容器 Up
docker logs lsky-pro --tail 50      # 看应用日志
```

容器挂了 → `docker compose up -d` 或 `docker restart lsky-pro`。

### 上传 401 / 未授权

token 过期。后台 `https://pic.ltreen.tech/admin` 重新生成 token → 更新**所有**装了 PicList 的机器的 `data.json`（Windows + Mac 等）。多机同步见 `piclist-multi-machine.md`。

### 上传成功但访问图片 502 / 打不开 / 加载慢

图床返回了 URL（说明 lsky 写入成功），但公网访问链路挂。frp 链路问题：

**飞牛 frpc**：
```bash
ssh letian@192.168.31.147 'docker logs frpc --tail 50'
```

**VPS frps + nginx**：
```bash
ssh root@47.94.235.59 'systemctl status frps; nginx -t; tail -20 /var/log/nginx/pic.ltreen.tech.error.log'
```

常见：frpc 容器重启后没自动重连、VPS nginx 配置改动后没 reload、frps 端口 18320 被防火墙拦。

### 图片能打开但 EXIF 还在 / 不是 webp

不是 bug。说明走了**兰空直连 API 路径**（不转格式不清 EXIF）。要 webp → 走 PicList，或上传前自己 `sips`/`cwebp` 转。见 `upload-paths.md` 对比表。

## 不该犯的错（自检清单）

上传失败先确认：
- [ ] PicList 真的在跑（不是开机自启没起来）
- [ ] `list` 是本机路径不是 URL，不是别的机器路径
- [ ] 路径分隔符对（Windows `\`，Mac/Linux `/`）
- [ ] JSON 里 Windows 路径反斜杠转义了（`C:\\Users\\...`）
- [ ] token 没过期（401 就是过期）
- [ ] 飞牛 NAS 没关机
- [ ] 走兰空直连时带了 `strategy_id=1`
