---
name: standard-report-auto-generation
description: Automatically generate, insert, update, and verify standard game-project weekly advertising report modules in Feishu Sheets. Use when an agent must select query_agent_wide_data parameters by project, aggregate by media/media+os, calculate user- or device-based acquisition and pure-new metrics, create the newest week above older modules, configure lark-cli-feishu-workflow, preserve a manual template, keep nine blank rows, write through Feishu OpenAPI, or audit weekly totals and formatting.
---

# 标准报表自动生成

严格执行“先读、再算、后写、再回读”。不要把空接口结果直接解释为没有投放，也不要改动用户指定的基准模板或手工数据。

## 前置检查

1. 完整读取本 Skill。
2. 读取 [`references/project-rules.json`](references/project-rules.json) 和 [`references/layout-and-metrics.md`](references/layout-and-metrics.md)。涉及飞书写入时再读取 [`references/feishu-write-and-verify.md`](references/feishu-write-and-verify.md)。
3. 必须加载 `$lark-cli-feishu-workflow`。若目标 Agent 尚未安装或授权，完整读取并执行 [`references/lark-cli-workflow-setup.md`](references/lark-cli-workflow-setup.md)，完成安装、配置、OAuth 用户授权和验权后再继续。
4. 检查工具和身份：

```bash
which xd-ad
xd-ad update --background
test -n "$XD_AD_KEY"
lark-cli whoami
lark-cli auth status --json --verify
```

5. 飞书必须使用用户身份。禁止使用 XD Feishu 插件。值写入优先使用 `feishu_identify` 获取 `user_access_token` 后，通过 Python `urllib.request` 调用 Sheets OpenAPI；`lark-cli` 用于读取、结构操作、格式复制和回读。

## 工作流

### 1. 确定周时间

- 正常周为周一至周日。
- 首周起始日不是周一时，从给定起始日开始，结束日仍严格取当周周日。
- 周模块按时间倒序排列。
- 新周日期比现有周更近时，在所有已有周模块上方插入。
- 完整模块后固定保留 9 行空白。
- 若周结束日在未来：查询截止日使用 `min(周结束日, 当前日期)`，标题仍写完整周区间，并在交付时说明数据截止日期。
- 若整个周尚未开始，只创建空白模板，禁止填 0 冒充数据。

### 2. 拉取正式数据

正式数据接口始终为：

```bash
xd-ad ad_adjust query_agent_wide_data \
  --group_by '["media","os"]' \
  --caliber '<user|device>' \
  --project_name '<项目准确名称>' \
  --start_dt YYYY-MM-DD \
  --end_dt YYYY-MM-DD \
  --page_size 5000
```

关键规则：

- 每次任务必须先确定项目准确名称、统计口径和报告指标口径。项目过滤使用 `project_name`，不要用 `tap_app_id` 代替。
- 开始拉数前向任务记录同步本次规则：`project_name`、`query_caliber`、`report_basis`、日期范围、`media + os`、排除规则、累计付费周期和目标工作簿。不要只说“沿用默认”。
- 周报渠道维度固定使用 `media`；分端固定使用 `media + os`。
- 默认规则由 `references/project-rules.json` 决定：火炬之光、香肠派对默认查询 `user` 并生成账号指标；未配置项目默认查询 `device` 并生成设备指标。
- 新项目首次执行时，把 `default` 仅视为候选规则。先用星云项目页面或用户给出的已知汇总核验；确认稳定后再把准确 `project_name`、别名、查询口径、报告口径和允许回退写入 `project-rules.json`。
- 用户明确指定账户/设备口径时，覆盖项目默认规则，并把覆盖项记录在交付结果中。
- 查询表口径 `caliber` 与报告指标口径 `report_basis` 分开：例如火炬 `user` 表尚未同步时，可经页面核验后用 `caliber=device` 查询，但报告仍按 `new_user_safe` 生成账号指标。
- 口径结果为空时，只能尝试项目规则允许的同接口回退并与项目页面交叉核验。不得改用 `query_ad_data` 作为普通周报正式数据源。
- 使用 [`scripts/query_week.py`](scripts/query_week.py) 生成标准化结果：

```bash
python3 scripts/query_week.py \
  --project '火炬之光' \
  --start 2026-08-24 \
  --end 2026-08-30 \
  --data-end 2026-08-28 \
  --caliber auto \
  --report-basis auto \
  --fallback-caliber auto \
  --output ./week.json
```

出现口径回退时，脚本会记录 `project_rule`、`requested_caliber`、`used_caliber`、`report_basis` 和警告。写入前必须人工确认回退结果与对应项目页面一致。

将标准化查询结果转换为 B:N 写入矩阵和逐行角色计划：

```bash
python3 scripts/build_module.py ./week.json --output ./module.json
```

先检查 `module.json` 的 `roles`、`values`、`module_height` 和 `insert_height_with_gap`，再执行任何飞书写入。

### 3. 过滤和计算

- 排除 `media=自然量`。
- 排除媒体名中包含 `REP`（不区分大小写）的渠道。
- 只写入 `real_cost > 0` 的渠道。当周消耗为 0 的渠道不写入。
- 仅保留 Android 和 iOS，分别按 `real_cost` 降序。
- 使用数值类型写入，不要把数字预格式化成字符串。
- 汇总行必须从当前模块的渠道行重新求和；比率和成本必须用汇总后的分子/分母重算，禁止相加或平均渠道比率。

指标公式见参考文件。账号口径使用 `new_user_safe`，设备口径使用 `new_device_safe`。纯新指标必须由相同口径的“总量减回归量”计算，不得混用账号与设备指标。

### 4. 读取并保护基准模块

写入前必须：

1. 用 `+workbook-info`、`+sheet-info` 获取 sheet ID、合并区域和行高。
2. 用 `+csv-get` 定位所有周标题行，以内容和日期判断，不得自己数行。
3. 用 `+cells-get --include value,formula,style` 保存：
   - 用户指定基准模块；
   - 即将插入位置附近的既有模块；
   - 目标区域。
4. 记录基准模块的值、公式、样式、合并区域和行高，作为回退快照。

禁止：

- 覆盖基准模板值；
- 改动用户手工数据；
- 用 `copy-to-range` 或普通复制粘贴复制值/公式；
- 仅按行号猜测行角色；
- 未回读就声称完成。

### 5. 创建新模块

模块高度根据实际渠道行数计算，详见参考文件。若新周最新：

1. 在第一块周报标题行前插入 `模块高度 + 9` 行。
2. 只复制基准格式：`+range-copy --paste-type formats`。
3. 按内容角色建立合并：总标题、汇总端口、分端标题、分端合计。
4. 按基准设置行高；表头含换行的 N 列必须写成 `纯新首日\nROAS`。
5. 模块之外的 9 行间隔保持无值、无边框；工作表其余空白区不显示网格线。

若渠道行数与基准不同，不要整块机械复制。逐类复制：总标题、汇总表头、汇总数据、汇总合计、分端标题、分端表头、渠道数据、分端合计。

### 6. 写入数据

通过 Sheets OpenAPI `values_batch_update` 写入，使用 `USER_ENTERED`。写入范围必须明确到新模块，不得覆盖相邻模块。

- 金额、人数、ROAS 等写数值，不写带 `¥`、逗号或 `%` 的字符串。
- 为避免飞书把公式当文本，周报派生值默认在本地计算后写静态数值；除非已在该表验证公式对象能正确解析。
- 标题和表头按模板原文写入。
- 进行中周标题保留完整周区间，数据只汇总到实际数据截止日。

### 7. 回读验收

写入后必须完成全部检查：

1. 用 OpenAPI 回读精确写入范围，逐格比对预期值。
2. 独立重算 Android、iOS、总计，确认合计等于渠道行之和。
3. 检查渠道排序、过滤条件和数据截止日。
4. 用 `+cells-get --include value,formula,style` 对比新模块与基准的对应角色。
5. 检查 N 列三处表头换行、数字格式、底色、字体、边框、合并、行高。
6. 回读基准模块，与写入前快照比较；值、公式、样式差异必须为 0。
7. 确认新模块后恰好 9 行空白，且旧模块仍按时间倒序。

只有以上检查通过才能向用户报告完成。报告中注明：查询接口、实际口径、周区间、数据截止日、写入位置、合计值和基准未改动的验证结果。

## 失败处理

- 首选 `caliber` 为空：不要写空周；按项目规则尝试允许的同接口口径，并与对应项目页面核验。
- 单格 OpenAPI 范围报 `wrong range`：使用完整范围，如 `N4:N4`。
- 格式复制后少数合并单元格样式不同：只增量修复差异字段，禁止解除基准合并。
- 插入位置错误：先回读确认新增行完全属于本次操作，再精确删除该范围；随后按“最新周向上插入”重建。
- API 请求成功不代表表格正确：始终回读。
