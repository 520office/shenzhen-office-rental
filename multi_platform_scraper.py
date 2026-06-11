#!/usr/bin/env python3
"""
多平台办公室房源批量采集工具 (Playwright版)
支持: 房天下(fang.com) / 58同城(58.com) / 贝壳(ke.com) / 安居客(anjuke.com)

用法:
  python multi_platform_scraper.py
  python multi_platform_scraper.py --input urls.txt
  python multi_platform_scraper.py --url https://sz.office.fang.com/zu/3_247674724.html
"""

import argparse
import datetime
import json
import random
import re
import sys
import os
import time
from playwright.sync_api import sync_playwright

# Windows 编码修复
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

# ============================================================
# 配置
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_URL_FILE = os.path.join(SCRIPT_DIR, "urls.txt")
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "scraped_new.json")

REQUEST_DELAY_MIN = 3.0
REQUEST_DELAY_MAX = 7.0
PAGE_TIMEOUT = 25000  # ms

AREAS = sorted(
    ["会展新城", "宝安中心", "南山科技园", "碧海湾", "前海", "西乡", "翻身", "新安", "兴东",
     "坪洲", "固戍", "福永", "沙井", "宝安", "南山", "福田", "罗湖", "龙华", "龙岗",
     "盐田", "光明", "坪山", "大鹏"],
    key=len, reverse=True
)

BUILDING_SUFFIX = "(?:大厦|大楼|中心|广场|写字楼|商务楼|办公楼|产业园|科技园|创业园|公寓|花园|城|馆|阁|苑|府|居|庭|座|岛|谷|园|壹方城|壹方中心|玖誉|卓越时代|卓越宝中|金融中心|嘉里中心|世茂|弘毅|颐都|华润|香缤|企业公馆|周大福|鸿荣源|壹号|金环宇|梧桐岛|泰华|星通|恒明珠|海纳|前海人寿)"


# ============================================================
# 通用工具
# ============================================================

def strip_html(text):
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def detect_platform(url):
    """检测URL属于哪个平台"""
    if "fang.com" in url or "office.fang" in url:
        return "fang"
    if "58.com" in url:
        return "58"
    if "ke.com" in url or "beike" in url:
        return "beike"
    if "anjuke.com" in url:
        return "anjuke"
    return "unknown"


def clean_url(url):
    """简化URL"""
    url = url.strip()
    if not url:
        return ""
    return url


def read_url_file(filepath):
    urls = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                u = clean_url(line)
                if u:
                    urls.append(u)
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def save_json(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已保存 {len(data)} 条房源到: {filepath}")


def parse_area_from_text(text, title=""):
    """从文本中提取区域"""
    # Try to match known area names
    for a in AREAS:
        if a in text or a in title:
            return a
    # Try district-sub pattern
    m = re.search(r"(南山|宝安|福田|罗湖|龙华|龙岗|盐田|光明|坪山|大鹏)[-·](\S+)", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.search(r"(南山|宝安|福田|罗湖|龙华|龙岗)\s*(\S+?区)", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return ""


def clean_name(name):
    """清理楼盘名称"""
    name = re.sub(r'写字楼$', '', name)
    name = re.sub(r'【\d+图】', '', name)
    name = re.sub(r'[，,].*$', '', name)
    name = name.strip()
    return name

def parse_name_from_text(text, title=""):
    """从文本中提取楼盘名称"""
    all_text = title + " " + text
    
    # Strategy 1: 前海 + suffix
    m = re.search(r"前海\s*" + BUILDING_SUFFIX, all_text)
    if m:
        return clean_name(m.group(0).replace(" ", ""))
    
    # Strategy 2: general suffix (匹配深圳区域+楼盘名)
    m = re.search(r"(?:深圳\w+区\w*|深圳\w+)?([^\s，,]{2,20}" + BUILDING_SUFFIX + ")", all_text)
    if m:
        name = m.group(1)
        if name not in ("宝安中心", "南山科技园", "会展新城", "写字楼出租") and len(name) >= 3:
            return clean_name(name)
    
    # Strategy 3: 58同城 - "深圳XX区XX+地名"
    m = re.search(r"深圳\w+区\w*(\w{2,15}(?:岛|谷|园|大厦|中心|广场))", all_text)
    if m:
        return m.group(1)
    
    # Strategy 4: from "深圳XX区XX" pattern
    m = re.search(r"深圳\w+区(\w{2,15})", all_text)
    if m:
        return m.group(1)
    
    return ""


def parse_size_from_text(text, title=""):
    """提取面积"""
    all_text = title + " " + text
    # 面积XXXm² or XXX平
    m = re.search(r"面积\s*(\d+)\s*[mM㎡²平]", all_text)
    if m:
        return m.group(1) + "㎡"
    # Title中的XX平
    m = re.search(r"(\d+)\s*[平㎡]", all_text)
    if m:
        num = int(m.group(1))
        if 30 < num < 20000:
            return m.group(1) + "㎡"
    return ""


def parse_price_from_text(text, html="", title=""):
    """提取价格，统一转换为元/㎡/月"""
    all_text = title + " " + text
    
    # 1. 元/㎡/月 directly
    m = re.search(r"([\d.]+)\s*元\s*/\s*[㎡平米²m]\s*/\s*月", all_text)
    if m:
        return f"{m.group(1)}元/㎡/月"
    
    # 2. 元/㎡/天 → ×30
    m = re.search(r"([\d.]+)\s*元\s*/\s*[㎡平米²m]\s*/\s*天", all_text)
    if m:
        daily = float(m.group(1))
        monthly = round(daily * 30)
        return f"{monthly}元/㎡/月"
    
    # 3. X万元/月 (total) → need to divide by size
    m = re.search(r"([\d.]+)\s*万\s*元?\s*/\s*月", all_text)
    if m:
        total_wan = float(m.group(1))
        total_yuan = total_wan * 10000
        # Try to get size
        sm = re.search(r"面积\s*(\d+)\s*[mM㎡²平]", all_text)
        if not sm:
            sm = re.search(r"(\d+)\s*[平㎡]", all_text)
        if sm:
            size_num = float(sm.group(1))
            per_sqm = round(total_yuan / size_num)
            return f"{per_sqm}元/㎡/月"
        return f"{int(total_yuan)}元/月"
    
    # 4. X元/月 (total)
    m = re.search(r"([\d,.]+)\s*元\s*/\s*月", all_text)
    if m:
        total = float(m.group(1).replace(",", ""))
        sm = re.search(r"面积\s*(\d+)\s*[mM㎡²平]", all_text)
        if not sm:
            sm = re.search(r"(\d+)\s*[平㎡]", all_text)
        if sm and (size_num := float(sm.group(1))) > 0:
            per_sqm = round(total / size_num)
            return f"{per_sqm}元/㎡/月"
        return f"{int(total)}元/月"
    
    return ""


def parse_decoration_from_text(text, title=""):
    all_text = title + " " + text
    if "豪华" in all_text or "豪装" in all_text:
        return "豪华装修"
    if "精装" in all_text:
        return "精装修"
    if "简装" in all_text:
        return "简装"
    if "毛坯" in all_text:
        return "毛坯"
    return "精装修"


def parse_floor_from_text(text, title=""):
    all_text = title + " " + text
    m = re.search(r"([低中高]楼层?)", all_text)
    if m:
        return m.group(1)
    m = re.search(r"共\s*(\d+)\s*层", all_text)
    if m:
        return f"共{m.group(1)}层"
    return ""


def parse_features_from_text(text, title=""):
    all_text = title + " " + text
    kw = {
        "近地铁": "近地铁" in all_text or "地铁口" in all_text or "地铁" in all_text,
        "配套食堂": bool(re.search(r"食堂|餐饮|餐厅", all_text)),
        "停车位": bool(re.search(r"停车|车位", all_text)),
        "海景": "海景" in all_text,
        "可注册": "可注册" in all_text,
        "红本": "红本" in all_text,
        "24小时空调": "24小时空调" in all_text or "独立控制" in all_text,
        "拎包入驻": "拎包" in all_text or "随时入住" in all_text or "随时入驻" in all_text,
        "配家私": "家私" in all_text or "家具" in all_text or "配家私" in all_text,
        "采光好": "采光" in all_text,
        "户型方正": "户型方正" in all_text,
        "5A甲级": "5A" in all_text or "甲级" in all_text,
        "中央空调": "中央空调" in all_text,
        "交通便捷": "交通" in all_text,
        "露台": "露台" in all_text,
    }
    return [k for k, v in kw.items() if v]


# ============================================================
# 平台专项解析
# ============================================================

def parse_fang(title, text, html, url):
    """解析房天下页面"""
    # Title format: "XX写字楼出租·办公室租赁宝安中心 XX 100-3000平出租-深圳写字楼_房天下"
    name = parse_name_from_text(text, title)
    area = parse_area_from_text(text, title)
    size = parse_size_from_text(text, title)
    
    # Fang specific: look for price in various places
    # Check meta description
    meta_desc = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html)
    if meta_desc:
        desc_text = meta_desc.group(1)
        price = parse_price_from_text(desc_text, title=title)
        if not price:
            price = parse_price_from_text(text, title)
    else:
        price = parse_price_from_text(text, title)
    
    # Try to find location in text (filter out meaningless values)
    location = ""
    loc_m = re.search(r"([\u4e00-\u9fff]{2,10}(?:区|路|街道|大道)[\u4e00-\u9fff\d]{0,15}(?:号)?)", text)
    if loc_m:
        loc = loc_m.group(1)
        if loc not in ("找小区", "核心区域", "商业区", "附近"):
            location = loc
    
    return {
        "name": name or "未知项目",
        "area": area,
        "location": location,
        "size": size,
        "price": price,
        "decoration": parse_decoration_from_text(text, title),
        "floor": parse_floor_from_text(text, title),
        "features": parse_features_from_text(text, title),
        "image": "",
        "date": datetime.date.today().isoformat(),
    }


def parse_58(title, text, html, url):
    """解析58同城页面"""
    name = parse_name_from_text(text, title)
    area = parse_area_from_text(text, title)
    size = parse_size_from_text(text, title)
    price = parse_price_from_text(text, html, title)
    
    # 58 specific: look for district in title
    m = re.search(r"深圳(\w+)\w+", title)
    if m and not area:
        dist = m.group(1)
        if len(dist) >= 2:
            area = dist
    
    # Location
    location = ""
    loc_m = re.search(r"楼盘地址[：:]\s*([^<\n]{2,50})", text)
    if loc_m:
        loc = loc_m.group(1).strip()
        if loc not in ("找小区", "核心区域", "暂无", ""):
            location = loc
    
    # Image
    image = ""
    img_m = re.search(r'data-src="(https?://[^"]+\.(?:jpg|png|jpeg))"', html)
    if img_m:
        image = img_m.group(1)
    
    return {
        "name": name or "未知项目",
        "area": area,
        "location": location,
        "size": size,
        "price": price,
        "decoration": parse_decoration_from_text(text, title),
        "floor": parse_floor_from_text(text, title),
        "features": parse_features_from_text(text, title),
        "image": image,
        "date": datetime.date.today().isoformat(),
    }


def parse_beike(title, text, html, url):
    """解析贝壳页面 - Title包含结构化数据"""
    # Title: 【金环宇862平中楼层近地铁精装朝东/面积862m²/价格6.04万元/月/精装/】-深圳贝壳商业地产
    # Or: 【信义领御研发中心（稻兴环球科创中心）2004.中楼层近地铁/面积2004m²/...】
    
    # ===== Extract name from start =====
    # Fix: handle both "XXX平" and "XXX." delimiters after area number
    name = ""
    m = re.search(r'【(.+?)\d+[平.]', title)
    if m:
        name = m.group(1).strip()
        # Remove floor/direction suffixes
        name = re.sub(r'(中|高|低)楼层.*$', '', name)
        name = re.sub(r'近地铁.*$', '', name)
        name = re.sub(r'精装.*$', '', name)
        name = re.sub(r'朝[东西南北].*$', '', name)
        name = name.strip()
    
    if not name:
        name = parse_name_from_text(text, title)
    
    # ===== Size from title =====
    # Fix: support decimal sizes like "面积2004.24m²"
    size = ""
    m = re.search(r'面积\s*([\d.]+)\s*[mM㎡²]', title)
    if m:
        size = m.group(1).rstrip('.') + "㎡"
    if not size:
        # Second try: "XXX平" - but prioritize larger numbers (avoid catching decimal parts)
        m = re.search(r'(?<!\d)(\d+)\s*平', title)
        if m:
            size = m.group(1) + "㎡"
    
    # ===== Price from title =====
    price = ""
    m = re.search(r'价格\s*([\d.]+)\s*万?\s*元?\s*/\s*月', title)
    if m:
        total = float(m.group(1)) * 10000  # 万元 → 元
        sm = re.search(r'面积\s*(\d+)', title)
        if sm:
            size_num = float(sm.group(1))
            per_sqm = round(total / size_num)
            price = f"{per_sqm}元/㎡/月"
        else:
            price = f"{int(total)}元/月"
    
    if not price:
        price = parse_price_from_text(text, html, title)
    
    # ===== Decoration from title =====
    decoration = parse_decoration_from_text(text, title)
    if "精装" in title:
        decoration = "精装修"
    
    # ===== Area: extract from breadcrumb or dedicated location element =====
    area = ""
    # Try beike breadcrumb: 深圳 > 宝安 > 新安
    m = re.search(r'深圳\s*[>＞]\s*(\S+?)\s*[>＞]\s*(\S+?)\s*[>＞]', text)
    if m:
        district = m.group(1).strip()
        sub = m.group(2).strip()
        # Clean sub-area (remove numbers, extra chars)
        sub = re.sub(r'[\d\s/【】]', '', sub)
        if sub in AREAS:
            area = sub
    # Try HTML breadcrumb links
    if not area:
        crumbs = re.findall(r'(?:breadcrumb|crumbs|crumbs-item)[^>]*>([^<]+)<', html)
        for crumb in reversed(crumbs):
            crumb = crumb.strip()
            if crumb in AREAS and crumb not in ('深圳', '宝安', '南山'):
                area = crumb
                break
    # Try text in specific "location" pattern near "新安" or similar
    if not area:
        m = re.search(r'(新安|西乡|福永|沙井|翻身|兴东|坪洲|固戍|碧海湾)', text)
        if m:
            area = m.group(1)
    # Fallback to general parsing (but reverse-prioritize sub-areas)
    if not area:
        area = parse_area_from_text(text, title)
    
    # ===== Floor from title =====
    floor = ""
    m = re.search(r'([低中高]楼层)', title)
    if m:
        floor = m.group(1)
    
    # ===== Location: derive from area or extract from HTML =====
    location = ""
    # Try breadcrumb in HTML for full "district-sub" format
    crumbs = re.findall(r'(?:breadcrumb|crumbs|crumbs-item)[^>]*>([^<]+)<', html)
    if len(crumbs) >= 3:
        # Filter for meaningful crumbs
        meaningful = [c.strip() for c in crumbs if c.strip() and len(c.strip()) <= 8 and '深圳' not in c and '首页' not in c]
        if len(meaningful) >= 2:
            location = '-'.join(meaningful[-2:])
    # If area is a sub-area, derive location from district
    if not location and area in ('新安', '西乡', '福永', '沙井', '翻身', '兴东', '坪洲', '固戍', '碧海湾'):
        location = f"宝安-{area}"
    if not location and area:
        location = area
    # Last resort: extract address from HTML
    if not location:
        loc_m = re.search(r'class="[^"]*address[^"]*"[^>]*>([^<]+)', html)
        if loc_m:
            loc = loc_m.group(1).strip()
            if loc and len(loc) >= 4 and '写字楼' not in loc:
                location = loc
    
    return {
        "name": name or "未知项目",
        "area": area,
        "location": location,
        "size": size,
        "price": price,
        "decoration": decoration,
        "floor": floor,
        "features": parse_features_from_text(text, title),
        "image": "",
        "date": datetime.date.today().isoformat(),
    }


def parse_anjuke(html, url):
    """解析安居客页面（复用旧逻辑）"""
    title = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
    title = title.group(1).strip() if title else ""
    text = strip_html(html)
    
    if "验证" in title or "安全验证" in title:
        return None
    
    from playwright_scraper import guess_name, guess_area, guess_size, guess_price, guess_decoration, guess_floor, guess_features, guess_image
    
    return {
        "name": guess_name(html, title, text),
        "area": guess_area(html),
        "location": "",
        "size": guess_size(html),
        "price": guess_price(html),
        "decoration": guess_decoration(html),
        "floor": guess_floor(html),
        "features": guess_features(html),
        "image": guess_image(html),
        "date": datetime.date.today().isoformat(),
    }


# ============================================================
# 统一采集入口
# ============================================================

def scrape_page(page, url, platform):
    """采集单个页面，根据平台类型分发"""
    try:
        page.goto(url, timeout=PAGE_TIMEOUT, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        html = page.content()
        title = page.title()
        text = strip_html(html)
        
        # 检测验证码
        if "验证" in title or "安全验证" in title or "频繁" in title:
            print(f"  ⚠️ 触发验证码!")
            return None
        
        if platform == "fang":
            result = parse_fang(title, text, html, url)
        elif platform == "58":
            result = parse_58(title, text, html, url)
        elif platform == "beike":
            result = parse_beike(title, text, html, url)
        elif platform == "anjuke":
            result = parse_anjuke(html, url)
        else:
            # Generic fallback
            result = {
                "name": parse_name_from_text(text, title),
                "area": parse_area_from_text(text, title),
                "location": "",
                "size": parse_size_from_text(text, title),
                "price": parse_price_from_text(text, html, title),
                "decoration": parse_decoration_from_text(text, title),
                "floor": parse_floor_from_text(text, title),
                "features": parse_features_from_text(text, title),
                "image": "",
                "date": datetime.date.today().isoformat(),
            }
        
        if result:
            # Cleanup
            if result.get("name"):
                result["name"] = clean_name(result["name"])
            if result.get("location") in ("找小区", "核心区域", "暂无", "商业区"):
                result["location"] = ""
            return result
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return None


def print_summary(projects):
    print("\n" + "=" * 100)
    print(f"{'#':<4} {'项目名称':<25} {'区域':<14} {'面积':<12} {'价格':<22} {'装修'}")
    print("-" * 100)
    for i, p in enumerate(projects, 1):
        name = (p.get("name") or "—")[:23]
        area = (p.get("area") or "—")[:12]
        size = (p.get("size") or "—")[:10]
        price = (p.get("price") or "—")[:20]
        deco = (p.get("decoration") or "—")
        print(f"{i:<4} {name:<25} {area:<14} {size:<12} {price:<22} {deco}")
    print("-" * 100)
    print(f"  共 {len(projects)} 条房源")
    print("=" * 100)


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="多平台办公室房源批量采集 (Playwright版)")
    parser.add_argument("--input", "-i", help="URL列表文件路径")
    parser.add_argument("--url", "-u", help="单个房源URL")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT, help="输出JSON文件路径")
    parser.add_argument("--no-delay", action="store_true", help="跳过请求间隔")
    parser.add_argument("--headed", action="store_true", help="显示浏览器窗口（调试用）")
    args = parser.parse_args()

    # 收集URL
    urls = []
    if args.url:
        urls.append(clean_url(args.url))
    if not urls:
        url_file = args.input or DEFAULT_URL_FILE
        if not os.path.exists(url_file):
            print(f"❌ URL文件不存在: {url_file}")
            sys.exit(1)
        urls = read_url_file(url_file)

    if not urls:
        print("❌ 没有找到有效的URL")
        sys.exit(1)

    # 统计各平台URL数量
    platforms = {}
    for u in urls:
        p = detect_platform(u)
        platforms[p] = platforms.get(p, 0) + 1
    
    print(f"\n🔍 准备解析 {len(urls)} 条房源 (Playwright浏览器模式)")
    print(f"📊 平台分布: {platforms}")
    print(f"📁 输出文件: {args.output}\n")

    projects = []
    success = 0
    failed = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not args.headed,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )
        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """)

        for i, url in enumerate(urls, 1):
            plat = detect_platform(url)
            plat_label = {"fang": "🏠房天下", "58": "📋58同城", "beike": "🐚贝壳", "anjuke": "🏢安居客"}.get(plat, "❓")
            print(f"[{i}/{len(urls)}] {plat_label} {url[:80]}...")
            
            result = scrape_page(page, url, plat)
            if result:
                projects.append(result)
                success += 1
                print(f"  ✅ {result['name'][:25]} | {result.get('area','')[:12]} | {result.get('size','')} | {result.get('price','')}")
            else:
                failed += 1
                print(f"  ❌ 采集失败")

            if i < len(urls) and not args.no_delay:
                delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
                print(f"  ⏳ 等待 {delay:.1f}秒...")
                time.sleep(delay)

            # 每15条刷新上下文
            if i % 15 == 0 and i < len(urls):
                print(f"\n  🔄 刷新浏览器上下文...")
                page.close()
                context.close()
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="zh-CN",
                )
                page = context.new_page()
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                """)

        browser.close()

    print(f"\n📊 完成: {success} 成功, {failed} 失败")
    if projects:
        print_summary(projects)
        save_json(projects, args.output)
        print(f"\n💡 下一步: 将 {args.output} 发给我，我来合并到 projects.json 并推送")


if __name__ == "__main__":
    main()
