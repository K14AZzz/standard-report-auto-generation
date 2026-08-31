#!/usr/bin/env python3
"""Build the B:N value matrix and row-role plan from query_week.py output."""

import argparse
import json
from datetime import date
from pathlib import Path


def labels(report_basis):
    unit = "账号" if report_basis == "user" else "设备"
    return {
        "acquisition": f"广告新增{unit}",
        "acquisition_cost": f"新增{unit}成本",
        "pure": f"纯新{unit}",
        "pure_cost": f"纯新{unit}成本",
    }


def headers(report_basis):
    text = labels(report_basis)
    summary = [
        "端口", "", "广告消耗", text["acquisition"], text["acquisition_cost"], "首日付费",
        "首日ROAS", "累计付费", "累计ROAS", text["pure"], text["pure_cost"],
        "首日纯新付费", "纯新首日\nROAS",
    ]
    detail = ["日期", "投放渠道"] + summary[2:]
    return summary, detail


def metric_values(label, channel, row):
    return [
        label, channel, row["real_cost"], row["acquisition_count"], row["acquisition_cost"],
        row["day1_paid_amount"], row["day1_roas"], row["day720_paid_amount"],
        row["cumulative_roas"], row["pure_acquisition_count"], row["pure_acquisition_cost"],
        row["pure_day1_paid_amount"], row["pure_day1_roas"],
    ]


def cn_title(start, end, market_label):
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    return f"{start_date.month}月{start_date.day}日-{end_date.month}月{end_date.day}日{market_label}投放汇总"


def short_range(start, end):
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    return f"{start_date.month}.{start_date.day}-{end_date.month}.{end_date.day}"


def build(data):
    summary_header, detail_header = headers(data["report_basis"])
    project = data["project"]
    market_label = data.get("market_label", "国服")
    week_label = short_range(data["week_start"], data["week_end"])
    android_rows = data["rows"]["Android"]
    ios_rows = data["rows"]["iOS"]
    values, roles = [], []

    def add(role, row):
        roles.append(role)
        values.append(row)

    add("summary_title", [cn_title(data["week_start"], data["week_end"], market_label), "", "", "不含商务费"] + [""] * 9)
    add("summary_header", summary_header)
    add("summary_android", metric_values("安卓", "", data["totals"]["Android"]))
    add("summary_ios", metric_values("iOS", "", data["totals"]["iOS"]))
    add("summary_total", metric_values("合计", "", data["totals"]["all"]))
    add("internal_blank", [""] * 13)
    add("android_title", [f"【{project}】{market_label}安卓投放"] + [""] * 12)
    add("android_header", detail_header)
    for row in android_rows:
        add("android_data", metric_values(week_label, row["media"], row))
    add("android_total", metric_values("合计", "", data["totals"]["Android"]))
    add("internal_blank", [""] * 13)
    add("ios_title", [f"【{project}】{market_label}iOS投放"] + [""] * 12)
    add("ios_header", detail_header)
    for row in ios_rows:
        add("ios_data", metric_values(week_label, row["media"], row))
    add("ios_total", metric_values("合计", "", data["totals"]["iOS"]))

    return {
        "project": project,
        "week_start": data["week_start"],
        "week_end": data["week_end"],
        "data_end": data["data_end"],
        "used_caliber": data["used_caliber"],
        "report_basis": data["report_basis"],
        "warnings": data.get("warnings", []),
        "module_height": len(values),
        "insert_height_with_gap": len(values) + 9,
        "columns": "B:N",
        "roles": roles,
        "values": values,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build(json.loads(args.input.read_text(encoding="utf-8")))
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
