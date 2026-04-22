# 远程连接 OpenCode Server 执行代码质量检查

## 连接到远程 OpenCode Server

### 方法 1: 使用 SSH 隧道 + OpenCode CLI

在 Windows 机器上，首先建立 SSH 隧道：

```powershell
ssh -L 4096:localhost:4096 user@192.168.1.50
```

然后在另一个 PowerShell 窗口中使用 OpenCode CLI：

```powershell
opencode attach --host localhost --port 4096 --password mypass
```

### 方法 2: 直接连接（如果 OpenCode 支持远程连接）

```powershell
opencode attach --host 192.168.1.50 --port 4096 --password mypass
```

### 方法 3: 使用配置文件

创建 `opencode.config.json`:

```json
{
  "remote": {
    "host": "192.168.1.50",
    "port": 4096,
    "password": "mypass",
    "workspace": "/home/user/myproject"
  }
}
```

然后连接：

```powershell
opencode attach --config opencode.config.json
```

## 执行代码质量检查

### 连接后执行

连接成功后，切换到目标目录并执行检查：

```bash
cd /home/user/myproject
opencode review work
```

### 一行命令执行

```powershell
opcode --host 192.168.1.50 --port 4096 --password mypass --workspace /home/user/myproject review work
```

### 使用完整命令参数

```powershell
opencode attach \
  --host 192.168.1.50 \
  --port 4096 \
  --password mypass \
  --workspace /home/user/myproject \
  --command "review work"
```

## 常用代码质量检查命令

- **完整代码审查**: `opencode review work`
- **代码质量检查**: `opencode lint`
- **运行测试**: `opencode test`
- **类型检查**: `opencode typecheck`
- **安全审计**: `opencode audit --security`

## Windows PowerShell 完整示例

```powershell
# 连接到远程服务器并执行代码审查
opencode attach `
  --host 192.168.1.50 `
  --port 4096 `
  --password mypass `
  --workspace /home/user/myproject `
  --command "review work"

# 或者先连接再执行
opencode attach --host 192.168.1.50 --port 4096 --password mypass
# 然后在交互式会话中
cd /home/user/myproject
review work
```

## 注意事项

1. **SSH 密钥认证**: 推荐使用 SSH 密钥而非密码
2. **防火墙**: 确保 4096 端口在防火墙中开放
3. **网络连接**: Windows 和远程机器需要在同一网络或可互相访问
4. **权限**: 确保用户对 /home/user/myproject 有读写权限
5. **OpenCode 版本**: 确保两端 OpenCode 版本兼容

## 环境变量配置（可选）

```powershell
$env:OPENCODE_HOST="192.168.1.50"
$env:OPENCODE_PORT="4096"
$env:OPENCODE_PASSWORD="mypass"
$env:OPENCODE_WORKSPACE="/home/user/myproject"

opencode attach
```
