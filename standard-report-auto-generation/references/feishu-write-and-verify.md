# 飞书写入与验证

## 目录

1. 目标工作簿
2. 认证
3. 读取与结构操作
4. 值写入
5. 样式对齐
6. 验证与回退

## 目标工作簿

目标工作簿和子表必须由用户输入或任务上下文明确提供。不要在 Skill 中固化真实工作簿 token、sheet ID 或 sheet name。每次先用 `+workbook-info` 复核目标工作簿、sheet ID、sheet name 和基准模块。

## 认证

如果 `$lark-cli-feishu-workflow` 尚未配置，先执行 `lark-cli-workflow-setup.md` 的完整流程。

用户身份检查：

```bash
lark-cli whoami
lark-cli auth status --json --verify
```

直连 OpenAPI 时，优先复用运行环境已有的用户 OAuth helper，并通过环境变量提供其安装目录：

```python
import os
from pathlib import Path
import sys

tool_dir_value = os.environ.get("FEISHU_IDENTIFY_PATH")
if not tool_dir_value:
    raise RuntimeError("Set FEISHU_IDENTIFY_PATH to the directory containing feishu_identify.py")
tool_dir = Path(tool_dir_value).expanduser().resolve()
sys.path.insert(0, str(tool_dir))
from feishu_identify import get_access_token

token = get_access_token()
```

若运行环境没有该 helper，则按 `lark-cli-workflow-setup.md` 完成 OAuth，并使用 `lark-cli` 用户身份路径。禁止打印 token，也不要把 token、app secret 或本地凭证文件提交到版本库。

## 读取与结构操作

```bash
lark-cli sheets +workbook-info --url '<sheet-url>'
lark-cli sheets +sheet-info --spreadsheet-token '<token>' --sheet-id '<sheet-id>' \
  --include merges,row_heights,col_widths,hidden_rows,hidden_cols,frozen
lark-cli sheets +csv-get --spreadsheet-token '<token>' --sheet-id '<sheet-id>' \
  --range A1:AN500
lark-cli sheets +cells-get --spreadsheet-token '<token>' --sheet-id '<sheet-id>' \
  --range B3:N17 --include value,formula,style --output-path ./snapshot.json
```

插入前确认目标位置。新周最新时，在首个模块标题行前插入：

```bash
lark-cli sheets +dim-insert --spreadsheet-token '<token>' --sheet-id '<sheet-id>' \
  --position '<first-title-row>' --count '<module-height-plus-9>' --inherit-style before --as user
```

复制格式时使用：

```bash
lark-cli sheets +range-copy --spreadsheet-token '<token>' --sheet-id '<sheet-id>' \
  --source-range '<reference-range>' --target-range '<new-anchor>' \
  --paste-type formats --as user
```

## 值写入

接口：

```text
POST /open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values_batch_update
```

请求体：

```json
{
  "valueRanges": [
    {
      "range": "<sheet-id>!B3:N17",
      "values": [["..."], ["..."]]
    }
  ],
  "valueInputOption": "USER_ENTERED"
}
```

单个单元格也要写完整范围，例如 `<sheet-id>!N4:N4`，不要写 `<sheet-id>!N4`。

## 样式对齐

优先复制格式，再增量修复差异。需要直接设置样式时使用：

```text
PUT /open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/styles_batch_update
```

或 `lark-cli sheets +cells-set-style`。只传需要修复的字段，避免覆盖背景色、边框或数字格式。

合并单元格中的内部单格可能无法作为 `range-copy` 源；此时使用 `+cells-set-style` 增量设置对应边框或数字格式，不要解除基准合并。

## 验证与回退

写入后：

1. OpenAPI 回读新模块值。
2. `+cells-get` 回读新模块和基准样式。
3. 归一化颜色表示后逐格比较 `cell_styles` 和 `border_styles`。
4. 核对合并和行高。
5. 比较基准写前/写后快照，差异必须为 0。
6. 若插错位置，只删除能证明属于本次新增且未写入用户数据的精确行范围；先 `--dry-run`，再 `--yes`。

任何写入失败、部分成功或无法证明基准未变时，停止并如实报告，不要继续批量修改。
