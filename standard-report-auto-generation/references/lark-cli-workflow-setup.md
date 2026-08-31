# lark-cli-feishu-workflow 配置

## 目录

1. 安装 Skill
2. 检查 lark-cli
3. 初始化或绑定配置
4. OAuth 用户授权
5. 验权
6. 常见问题

## 安装 Skill

目标 Agent 应同时安装：

```text
standard-report-auto-generation Skill（本包）
lark-cli-feishu-workflow Skill
```

标准安装位置：

```text
${CODEX_HOME:-$HOME/.codex}/skills/lark-cli-feishu-workflow/SKILL.md
```

如果使用分发 ZIP，将两个 Skill 文件夹一起解压到 `${CODEX_HOME:-$HOME/.codex}/skills/`。安装后重新开启 Agent 会话，让 Skill 清单重新加载。

## 检查 lark-cli

```bash
which lark-cli
lark-cli --version
```

不要硬编码某台机器的二进制路径。若环境未安装，优先使用运行环境提供的安装方式；可用的 Lark CLI Skill 安装入口为：

```bash
npx skills add larksuite/cli -g -y
```

安装后再次执行 `which lark-cli`。如果命令仍不存在，停止并让环境管理员提供完整 CLI；不要伪造 OpenAPI 命令。

## 初始化或绑定配置

先检查当前配置：

```bash
lark-cli whoami
lark-cli auth status --json --verify
```

尚未配置时：

```bash
lark-cli config init --new
```

如果 Agent 环境已经有飞书凭证来源，优先绑定已有配置：

```bash
lark-cli config bind
```

不要为了同一个用户静默创建第二套应用配置。需要多个环境时使用明确的 `--profile <name>`。

## OAuth 用户授权

周报写入必须使用用户身份，申请最小 Sheets 域：

```bash
lark-cli auth login --domain sheets --no-wait --json
```

从结果记录 `verification_url` 和 `device_code`：

```bash
lark-cli auth qrcode '<verification_url>' --output ./feishu-auth.png
```

让用户扫码并确认后，由 Agent 完成：

```bash
lark-cli auth login --device-code '<device_code>'
```

不得修改验证 URL，不得复用过期 device code，不得在日志中输出 access token、app secret。

## 验权

```bash
lark-cli whoami
lark-cli auth status --json --verify
```

验收条件：

- `identity=user`
- `available=true`
- `verified=true`
- token 状态为 `ready`，或为可自动刷新的 `needs_refresh` 且已授予 `offline_access`
- scope 至少包含 Sheets 读取、写入和元信息权限

`needs_refresh` 时不要臆造 refresh 命令；当前 CLI 会在实际 API 调用时使用 refresh token。直接用目标工作簿做只读探测：

```bash
lark-cli sheets +workbook-info --url '<spreadsheet-url>' --as user
lark-cli sheets +csv-get --url '<spreadsheet-url>' --sheet-name '<sheet-name>' --range A1:N5 --as user
```

只读探测成功即证明当前授权可用；之后才能执行插行、样式或值写入。

## 常见问题

- `请求不合法`：核对 OAuth 回调、品牌（Feishu/Lark）、profile 和 device code 是否匹配；重新发起登录，不要改 URL。
- `sheet not found`：`--sheet-name` 必须传真实名称；短链接参数里的 sheet ID 不是 sheet name。
- 用户身份不可用：重新执行 Sheets 域 OAuth；不要切到 bot 身份绕过。
- CLI 能读不能写：检查 scope 与文档权限；先解决权限，不要改用浏览器批量覆盖。
- 认证仍受限时，使用同一 OAuth 用户身份的 `feishu_identify + urllib` 直连 Sheets OpenAPI；Computer Use 只作 UI 兜底。
