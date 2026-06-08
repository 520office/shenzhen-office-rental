#!/usr/bin/env python3
"""
58同城/安居客 深圳办公室出租信息采集脚本
==============================================
采集 58同城 深圳各区域办公室出租信息，输出JSON格式，
可直接导入 admin.html 管理后台的"导入JSON"功能。

使用方法:
    python scraper_58.py                    # 采集所有区域
    python scraper_58.py --area 南山科技园    # 采集指定区域
    python scraper_58.py --pages 3           # 采集3页
    python scraper_58.py --output mydata.json

注意事项:
    1. 采集间隔2秒，避免被反爬
    2. 仅供个人学习使用，大量采集请遵守网站规则
    3. 58同城页面结构可能变化，如采集失败请反馈
"""

import argparse
import json
import re
import time
import sys
import os
import urllib.request
import urllib.error
from urllib.parse import quote

# 修复 Windows Git Bash 的编码问题
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ============================================================
# 区域配置：区域名 -> 58同城搜索关键词
# ============================================================
AREA_CONFIG = {
    "南山科技园": "南山科技园 办公室 出租",
    "前海": "前海 写字楼 出租",
    "宝安中心": "宝安中心 办公室 出租",
    "西乡": "西乡 写字楼 出租",
    "翻身": "翻身 写字楼 出租",
    "新安": "新安 办公室 出租",
    "兴东": "兴东 写字楼 出租",
    "坪洲": "坪洲 办公室 出租",
    "碧海湾": "碧海湾 写字楼 出租",
    "固戍": "固戍 办公室 出租",
    "福永": "福永 写字楼 出租",
    "沙井": "沙井 办公室 出租",
    "会展新城": "会展新城 写字楼 出租",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 58同城办公室出租搜索URL模板
BASE_URL = "https://sz.58.com/zhichang/zhaozu/pn{page}/?key={keyword}"

# 安居客（同样是58系，更稳定）
ANJUKE_URL = "https://shenzhen.anjuke.com/office/rent/{area}/p{page}/"


def fetch_html(url, retries=3):
    """获取网页HTML"""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
                return content
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code}: {url}")
            if e.code == 403:
                print("  提示: 58同城可能触发了反爬，请稍后再试或减少采集频率")
            time.sleep(3)
        except Exception as e:
            print(f"  请求异常: {e}")
            time.sleep(2)
    return None


def parse_58_listing(html):
    """从58同城列表页解析房源数据"""
    results = []

    # 匹配列表项
    house_pattern = re.compile(
        r'<div class="house-list-wrap">.*?</div>\s*</li>',
        re.DOTALL
    )

    # 或 58 新版的卡片结构
    card_pattern = re.compile(
        r'<li.*?class="house-cell.*?">(.*?)</li>',
        re.DOTALL
    )

    cards = card_pattern.findall(html)
    if not cards:
        # 尝试新版布局
        cards = re.findall(r'<div class="list-info">(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)

    for card in cards[:20]:  # 最多取20条
        try:
            # 标题
            title_match = re.search(r'<a.*?class="strongbox".*?>(.*?)</a>', card, re.DOTALL)
            if not title_match:
                title_match = re.search(r'<h2.*?>(.*?)</h2>', card, re.DOTALL)
            title = re.sub(r'<.*?>', '', title_match.group(1)).strip() if title_match else "未知"

            # 地址/位置
            addr_match = re.search(r'<p class="infor">.*?<span>(.*?)</span>', card, re.DOTALL)
            location = addr_match.group(1).strip() if addr_match else ""

            # 面积
            size_match = re.search(r'(\d+[-~]\d+)\s*㎡|(\d+[-~]\d+)\s*平米|(\d+)\s*㎡', card)
            if size_match:
                size = next(s for s in size_match.groups() if s) + "㎡" if "㎡" not in (size_match.group(0) or "") else size_match.group(0).strip()
            else:
                size = "面积详询"

            # 价格
            price_match = re.search(r'<b class="price">(.*?)</b>', card, re.DOTALL)
            if not price_match:
                price_match = re.search(r'<span class="price">.*?<b>(.*?)</b>', card, re.DOTALL)
            if not price_match:
                price_match = re.search(r'(\d+[\d.]*)\s*元/㎡', card)
            price = price_match.group(1).strip() if price_match else "价格面议"
            if price and "元" not in price:
                price = price + "元/㎡/月"

            # 标签
            tags = re.findall(r'<i class="spec">(.*?)</i>', card)
            if not tags:
                tags = re.findall(r'<span class="spec">(.*?)</span>', card)

            results.append({
                "name": title,
                "area": "",  # 需要从标题或地址中提取
                "location": location or "深圳市",
                "size": size,
                "price": price,
                "decoration": "精装修",
                "floor": "",
                "features": tags[:4] if tags else ["写字楼出租"],
                "image": "",
            })
        except Exception as e:
            continue

    return results


def parse_anjuke_listing(html):
    """从安居客列表页解析房源数据"""
    results = []

    # 安居客的办公室列表项
    pattern = re.compile(
        r'<div class="property-content">(.*?)</div>\s*</div>\s*</div>\s*<div class="property-extra">',
        re.DOTALL
    )

    items = pattern.findall(html)

    for item in items[:20]:
        try:
            # 标题
            title_match = re.search(r'<h3.*?><a.*?>(.*?)</a>', item, re.DOTALL)
            title = re.sub(r'<.*?>', '', title_match.group(1)).strip() if title_match else "未知"

            # 地址
            addr_match = re.search(r'<span class="comm-address".*?>(.*?)</span>', item, re.DOTALL)
            location = re.sub(r'<.*?>', '', addr_match.group(1)).strip() if addr_match else "深圳市"

            # 面积
            size_match = re.search(r'(\d+[-~]\d+)㎡|(\d+)\s*㎡', item)
            size = (size_match.group(1) or size_match.group(2)) + "㎡" if size_match else "面积详询"

            # 价格
            price_match = re.search(r'(\d+[\d.]*)\s*元/㎡/月', item)
            price = price_match.group(1) + "元/㎡/月" if price_match else "价格面议"

            results.append({
                "name": title,
                "area": "",
                "location": location,
                "size": size,
                "price": price,
                "decoration": "精装修",
                "floor": "",
                "features": ["写字楼出租"],
                "image": "",
            })
        except Exception:
            continue

    return results


def guess_area(title, location):
    """根据标题和地址猜测所属区域"""
    areas = list(AREA_CONFIG.keys())
    text = title + location
    # 按区域名长度降序匹配，优先匹配长名称（如"宝安中心"优先于"宝安"）
    areas_sorted = sorted(areas, key=len, reverse=True)
    for area in areas_sorted:
        if area in text:
            return area
    # 模糊匹配
    for area in areas_sorted:
        if area[:2] in text:
            return area
    return "宝安中心"


def scrape_58_area(area_name, keyword, max_pages=2):
    """采集58同城指定区域的数据"""
    all_results = []
    print(f"\n📍 正在采集 [{area_name}] ...")

    for page in range(1, max_pages + 1):
        url = BASE_URL.format(page=page, keyword=quote(keyword))
        print(f"  第{page}页: {url}")

        html = fetch_html(url)
        if html is None:
            print("  ⚠️ 采集失败，跳过该页")
            continue

        results = parse_58_listing(html)
        if not results:
            # 尝试安居客
            # 安居客区域映射
            anjuke_area_map = {
                "南山科技园": "nanshan",
                "前海": "qianhai",
                "宝安中心": "baoan",
                "西乡": "xixiang",
            }
            anjuke_area = anjuke_area_map.get(area_name, "baoan")
            anjuke_url = ANJUKE_URL.format(area=anjuke_area, page=page)
            print(f"  尝试安居客: {anjuke_url}")
            html2 = fetch_html(anjuke_url)
            if html2:
                results = parse_anjuke_listing(html2)

        for r in results:
            r["area"] = guess_area(r["name"], r["location"])
            if not r["area"] or r["area"] == "宝安中心":
                r["area"] = area_name

        all_results.extend(results)
        print(f"  ✅ 采集到 {len(results)} 条")
        time.sleep(2)  # 礼貌间隔

    return all_results


def deduplicate(results):
    """按名称去重"""
    seen = set()
    unique = []
    for r in results:
        key = r["name"][:10]
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def main():
    parser = argparse.ArgumentParser(description="58同城深圳办公室出租信息采集")
    parser.add_argument("--area", type=str, default=None, help="指定区域名称，不指定则采集全部")
    parser.add_argument("--pages", type=int, default=2, help="每个区域采集页数 (默认2)")
    parser.add_argument("--output", type=str, default=None, help="输出JSON文件路径")
    parser.add_argument("--list-areas", action="store_true", help="列出所有支持的区域")
    args = parser.parse_args()

    if args.list_areas:
        print("支持的区域:")
        for k in AREA_CONFIG:
            print(f"  - {k}")
        return

    # 确定采集范围
    if args.area:
        if args.area not in AREA_CONFIG:
            print(f"❌ 未知区域: {args.area}")
            print(f"可用区域: {', '.join(AREA_CONFIG.keys())}")
            sys.exit(1)
        areas_to_scrape = {args.area: AREA_CONFIG[args.area]}
    else:
        areas_to_scrape = AREA_CONFIG

    # 采集
    all_results = []
    for area_name, keyword in areas_to_scrape.items():
        results = scrape_58_area(area_name, keyword, args.pages)
        all_results.extend(results)

    # 去重
    all_results = deduplicate(all_results)

    # 添加id
    for i, r in enumerate(all_results):
        r["id"] = i + 1

    # 输出
    output = {
        "source": "58同城/安居客 自动采集",
        "total": len(all_results),
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data": all_results,
    }

    json_str = json.dumps(all_results, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"\n📦 已保存到: {args.output}")

    print(f"\n📊 采集完成: 共 {len(all_results)} 条房源")
    print(f"\n{'='*60}")
    print("使用方法:")
    print("1. 打开 admin.html 管理后台")
    print("2. 点击「📥 导入JSON」")
    print("3. 粘贴以下JSON数据")
    print(f"{'='*60}\n")
    print(json_str[:500] + ("..." if len(json_str) > 500 else ""))


if __name__ == "__main__":
    main()
