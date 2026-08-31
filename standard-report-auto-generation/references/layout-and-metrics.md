# 周报结构与指标

## 目录

1. 数据过滤
2. 指标映射
3. 模块结构
4. 数字格式
5. 日期与排序

## 数据过滤

使用 `query_agent_wide_data`，按 `media + os` 聚合。保留条件：

```text
os in {Android, iOS}
media != 自然量
"rep" not in media.lower()
real_cost > 0
```

Android、iOS 各自按 `real_cost` 降序。

## 项目参数与指标映射

先读取 `project-rules.json`：

- `query_caliber` 决定查询 `user` 或 `device` 宽表。
- `report_basis` 决定周报展示账号还是设备指标。
- `fallback_calibers` 只表示该项目允许核查的同接口回退；回退结果必须与项目页面交叉验证。
- 未配置项目使用 `default`。新增项目的稳定规则应写入配置文件，不要散落在脚本条件分支中。

查询表口径和报告指标口径不可混为一谈。后端用 device 表回退时，如果项目规则的 `report_basis=user`，仍从返回行读取 `new_user_safe`，不能改成设备指标。

### 账号口径

| 周报字段 | 计算方式 |
|---|---|
| 广告消耗 | `real_cost`，缺失时才检查 `cost` |
| 广告新增账号 | `new_user_safe` |
| 新增账号成本 | `real_cost / new_user_safe` |
| 首日付费 | `day1_paid_amount` |
| 首日 ROAS | `day1_paid_amount / real_cost` |
| 累计付费 | `day720_paid_amount`（作为当前可得累计值） |
| 累计 ROAS | `day720_paid_amount / real_cost` |
| 纯新账号 | `max(new_user_safe - reattr_new_user_safe, 0)` |
| 纯新账号成本 | `real_cost / 纯新账号` |
| 首日纯新付费 | `max(day1_paid_amount - day1_paid_amount_reattr, 0)` |
| 纯新首日 ROAS | `首日纯新付费 / real_cost` |

### 设备口径

将上表的账号字段替换为：

| 周报字段 | 计算方式 |
|---|---|
| 广告新增设备 | `new_device_safe` |
| 新增设备成本 | `real_cost / new_device_safe` |
| 纯新设备 | `max(new_device_safe - reattr_new_device_safe, 0)` |
| 纯新设备成本 | `real_cost / 纯新设备` |

付费、累计付费和 ROAS 公式不变。

分母为 0 时结果写 0。汇总行先分别求和原始分子和分母，再重算成本与比率。

## 模块结构

角色顺序：

1. 总标题行
2. 汇总表头行
3. Android 汇总数据行
4. iOS 汇总数据行
5. 汇总合计行
6. 空行
7. Android 分端标题行
8. Android 分端表头行
9. Android 渠道数据行（N 行）
10. Android 合计行
11. 空行
12. iOS 分端标题行
13. iOS 分端表头行
14. iOS 渠道数据行（M 行）
15. iOS 合计行

模块高度：

```text
13 + Android渠道数 + iOS渠道数
```

模块后再保留 9 行空白。若某端没有正消耗渠道，仍保留分端标题、表头和合计行；合计写 0，不伪造渠道行。

列 B:N：

| 列 | 字段 |
|---|---|
| B | 日期 / 端口 / 标题 |
| C | 投放渠道 |
| D | 广告消耗 |
| E | 广告新增账号 / 广告新增设备（由 report_basis 决定） |
| F | 新增账号成本 / 新增设备成本 |
| G | 首日付费 |
| H | 首日 ROAS |
| I | 累计付费 |
| J | 累计 ROAS |
| K | 纯新账号 / 纯新设备 |
| L | 纯新账号成本 / 纯新设备成本 |
| M | 首日纯新付费 |
| N | 纯新首日 ROAS |

N 列表头必须包含换行：`纯新首日\nROAS`。

## 数字格式

以基准模块实际格式为准。常用规则：

- D、G、I、M：整数货币，`¥#,##0`
- E、K：整数，`#,##0`
- F、L：一位小数货币，`¥#,##0.0`
- H、J、N：百分比一位小数，`0.0%`

格式复制按内容角色执行，不按绝对行号执行。

## 日期与排序

- 标题：`M月D日-M月D日国服投放汇总`
- 数据日期：`M.D-M.D`
- 每周周一至周日；不完整首周仍在周日结束。
- 最新周插在顶部；旧模块整体下移但内容与格式不得改变。
- 进行中周只查询到当前日期，不能查询未来日期后把空值当 0。
