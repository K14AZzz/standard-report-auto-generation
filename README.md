# 标准报表自动生成

一套可复用的 Codex Skills，用于按项目规则拉取广告数据、生成标准周报模块，并通过飞书用户身份安全写入和回读核验。

仓库包含两个 Skill：

- `standard-report-auto-generation`：项目规则、周报结构、数据计算、写入与验收流程。
- `lark-cli-feishu-workflow`：`lark-cli` 安装、OAuth 用户授权、表格读取、格式修改和回读验证流程。

## 安装

将两个目录复制到 Codex Skills 目录：

```bash
git clone https://github.com/K14AZzz/standard-report-auto-generation.git
cp -R standard-report-auto-generation/standard-report-auto-generation ~/.codex/skills/
cp -R standard-report-auto-generation/lark-cli-feishu-workflow ~/.codex/skills/
```

重新开启一个 Codex 会话后即可调用：

```text
使用 $standard-report-auto-generation 为指定项目生成标准周报
```

## 首次配置

1. 按 `standard-report-auto-generation/references/lark-cli-workflow-setup.md` 安装并配置 `lark-cli`。
2. 完成飞书 Sheets OAuth 用户授权，并执行 `lark-cli auth status --json --verify` 验证身份。
3. 在 `standard-report-auto-generation/references/project-rules.json` 中补充项目的：
   - `project_name`
   - `query_caliber`
   - `report_basis`
   - `fallback_calibers`
4. 确认运行环境可调用 `query_agent_wide_data`，并配置其所需凭证。
5. 每次任务由用户提供目标飞书表格、子表和基准模板；不要把真实 token 或凭证写入 Skill。

### 常见授权错误：`client secret is invalid`

这表示 CLI 还没有通过应用凭证校验，不是表格权限错误。请确认 App ID 和 App Secret 来自同一个飞书自建应用，Secret 没有被重新生成，且没有把用户 token、占位符或带引号/空格的文本当作 Secret。推荐通过 stdin 重配：

```bash
printf '%s\n' "$FEISHU_APP_SECRET" | \
  lark-cli config init --app-id "$FEISHU_APP_ID" --app-secret-stdin --brand feishu
lark-cli whoami
lark-cli auth status --json --verify
```

配置成功后再执行 `lark-cli auth login --domain sheets --no-wait --json`，每次都使用新生成的 device code。不要把 App Secret、access token 或 OAuth 缓存提交到 GitHub；给不同使用者配置时，建议每人使用自己的飞书应用凭证。

## 默认规则

- 数据接口：`query_agent_wide_data`
- 渠道维度：`media`
- 分端维度：`media + os`
- 排除自然量、REP 和时段内零消耗渠道
- 最新周模块插入到旧周上方
- 周模块之间保留 9 行空白
- 飞书值写入使用用户身份 OpenAPI
- 写入后回读，并复算渠道合计、分端合计和纯新指标
- 不修改用户指定的基准模板和手工数据

## 安全说明

不要提交 access token、app secret、OAuth 缓存、`.env` 文件或真实工作簿 token。直连 OpenAPI 的可选本地 helper 目录通过 `FEISHU_IDENTIFY_PATH` 环境变量提供。
