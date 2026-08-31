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
