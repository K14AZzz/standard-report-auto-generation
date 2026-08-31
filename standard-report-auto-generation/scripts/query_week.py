#!/usr/bin/env python3
"""Query and normalize one project's weekly advertising period."""

import argparse
import json
import subprocess
from pathlib import Path


RULES_PATH = Path(__file__).resolve().parent.parent / "references" / "project-rules.json"


def load_rules(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_rule(project, rules):
    for key, rule in rules.get("projects", {}).items():
        aliases = set(rule.get("aliases", [])) | {key, rule.get("project_name", key)}
        if project in aliases:
            return key, rule
    return "default", {**rules["default"], "project_name": project, "aliases": [project]}


def run_query(start, end, caliber, project):
    command = [
        "xd-ad", "ad_adjust", "query_agent_wide_data",
        "--group_by", '["media","os"]',
        "--caliber", caliber,
        "--project_name", project,
        "--start_dt", start,
        "--end_dt", end,
        "--page_size", "5000",
    ]
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def number(value):
    return float(value or 0)


def normalize(data, report_basis):
    count_key = "new_user_safe" if report_basis == "user" else "new_device_safe"
    reattr_count_key = "reattr_new_user_safe" if report_basis == "user" else "reattr_new_device_safe"
    output = {"Android": [], "iOS": []}
    for raw in data.get("list", []):
        media = str(raw.get("media") or "").strip()
        os_name = str(raw.get("os") or "").strip()
        metrics = dict(raw.get("metrics") or {})
        cost = number(metrics.get("real_cost") or metrics.get("cost"))
        if os_name not in output or media == "自然量" or "rep" in media.lower() or cost <= 0:
            continue
        acquisitions = number(metrics.get(count_key))
        reattr_acquisitions = number(metrics.get(reattr_count_key))
        paid1 = number(metrics.get("day1_paid_amount"))
        reattr_paid1 = number(metrics.get("day1_paid_amount_reattr"))
        cumulative = number(metrics.get("day720_paid_amount"))
        pure_acquisitions = max(acquisitions - reattr_acquisitions, 0)
        pure_paid1 = max(paid1 - reattr_paid1, 0)
        output[os_name].append({
            "media": media,
            "os": os_name,
            "real_cost": cost,
            "acquisition_count": acquisitions,
            "acquisition_cost": cost / acquisitions if acquisitions else 0,
            "day1_paid_amount": paid1,
            "day1_roas": paid1 / cost if cost else 0,
            "day720_paid_amount": cumulative,
            "cumulative_roas": cumulative / cost if cost else 0,
            "pure_acquisition_count": pure_acquisitions,
            "pure_acquisition_cost": cost / pure_acquisitions if pure_acquisitions else 0,
            "pure_day1_paid_amount": pure_paid1,
            "pure_day1_roas": pure_paid1 / cost if cost else 0,
        })
    for rows in output.values():
        rows.sort(key=lambda row: row["real_cost"], reverse=True)
    return output


def total(rows):
    cost = sum(row["real_cost"] for row in rows)
    acquisitions = sum(row["acquisition_count"] for row in rows)
    paid1 = sum(row["day1_paid_amount"] for row in rows)
    cumulative = sum(row["day720_paid_amount"] for row in rows)
    pure_acquisitions = sum(row["pure_acquisition_count"] for row in rows)
    pure_paid1 = sum(row["pure_day1_paid_amount"] for row in rows)
    return {
        "real_cost": cost,
        "acquisition_count": acquisitions,
        "acquisition_cost": cost / acquisitions if acquisitions else 0,
        "day1_paid_amount": paid1,
        "day1_roas": paid1 / cost if cost else 0,
        "day720_paid_amount": cumulative,
        "cumulative_roas": cumulative / cost if cost else 0,
        "pure_acquisition_count": pure_acquisitions,
        "pure_acquisition_cost": cost / pure_acquisitions if pure_acquisitions else 0,
        "pure_day1_paid_amount": pure_paid1,
        "pure_day1_roas": pure_paid1 / cost if cost else 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="Exact project_name or configured alias")
    parser.add_argument("--start", required=True, help="Week start YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Week title end YYYY-MM-DD")
    parser.add_argument("--data-end", help="Actual query end; defaults to --end")
    parser.add_argument("--caliber", choices=("auto", "user", "device"), default="auto")
    parser.add_argument("--report-basis", choices=("auto", "user", "device"), default="auto")
    parser.add_argument("--fallback-caliber", choices=("auto", "none", "user", "device"), default="auto")
    parser.add_argument("--market-label", default="国服")
    parser.add_argument("--rules", type=Path, default=RULES_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rules = load_rules(args.rules)
    rule_key, rule = resolve_rule(args.project, rules)
    project_name = rule.get("project_name", args.project)
    requested = rule["query_caliber"] if args.caliber == "auto" else args.caliber
    report_basis = rule["report_basis"] if args.report_basis == "auto" else args.report_basis
    fallbacks = list(rule.get("fallback_calibers", [])) if args.fallback_caliber == "auto" else ([] if args.fallback_caliber == "none" else [args.fallback_caliber])
    data_end = args.data_end or args.end
    used = requested
    raw = run_query(args.start, data_end, requested, project_name)
    warnings = []
    if not raw.get("list"):
        for fallback in fallbacks:
            if fallback == requested:
                continue
            candidate = run_query(args.start, data_end, fallback, project_name)
            if candidate.get("list"):
                raw = candidate
                used = fallback
                warnings.append(f"{requested} caliber returned empty; {fallback} result requires project-page cross-check before writing")
                break

    rows = normalize(raw, report_basis)
    result = {
        "project": project_name,
        "project_rule": rule_key,
        "market_label": args.market_label,
        "week_start": args.start,
        "week_end": args.end,
        "data_end": data_end,
        "requested_caliber": requested,
        "used_caliber": used,
        "report_basis": report_basis,
        "group_by": ["media", "os"],
        "warnings": warnings,
        "rows": rows,
        "totals": {
            "Android": total(rows["Android"]),
            "iOS": total(rows["iOS"]),
            "all": total(rows["Android"] + rows["iOS"]),
        },
        "module_height": 13 + len(rows["Android"]) + len(rows["iOS"]),
        "insert_height_with_gap": 22 + len(rows["Android"]) + len(rows["iOS"]),
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
