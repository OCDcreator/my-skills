# 上传路径详解

SKILL.md 给了决策表，本文件展开三条路径的完整细节、返回字段、对比表、跨平台函数。读完 SKILL.md 仍不清楚具体怎么调时读这里。

## PicList server API（路径 1）

PicList 是 Electron 跨平台客户端，在 Windows / Mac / Linux 都可装。装好后本地跑一个 HTTP server，所有上传走这个 server，server 内部按配置（默认 lskyplist）把文件传到 pic.ltreen.tech。

### 环境现状（已配好，无需重配）

| 项 | 值 |
|---|---|
| PicList server | `http://127.0.0.1:36677`（本机，已启用） |
| 图床 | 兰空 Pro+ 2.4.1，`https://pic.ltreen.tech` |
| PicList 默认图床 | `lskyplist`（已切为默认） |
| configName | `picltreen` |
| 上传接口（PicList 侧） | `POST /upload` |
| strategyId | `1`（本地储存） |
| PicList 图片处理 | 自动转 webp（`buildIn.compress.isConvert=true`）+ 去 EXIF + 质量 90 |
| 后台管理 | `https://pic.ltreen.tech/admin` |

**前置**：PicList 必须在运行（系统托盘有图标）。server 无响应就提示用户启动 PicList。

### 三种上传方式

1. **server API**（程序化/批量，推荐脚本与迁移用）—— 见下
2. **剪贴板快捷键** `Ctrl+Alt+P` —— 单张/交互，返回格式按 `pasteStyle`（当前 HTML）
3. **PicList GUI 拖拽** —— 主界面拖图到上传区

### server API 调用

```
POST http://127.0.0.1:36677/upload
Content-Type: application/json

{"list": ["C:\\absolute\\path\\img1.png", "C:\\path\\img2.jpg"]}
```

要点：
- `list` = **本机绝对路径**数组（不是 URL；远程图必须先下载到本机）。Mac 上是 `/Users/...` 形式，Windows 上是 `C:\...` 形式，路径分隔符按本机走。
- 默认图床：直接 POST。指定图床：`?picbed=lskyplist&configName=picltreen`。
- 返回 `result[i]` 与 `list[i]` **顺序对齐**——靠这个做链接替换。
- PicList 按其 `buildIn` 处理（默认转 webp + 清 EXIF + 质量 90 压缩）。

返回样例：
```json
{"success": true,
 "result": ["https://pic.ltreen.tech/uploads/20260615/abc.webp"],
 "fullResult": [{"imgUrl": "...", "fileName": "...", "type": "lskyplist",
                 "width": 64, "height": 48, "mimeType": "image/webp"}]}
```

PowerShell（Windows PowerShell 5.1 / pwsh 7+ 都可）：
```powershell
$body = @{ list = @("C:\path\a.png","C:\path\b.jpg") } | ConvertTo-Json
$resp = Invoke-RestMethod -Uri "http://127.0.0.1:36677/upload" -Method Post `
  -Body $body -ContentType "application/json" -TimeoutSec 180
$resp.result   # URL 数组，顺序与 list 一致
```

curl（Mac/Linux，PicList 也得在本机跑）：
```bash
curl -sS -X POST http://127.0.0.1:36677/upload \
  -H "Content-Type: application/json" \
  -d '{"list":["/Users/dht/path/a.png"]}'
```

### 跨机调用的限制

PicList `list` 只吃**本机路径**。Mac 上的图不能直接塞给 Windows 的 PicList——Windows 读不到 Mac 文件系统。要跨机：要么各自跑本地 PicList（推荐，配置见 `piclist-multi-machine.md`），要么先 `scp` 到目标机再调，要么走兰空直连 API。

## 兰空直连 API（路径 3）

公网 HTTPS 链路，**任何机器**（Mac/Linux/服务器/VPS）都能用，不依赖本地 PicList。

### 上传

```bash
# 必须带 strategy_id=1，否则返回"服务异常"
curl -X POST https://pic.ltreen.tech/api/v1/upload \
  -H "Authorization: Bearer 1|<40字符token>" \
  -F "file=@/path/img.png" -F "strategy_id=1"
```

成功返回（精简）：
```json
{"status": true, "message": "上传成功",
 "data": {
   "key": 26, "name": "<原文件名去扩展>",
   "pathname": "20260622/800f0698b9fd223981df06e25f5a4f78.png",
   "mimetype": "image/png", "extension": "png",
   "md5": "800f0698b9fd223981df06e25f5a4f78", "size": 0.31,
   "origin_name": "<原始文件名>",
   "links": {
     "url": "https://pic.ltreen.tech/uploads/20260622/800f0698b9fd223981df06e25f5a4f78.png",
     "html": "<img src=\"...\" alt=\"...\" />",
     "bbcode": "[img]...[/img]",
     "markdown": "![<原始文件名>](https://pic.ltreen.tech/uploads/...png)",
     "markdown_with_link": "[![...](...)](...)",
     "thumbnail_url": "..."
   }}}
```

URL 在 `data.links.url`，markdown 在 `data.links.markdown`。

### 与 PicList 路径的关键差异（实测 2026-06-22）

| 行为 | PicList（本机客户端处理） | 兰空 API（服务端处理） |
|------|--------------------------|----------------------|
| **格式转换** | ✅ png/jpg 上传前转 **webp** + 清 EXIF + 质量 90 | ❌ **不转格式**。png 仍是 png，按原 mimetype 落盘 |
| **EXIF 清理** | ✅ | ❌（原图 EXIF 保留） |
| **文件重命名** | 随兰空规则 | ✅ 按文件内容 **md5**（32 位）重命名，原文件名只在 `origin_name` 和 alt 文本 |
| **目录结构** | `YYYYMMDD/<md5>.<ext>` | `YYYYMMDD/<md5>.<ext>`（一致） |

**结论**：两条路径都会自动 md5 重命名 + 按日期分目录，但**只有 PicList 路径转 webp / 清 EXIF**。要在 Mac 上拿到 webp，又不想装 PicList：上传前自己转。

```bash
# macOS 自带 sips 转 webp
sips -s format webp input.png --out input.webp
# 或 cwebp（需 brew install webp）：cwebp -q 85 input.png -o input.webp
```

然后转出来的 `.webp` 路径传给兰空 API。

### token 获取 / 刷新

token 格式 `Bearer 1|<40字符>`（Laravel Sanctum）：
- **最省事**：从已配好 PicList 的机器读
  - Windows: `C:\Users\<user>\AppData\Roaming\piclist\data.json` → `picBed.lskyplist.token`
  - Mac: `~/Library/Application Support/piclist/data.json` → `picBed.lskyplist.token`
- 后台：`POST /api/v1/images/tokens`（需先登录）
- tinker：后台 `php artisan tinker` 里 `createToken`
- token 失效（401）→ 后台 `/admin` 重新生成 + 更新所有装了 PicList 的机器配置

### Mac/Linux 单图快速上传函数

```bash
# 加到 ~/.zshrc 或 ~/.bashrc
lsky_upload() {
  local f="$1"
  curl -sS -X POST https://pic.ltreen.tech/api/v1/upload \
    -H "Authorization: Bearer 1|<你的token>" \
    -F "file=@$f" -F "strategy_id=1" \
    | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['data']['links']['url'])"
}
lsky_upload /path/img.png   # → 打印公网 URL
```

## 迁移脚本（路径 4）

见 `../scripts/migrate-md-images.ps1`。脚本走 PicList server API，所以本机必须有 PicList 在跑。

跨平台说明：
- **Windows**：`pwsh -File migrate-md-images.ps1 -InputPath "...md"` 或 `powershell -File ...`
- **Mac**：需先 `brew install --cask powershell`，然后 `pwsh -File migrate-md-images.ps1 -InputPath "...md"`
- **Linux 服务器**：装 `pwsh` 后同样能跑，但要求该机有 PicList（一般服务器没有，这时改用兰空直连 API 手动迁移）

脚本参数：`-InputPath`（必填）、`-OutputPath`（默认 `.uploaded.md`）、`-PicBed`/`-ConfigName`（留空走默认）、`-DownloadTimeout`/`-UploadTimeout`。
