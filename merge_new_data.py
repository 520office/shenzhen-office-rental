#!/usr/bin/env python3
"""合并 scraped_clean.json 到 projects.json，去重后输出合并结果"""

import json
import re
import os

PROJECTS_FILE = os.path.join(os.path.dirname(__file__), "projects.json")
SCRAPED_FILE = os.path.join(os.path.dirname(__file__), "scraped_clean.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "projects_merged.json")
REPORT_FILE = os.path.join(os.path.dirname(__file__), "merge_report.txt")


def normalize_name(name: str) -> str:
    """归一化名称用于匹配"""
    n = name.strip()
    # 只去掉 "前海！" / "前海!" 这类异常前缀（不含正常"前海XX"命名）
    n = re.sub(r'^(前海[！!])\s*', '', n)
    # 去掉 "(办公)" 后缀
    n = re.sub(r'\s*\(办公\)\s*$', '', n)
    # 统一空格
    n = re.sub(r'\s+', '', n)
    return n


def make_key(record: dict) -> str:
    """生成去重匹配键：归一化名称 + 面积"""
    name = normalize_name(record.get("name", ""))
    size = record.get("size", "").strip()
    return f"{name}|{size}"


def normalize_area(area: str) -> str:
    """统一 area 格式"""
    a = area.strip()
    if not a:
        return a
    # 如果只是 "前海"，改为 "南山-前海"
    if a == "前海":
        return "南山-前海"
    return a


def main():
    """主合并逻辑"""
    with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
        existing = json.load(f)

    with open(SCRAPED_FILE, "r", encoding="utf-8") as f:
        new_data = json.load(f)

    print(f"现有数据: {len(existing)} 条")
    print(f"新采集数据: {len(new_data)} 条")

    # 建立现有数据索引
    existing_index = {}
    for i, rec in enumerate(existing):
        key = make_key(rec)
        if key in existing_index:
            print(f"  ⚠ 现有数据重复: {key} (索引 {existing_index[key]}, {i})")
        existing_index[key] = i

    # 统计
    merged = list(existing)
    added = []
    updated = []
    skipped = []
    unchanged = []

    for rec in new_data:
        key = make_key(rec)
        # 清洗新记录
        rec["name"] = rec["name"].strip()
        # 只去掉 "前海！" / "前海!" 异常前缀
        rec["name"] = re.sub(r'^(前海[！!])\s*', '', rec["name"])
        # 统一 area
        rec["area"] = normalize_area(rec.get("area", ""))

        if key in existing_index:
            idx = existing_index[key]
            old = merged[idx]
            # 如果旧记录没有价格但新记录有 → 更新价格
            old_price = old.get("price", "")
            new_price = rec.get("price", "")
            changed = False

            if not old_price and new_price:
                old["price"] = new_price
                changed = True
            # 如果旧记录没有 area 但新记录有 → 补 area
            if not old.get("area") and rec.get("area"):
                old["area"] = rec["area"]
                changed = True
            # 如果旧记录没有 floor 但新记录有 → 补 floor
            if not old.get("floor") and rec.get("floor"):
                old["floor"] = rec["floor"]
                changed = True

            if changed:
                updated.append({"name": old["name"], "size": old["size"], "new_price": new_price, "old_price": old_price})
            else:
                unchanged.append(key)
        else:
            # 新记录
            added.append(rec)
            merged.append(rec)

    # 写入合并结果
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    # 生成报告
    report = []
    report.append("=" * 50)
    report.append("数据合并报告")
    report.append("=" * 50)
    report.append(f"合并前: {len(existing)} 条")
    report.append(f"新采集: {len(new_data)} 条")
    report.append(f"合并后: {len(merged)} 条")
    report.append("")
    report.append(f"新增: {len(added)} 条")
    for a in added:
        report.append(f"  + {a['name']} | {a['size']} | {a.get('price','无')}")
    report.append("")
    report.append(f"更新价格: {len(updated)} 条")
    for u in updated:
        report.append(f"  ~ {u['name']} | {u['size']} | {u['old_price']} → {u['new_price']}")
    report.append("")
    report.append(f"已存在(无变化): {len(unchanged)} 条")
    report.append(f"跳过: {len(skipped)} 条")
    report.append("")
    report.append("=" * 50)
    report.append("楼盘分布 (合并后):")
    from collections import Counter
    area_counter = Counter(r.get("area", "未知") for r in merged)
    for area, count in area_counter.most_common():
        report.append(f"  {area}: {count}条")

    report_text = "\n".join(report)
    print(report_text)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n⚠ 合并结果已写入: {OUTPUT_FILE}")
    print(f"⚠ 报告已写入: {REPORT_FILE}")
    print(f"\n确认无误后，将 {OUTPUT_FILE} 覆盖 {PROJECTS_FILE} 即可。")


if __name__ == "__main__":
    main()
