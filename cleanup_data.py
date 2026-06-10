#!/usr/bin/env python3
"""清洗 scraped_new.json：修复名称过长、补全价格"""

import json
import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(SCRIPT_DIR, "scraped_new.json")
OUTPUT = os.path.join(SCRIPT_DIR, "scraped_clean.json")

# 楼盘名后缀模式
BUILDING_SUFFIX = r"(?:大厦|大楼|中心|广场|写字楼|商务楼|产业园|科技园|创业园|公寓|花园|城|馆|阁|苑|府|居|庭|座|壹号|壹方城|壹方中心|玖誉|卓越时代|卓越宝中|金融中心|自贸大厦|弘毅大厦|世茂大厦|华润中心|嘉里中心|信利康大厦|桂湾中心|周大福)"


def fix_name(text):
    """从长文本提取纯楼盘名"""
    if not text or len(text) <= 15:
        return text or "未知项目"

    # 去掉多余空格（但保留中文间无空格）
    clean = re.sub(r"\s+", "", text)

    # 如果已经是正常的短名称，直接返回
    if len(clean) <= 20:
        return clean

    # 策略1: 匹配 前海XXX大厦/中心/广场 等
    m = re.search(rf"(前海[^\s，,，。!！、]{2,20}?{BUILDING_SUFFIX})", clean)
    if m:
        return m.group(1)

    # 策略2: 任意 XXX大厦/中心结尾
    m = re.search(rf"([^\s，,，。!！、]{{2,20}}{BUILDING_SUFFIX})", clean)
    if m:
        return m.group(1)

    # 策略3: 取第一个 "、" 或 "。" 或 "面积" 或 "价格" 前的内容
    m = re.match(r"(.+?)[。，,，！!、面积价格]", clean)
    if m:
        short = m.group(1).strip()
        if 3 <= len(short) <= 20:
            return short

    # 策略4: 直接截断
    return clean[:15]


def fix_price_from_name(text):
    """从长文本中提取价格"""
    # "价 格：70元/平"
    m = re.search(r"价\s*格[：:]\s*([\d.]+)\s*元\s*[/每]\s*平", text)
    if m:
        return f"{m.group(1)}元/㎡/月"

    # "价格70元/㎡"
    m = re.search(r"价格[：:]*\s*([\d.]+)\s*元\s*/\s*[㎡平]", text)
    if m:
        return f"{m.group(1)}元/㎡/月"

    # "70元每平"
    m = re.search(r"([\d.]+)\s*元\s*[每/]\s*平", text)
    if m:
        return f"{m.group(1)}元/㎡/月"

    # "50元每平方"
    m = re.search(r"([\d.]+)\s*元\s*每\s*[平㎡平方]", text)
    if m:
        return f"{m.group(1)}元/㎡/月"

    return ""


def main():
    with open(INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"原始: {len(data)} 条")

    fixed_name = 0
    fixed_price = 0

    for p in data:
        orig_name = p["name"]

        # 修复名称
        new_name = fix_name(p["name"])
        if new_name != orig_name:
            print(f"  名称: [{orig_name[:30]}...] → [{new_name}]")
            fixed_name += 1
            # 从原始名称中尝试提取价格
            if not p["price"]:
                extracted = fix_price_from_name(orig_name)
                if extracted:
                    p["price"] = extracted
                    fixed_price += 1
                    print(f"  价格: 从名称中提取 → {extracted}")
            p["name"] = new_name

    # 去重（同名+同面积）
    seen = {}
    deduped = []
    dups = 0
    for p in data:
        key = (p["name"], p["size"])
        if key in seen:
            # 保留信息更全的那条
            existing = seen[key]
            if not existing["price"] and p["price"]:
                existing["price"] = p["price"]
            if not existing["floor"] and p["floor"]:
                existing["floor"] = p["floor"]
            if len(p.get("features", [])) > len(existing.get("features", [])):
                existing["features"] = p["features"]
            dups += 1
        else:
            seen[key] = p
            deduped.append(p)

    data = deduped

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n名称修复: {fixed_name} 条")
    print(f"价格补全: {fixed_price} 条")
    print(f"去重移除: {dups} 条")
    print(f"最终: {len(data)} 条 → {OUTPUT}")

    # 摘要
    print(f"\n{'='*80}")
    print(f"{'#':<4} {'项目名称':<22} {'面积':<8} {'价格':<16}")
    print(f"{'-'*80}")
    for i, p in enumerate(data, 1):
        name = p["name"][:20]
        size = p["size"] or "—"
        price = p["price"] or "—"
        print(f"{i:<4} {name:<22} {size:<8} {price:<16}")
    print(f"{'-'*80}")

    no_price = sum(1 for p in data if not p["price"])
    print(f"  共 {len(data)} 条, 缺价格 {no_price} 条")


if __name__ == "__main__":
    main()
