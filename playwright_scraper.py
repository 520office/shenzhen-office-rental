#!/usr/bin/env python3
"""
安居客 办公室房源批量采集工具 (Playwright版)
============================================
使用真实 Chromium 浏览器绕过反爬检测，解决验证码问题。

用法:
  python playwright_scraper.py
  python playwright_scraper.py --input urls.txt
  python playwright_scraper.py --url https://sz.sydc.anjuke.com/xzl-zu/7118047650/
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
DEFAULT_URL_FILE = os.path.join(os.path.dirname(SCRIPT_DIR), "urls.txt")
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "scraped_new.json")

REQUEST_DELAY_MIN = 3.0
REQUEST_DELAY_MAX = 6.0
PAGE_TIMEOUT = 20000  # ms

AREAS = sorted(
    ["会展新城", "宝安中心", "南山科技园", "碧海湾", "前海", "西乡", "翻身", "新安", "兴东",
     "坪洲", "固戍", "福永", "沙井", "宝安", "南山", "福田", "罗湖", "龙华", "龙岗",
     "盐田", "光明", "坪山", "大鹏"],
    key=len, reverse=True
)


# ============================================================
# HTML 解析函数（复用原有逻辑）
# ============================================================

def strip_html(text):
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_title(html):
    m = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"<h1[^>]*class=['\"]?bus-keytitle['\"]?[^>]*>([\s\S]*?)</h1>", html, re.IGNORECASE)
    if m:
        return strip_html(m.group(1))
    return ""


def guess_name(html, title, text):
    # 策略1: bus-map-title 锚点（最准确）
    m = re.search(r'<a[^>]*class="[^"]*bus-map-title[^"]*"[^>]*>\s*(.+?)\s*</a>', html, re.IGNORECASE)
    if m:
        name = strip_html(m.group(1))
        # 如果内容太长（可能包含描述），只取到第一个句号/逗号前，或截断
        if len(name) > 60:
            name = re.split(r"[。，,，]", name)[0]
        if len(name) >= 3 and "地图" not in name:
            return name[:50]

    # 策略2: 描述中的【楼盘】：
    m = re.search(r"(?:【楼盘】|《1》项目|项目)[：:]\s*(.+?)(?:<br|（|\n|<)", text)
    if m:
        name = m.group(1).strip()
        name = re.sub(r"（.*", "", name)
        if len(name) >= 3:
            return name

    # 策略3: h1 bus-keytitle
    m = re.search(r"<h1[^>]*class=['\"]?bus-keytitle['\"]?[^>]*>([\s\S]*?)</h1>", html)
    if m:
        h1_text = strip_html(m.group(1))
        parts = h1_text.split("丨")
        if len(parts) >= 2:
            second = parts[1]
            m2 = re.search(r".{1,30}?(大厦|大楼|中心|广场|写字楼|商务楼|办公楼|产业园|科技园|创业园|公寓|花园|城|馆|阁|苑|府|居|庭|座|壹方城|壹方中心|玖誉|卓越时代|卓越宝中)", second)
            if m2:
                return m2.group(0)
            first_bang = second.split("！")[0] if "！" in second else second[:20]
            return first_bang[:30]

    # 策略4: 楼盘后缀
    suffix_patterns = [
        r"前海[^，,\s]{2,10}(?:大厦|中心|广场|时代|城|府|馆|阁|座)",
        r"([^\s，,]{2,20}(?:大厦|大楼|中心|广场|写字楼|商务楼|办公楼|产业园|科技园|创业园|公寓|花园|城|馆|阁|苑|府|居|庭|座|壹方城|壹方中心|玖誉))",
    ]
    for pat in suffix_patterns:
        m = re.search(pat, text)
        if m:
            name = m.group(1) if m.lastindex else m.group(0)
            if len(name) >= 3 and name not in ("科技园", "创业园", "写字楼", "办公楼"):
                return name

    # 策略5: title 兜底
    clean = re.sub(r"[【】出租办公多图低价急租房东直租业主一手看海景地铁口]", "", title)
    clean = clean.strip()[:30]
    return clean if len(clean) >= 4 else "未知项目"


def guess_area(html):
    m = re.search(r"<text>\s*(宝安|南山|福田|罗湖|龙华|龙岗|盐田|光明|坪山|大鹏)\s*</text>", html)
    district = m.group(1) if m else ""
    sub_m = re.search(r"<text>\s*·\s*(\S+?)\s*</text>", html)
    sub = sub_m.group(1) if sub_m else ""
    m2 = re.search(r'<div[^>]*class="[^"]*bus-map-name[^"]*"[^>]*>\s*(.+?)\s*</div>', html)
    if m2:
        return strip_html(m2.group(1))
    title = extract_title(html)
    for a in AREAS:
        if a in title:
            return a
    if district:
        return f"{district}-{sub}" if sub else district
    return ""


def guess_location(html):
    m = re.search(r"楼盘地址[：:]\s*([^<]+)", html)
    if m:
        return m.group(1).strip()
    m = re.search(r'<div[^>]*class="[^"]*bus-map-name[^"]*"[^>]*>\s*(.+?)\s*</div>', html)
    if m:
        return strip_html(m.group(1))
    return ""


def guess_size(html):
    text = strip_html(html)
    m = re.search(r"(?:《2》面积|[【\[]面积[】\]])\s*[：:]\s*(\d+)\s*[平㎡mM]", text)
    if m:
        return m.group(1) + "㎡"
    m = re.search(r'<meta[^>]*name="description"[^>]*content="[^"]*面积\s*(\d+)\s*[平米㎡]', html)
    if m:
        return m.group(1) + "㎡"
    m = re.search(r"(\d+)\s*[平㎡]", text)
    if m:
        num = int(m.group(1))
        if 30 < num < 10000:
            return m.group(1) + "㎡"
    title = extract_title(html)
    m = re.search(r"(\d+)\s*[平㎡mM]", title)
    if m:
        num = int(m.group(1))
        if 30 < num < 10000:
            return m.group(1) + "㎡"
    return ""


def guess_price(html):
    text = strip_html(html)
    m = re.search(r'<meta[^>]*name="description"[^>]*content="[^"]*单价\s*([\d.]+)\s*元\s*/\s*㎡\s*/\s*天', html)
    if m:
        daily = float(m.group(1))
        monthly = int(daily * 30)
        return f"{monthly}元/㎡/月"
    m = re.search(r"(?:【单价】|《3》租金|租金)[：:]\s*([\d.]+)\s*元\s*/\s*平", text)
    if m:
        return f"{m.group(1)}元/㎡/月"
    m = re.search(r'<div[^>]*class="[^"]*price[^"]*"[^>]*>\s*([\d.]+)\s*<span[^>]*class="[^"]*unit[^"]*"[^>]*>\s*元\s*/\s*㎡\s*/\s*天', html)
    if m:
        daily = float(m.group(1))
        monthly = int(daily * 30)
        return f"{monthly}元/㎡/月"
    m = re.search(r"([\d.]+)\s*元\s*/\s*[㎡平米]\s*/\s*月", text)
    if m:
        return f"{m.group(1)}元/㎡/月"
    m = re.search(r"([\d.]+)\s*元\s*/\s*平", text)
    if m:
        return f"{m.group(1)}元/㎡/月"
    m = re.search(r"([\d.]+)\s*元\s*/\s*月", text)
    if m:
        return f"{m.group(1)}元/月"
    return ""


def guess_decoration(html):
    text = strip_html(html)
    if "豪华" in text or "豪装" in text:
        return "豪华装修"
    if "精装" in text:
        return "精装修"
    if "简装" in text:
        return "简装"
    if "毛坯" in text:
        return "毛坯"
    return "精装修"


def guess_floor(html):
    text = strip_html(html)
    m = re.search(r"([低中高]区).*?共\s*(\d+)\s*层", text)
    if m:
        return f"{m.group(1)} / 共{m.group(2)}层"
    m = re.search(r"([低中高]区)", text)
    if m:
        return m.group(1)
    m = re.search(r"共\s*(\d+)\s*层", text)
    if m:
        return f"共{m.group(1)}层"
    return ""


def guess_features(html):
    text = strip_html(html)
    kw = {
        "近地铁": "近地铁" in text,
        "地铁口": "地铁口" in text,
        "配套食堂": bool(re.search(r"食堂|餐饮|餐厅", text)),
        "停车位": bool(re.search(r"停车|车位", text)),
        "海景": "海景" in text,
        "可注册": "可注册" in text,
        "红本": "红本" in text,
        "24小时空调": "24小时空调" in text or "独立控制" in text,
        "拎包入驻": "拎包" in text or "随时入住" in text or "随时入驻" in text,
        "配家私": "家私" in text or "家具" in text or "配家私" in text,
        "采光好": "采光" in text,
        "户型方正": "户型方正" in text,
        "5A甲级": "5A" in text or "甲级" in text,
        "中央空调": "中央空调" in text,
        "交通便捷": "交通" in text,
    }
    return [k for k, v in kw.items() if v]


def guess_image(html):
    m = re.search(r'data-background="(https?://pic\d+\.ajkimg\.com/display/hj/[a-f0-9]+/600x450c\.jpg)\?', html)
    if m:
        return m.group(1).replace("600x450c", "800x600c")
    m = re.search(r'data-background="(https?://pic\d+\.ajkimg\.com/display/[^"]+?\.jpg)\?', html)
    if m:
        return m.group(1).replace("600x450c", "800x600c")
    return ""


def parse_page(html, url):
    """解析单个页面"""
    title = extract_title(html)
    text = strip_html(html)

    # 检测验证码
    if "验证" in title or "安全验证" in title or "频繁" in title:
        print(f"  ⚠️ 触发验证码页面！")
        return None

    if not title or len(title) < 5:
        # 再检测一下是不是有内容但title短
        if len(html) < 500:
            print(f"  ⚠️ 页面内容异常（可能被拦截）")
            return None

    name = guess_name(html, title, text)
    area = guess_area(html)
    location = guess_location(html)
    size = guess_size(html)
    price = guess_price(html)
    decoration = guess_decoration(html)
    floor = guess_floor(html)
    features = guess_features(html)
    image = guess_image(html)

    return {
        "name": name,
        "area": area,
        "location": location,
        "size": size,
        "price": price,
        "decoration": decoration,
        "floor": floor,
        "features": features,
        "image": image,
        "date": datetime.date.today().isoformat(),
    }


def clean_url(url):
    """简化URL"""
    url = url.strip()
    if not url:
        return ""
    m = re.match(r"(https?://[^/]+/(?:xzl-zu|cw-zu)/\d+/)", url)
    if m:
        return m.group(1)
    return url


def read_url_file(filepath):
    urls = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                clean = clean_url(line)
                if clean:
                    urls.append(clean)
    # 去重
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


def print_summary(projects):
    print("\n" + "=" * 100)
    print(f"{'#':<4} {'项目名称':<28} {'区域':<14} {'面积':<14} {'价格':<22} {'装修'}")
    print("-" * 100)
    for i, p in enumerate(projects, 1):
        name = p["name"][:26] if p["name"] else "—"
        area = p["area"][:12] if p["area"] else "—"
        size = p["size"][:12] if p["size"] else "—"
        price = p["price"][:20] if p["price"] else "—"
        deco = p["decoration"] if p["decoration"] else "—"
        print(f"{i:<4} {name:<28} {area:<14} {size:<14} {price:<22} {deco}")
    print("-" * 100)
    print(f"  共 {len(projects)} 条房源")
    print("=" * 100)


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="安居客房源批量采集 (Playwright版)")
    parser.add_argument("--input", "-i", help="URL列表文件路径")
    parser.add_argument("--url", "-u", help="单个房源URL")
    parser.add_argument("--urls", help="多个URL，用引号包裹")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT, help="输出JSON文件路径")
    parser.add_argument("--no-delay", action="store_true", help="跳过请求间隔")
    parser.add_argument("--headed", action="store_true", help="显示浏览器窗口（调试用）")
    args = parser.parse_args()

    # 收集URL
    urls = []
    if args.url:
        urls.append(clean_url(args.url))
    if args.urls:
        for u in args.urls.split():
            u = u.strip()
            if u:
                urls.append(clean_url(u))
    if not urls:
        url_file = args.input or DEFAULT_URL_FILE
        if not os.path.exists(url_file):
            print(f"❌ URL文件不存在: {url_file}")
            sys.exit(1)
        urls = read_url_file(url_file)

    if not urls:
        print("❌ 没有找到有效的URL")
        sys.exit(1)

    print(f"\n🔍 准备解析 {len(urls)} 条房源 (Playwright浏览器模式)...")
    print(f"📁 输出文件: {args.output}\n")

    projects = []
    success = 0
    failed = 0

    # 启动 Playwright
    with sync_playwright() as p:
        # 启动浏览器 - 使用常见分辨率，模拟真实用户
        browser = p.chromium.launch(
            headless=not args.headed,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )

        # 创建上下文 - 桌面UA
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )

        # 注入反检测脚本
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
            print(f"[{i}/{len(urls)}] {url}")
            try:
                # 先尝试用新页面访问
                page.goto(url, timeout=PAGE_TIMEOUT, wait_until="domcontentloaded")
                # 额外等待一下让JS执行
                page.wait_for_timeout(2000)

                html = page.content()

                # 检测是否验证码
                if "安全验证" in html or "请输入验证码" in html:
                    print(f"  ⚠️ 触发安全验证！等待中...")
                    page.wait_for_timeout(5000)
                    html = page.content()

                if "安全验证" in html or "请输入验证码" in html:
                    print(f"  ❌ 验证码无法自动绕过，跳过此条")
                    failed += 1
                else:
                    proj = parse_page(html, url)
                    if proj:
                        projects.append(proj)
                        success += 1
                        print(f"  ✅ {proj['name']} | {proj['area']} | {proj['size']} | {proj['price']}")
                    else:
                        failed += 1
                        title = extract_title(html)
                        print(f"  ⚠️ 未能解析 (title: {title[:50] if title else '无'})")

            except Exception as e:
                failed += 1
                print(f"  ❌ 错误: {e}")

            # 随机延时
            if i < len(urls) and not args.no_delay:
                delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
                print(f"  ⏳ 等待 {delay:.1f}秒...")
                time.sleep(delay)

            # 每10条刷新一下上下文
            if i % 10 == 0:
                print(f"\n  🔄 刷新浏览器上下文...")
                page.close()
                context.close()
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0.0.0 Safari/537.36"
                    ),
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

    # 输出
    print(f"\n📊 完成: {success} 成功, {failed} 失败")
    if projects:
        print_summary(projects)
        save_json(projects, args.output)
        print(f"\n💡 下一步: 将 {args.output} 发给我，我来合并到 projects.json 并推送")


if __name__ == "__main__":
    main()
