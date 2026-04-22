# 远程连接 OpenCode Server 执行代码质量检查

## 核心命令

从 Windows 机器远程连接到 `192.168.1.50:4096` 上的 OpenCode server，并在 `/home/user/myproject` 目录下检查代码质量：

```bash
opencode run "检查代码质量，包括代码规范、性能问题、安全隐患和可维护性" --attach http://192.168.1.50:4096 --password mypass --dir /home/user/myproject
```

## 参数说明

- `--attach http://192.168.1.50:4096` - 连接到远程运行的 OpenCode server
- `--password mypass` - 提供 Basic Auth 密码进行身份验证
- `--dir /home/user/myproject` - 指定远程服务器上的工作目录

## 常用变体

### 1. 指定具体文件检查
```bash
opencode run "审查这些文件的问题" --attach http://192.168.1.50:4096 --password mypass --dir /home/user/myproject -f src/main.ts -f src/utils.ts
```

### 2. JSON 格式输出（便于脚本处理）
```bash
opencode run "检查代码质量" --attach http://192.168.1.50:4096 --password mypass --dir /home/user/myproject --format json
```

### 3. 指定模型
```bash
opencode run "检查代码质量" --attach http://192.168.1.50:4096 --password mypass --dir /home/user/myproject -m anthropic/claude-sonnet-4
```

### 4. 跳过权限确认（自动化场景）
```bash
opencode run "检查代码质量并自动修复简单问题" --attach http://192.168.1.50:4096 --password mypass --dir /home/user/myproject --dangerously-skip-permissions
```

## 完整示例

```bash
# 在远程服务器上对整个项目进行代码质量审查
opencode run "请对 /home/user/myproject 目录下的代码进行全面的质量检查，包括：
1. 代码规范和风格问题
2. 潜在的性能问题
3. 安全隐患（如 SQL 注入、XSS 等）
4. 代码重复和可维护性问题
5. 缺少错误处理的地方
6. 测试覆盖率不足的模块

请给出具体的问题位置和修复建议。" \
--attach http://192.168.1.50:4096 \
--password mypass \
--dir /home/user/myproject \
--format json
```

## 注意事项

1. **网络可达性**：确保 Windows 机器可以访问 `192.168.1.50:4096`（检查防火墙设置）
2. **密码安全**：在脚本中使用时，考虑通过环境变量传递密码而不是硬编码
3. **工作目录权限**：确保 OpenCode server 对 `/home/user/myproject` 有读取权限
4. **自动化场景**：如果需要完全自动化执行，使用 `--dangerously-skip-permissions` 跳过工具调用权限确认（仅在可信环境中使用）
