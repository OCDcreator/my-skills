# 翻译 API 调用参考（translation-api.md）

**仅在用户明确要求调 API 翻译、或字符串量很大（> 200 条）时读本文件。** 默认 agent 直接翻译即可。

本文件给出 OpenAI、DeepL、百度翻译的批量调用模板。原则：**批量打包、逐行对应、校验回填**。

## 通用原则

1. **批量**：每批发送 ≤ 50 条或 ≤ 4KB，避免超长截断
2. **逐行对应**：要求 API "按顺序逐行返回译文，条数必须一致"
3. **占位符保护**：`${n}` `{{date}}` `%s` `{0}` 在 prompt 里明确要求保留
4. **回填校验**：收到的译文条数必须 = 发送条数，否则整批重试

## 批量请求格式（推荐）

把待翻译条目编号发送，让 API 按编号返回，便于校验：

```
请将以下 Obsidian 插件界面文本翻译为简体中文。
要求：
1. 只返回译文，按行对应，每行一条，行首带编号
2. 保留 ${...} {{...}} %s 等占位符原样不动
3. 符合软件界面中文习惯

1. Auto backup
2. Backup every X minutes
3. Save changes
...
```

期望返回：
```
1. 自动备份
2. 每 X 分钟备份一次
3. 保存更改
```

## OpenAI / 兼容 API

```bash
# 批量翻译脚本示例（保存为 translate.js，按需改）
node -e '
const https = require("https");
const entries = require("./pending.json"); // { items: ["Auto backup", ...] }

const body = JSON.stringify({
  model: "gpt-4o-mini",
  messages: [
    { role: "system", content: "你是 Obsidian 插件翻译助手。只返回译文，逐行对应，保留 ${} {{}} %s 占位符。" },
    { role: "user", content: entries.items.map((s,i)=>`${i+1}. ${s}`).join("\n") }
  ],
  temperature: 0.3
});

const req = https.request({
  hostname: "api.openai.com",   // 或用户的代理域名
  path: "/v1/chat/completions",
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + process.env.OPENAI_API_KEY
  }
}, res => {
  let d = "";
  res.on("data", c => d += c);
  res.on("end", () => {
    const txt = JSON.parse(d).choices[0].message.content;
    const lines = txt.trim().split("\n")
      .map(l => l.replace(/^\d+\.\s*/, "")); // 去编号
    if (lines.length !== entries.items.length) {
      console.error("条数不一致! 期望", entries.items.length, "得到", lines.length);
      process.exit(1);
    }
    console.log(JSON.stringify(lines));
  });
});
req.on("error", e => { console.error(e); process.exit(1); });
req.write(body);
req.end();
'
```

环境变量：`OPENAI_API_KEY`、可选 `OPENAI_BASE_URL`（代理）。

**自定义端点**：用户可能用国内代理（如 `https://api.deepseek.com`、`https://oneapi.xxx.com`）。改 hostname 即可，模型名也要对应改。

## DeepL

DeepL 适合英→中批量，质量高。免费版每月 50 万字符。

```bash
curl -s https://api-free.deepl.com/v2/translate \
  -H "Authorization: DeepL-Auth-Key $DEEPL_API_KEY" \
  -d "text=Auto backup" \
  -d "text=Backup every X minutes" \
  -d "target_lang=ZH"
```

返回 JSON 里的 `translations[].text` 与请求 `text=` 顺序一致，可直接对应。
注意：DeepL 对 `${}` 占位符偶尔会改动，**回填后必须抽查**。

## 百度翻译

适合国内、免费额度大（标准版 QPS 1）。**注意 QPS 限制**，需加间隔。

i18n 插件的 data.json 里已有配置字段：`I18N_NIT_APIS.BAIDU.{APP_ID, KEY}`。可复用用户的 key。

百度要签名（MD5）：
```bash
node -e '
const crypto = require("crypto");
const appId = process.env.BAIDU_APP_ID;
const key = process.env.BAIDU_KEY;
const q = "Auto backup";
const salt = Date.now().toString();
const sign = crypto.createHash("md5").update(appId + q + salt + key).digest("hex");
const url = `https://fanyi-api.baidu.com/api/trans/vip/translate?q=${encodeURIComponent(q)}&from=en&to=zh&appid=${appId}&salt=${salt}&sign=${sign}`;
fetch(url).then(r=>r.json()).then(d=>console.log(d.trans_result[0].dst));
'
```
百度一次只翻一条（或少量），**量大时必须加 500ms+ 间隔**，否则封 IP。

## 模式选择建议

| 场景 | 推荐 |
|---|---|
| < 100 条，一次性 | agent 直译（默认） |
| 100-300 条 | agent 直译，或 OpenAI 批量 |
| > 300 条 | OpenAI 批量（成本低、快） |
| 只要中→英质量 | DeepL |
| 国内无梯子 | 百度 / 国内 OpenAI 代理 |

## 失败处理

- API 超时/限流：指数退避重试，最多 3 次
- 条数不一致：整批重试，降 temperature 到 0
- 译文含未授权改动（占位符被改）：标记该条，回退到 agent 直译或人工

## 安全提醒

- API key **绝不写入 skill 文件或翻译清单**，只从环境变量或用户当场提供的临时配置读
- 翻译完即丢弃 key，不持久化
