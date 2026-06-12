"""
安居客 (Anjuke) 办公室房源采集器
===================================
需要用户提供已登录安居客的Cookie才能使用。
Cookie 获取方式：浏览器登录 anjuke.com → F12 → Console → document.cookie
"""

import asyncio
import json
import re
import datetime
import random
import sys
from playwright.async_api import async_playwright


# === 采集配置 ===
CONFIG = {
    "cookie_file": "anjuke_cookies.txt",   # Cookie 文件路径
    "delay_min": 8,                         # 每条URL最小延迟(秒)
    "delay_max": 15,                        # 每条URL最大延迟(秒)
    "timeout": 30000,                       # 页面加载超时(ms)
    # 安居客深圳办公室区域URL列表页（可从这里获取URL列表）
    "list_urls": {
        "宝安": "https://sz.sydc.anjuke.com/xzl-zu/baoan/",
        "南山": "https://sz.sydc.anjuke.com/xzl-zu/nanshan/",
        "福田": "https://sz.sydc.anjuke.com/xzl-zu/futian/",
        "罗湖": "https://sz.sydc.anjuke.com/xzl-zu/luohu/",
    },
}


def load_cookies(filename):
    """从文件或环境变量加载 Cookie"""
    # 先尝试从文件加载
    try:
        with open(filename, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except FileNotFoundError:
        # 回退到硬编码（仅开发测试用）
        text = """sessid=D31699AA-7F83-0625-3F13-37E781A0E848;  aQQ_ajkguid=9A23F1A6-E411-81AA-3CA8-6C68674344E4;  id58=d1gVmWgjWAFqV3czCZDCAg==;  58tj_uuid=ca963804-62b1-4606-81c7-f946699f02ca;  _ga=GA1.2.1751302714.1747146756;  xxzlclientid=11857e11-7902-4dda-84cf-1747146758533;  xxzlxxid=pfmxmer1EOB4MBCWlgDuYYNiYf+TQeV3SvaLTQ5dw1/mFbCG9+Cana0aSK7BTYCgUlQZ;  seo_source_type=1;  new_uv=10;  als=0"""

    cookies = []
    for item in text.split(";"):
        item = item.strip()
        if "=" in item:
            name, value = item.split("=", 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".anjuke.com",
                "path": "/",
            })
    return cookies


def parse_anjuke(html):
    """
    从安居客房源页面HTML中提取数据。
    
    页面结构:
    - 标题: <title>【多图】{商圈} {描述} {面积}平...-深圳58安居客</title>
    - 详情: <div class="item"><span class="title">X</span>：<span class="value">Y</span></div>
    - 图片: https://pic1.ajkimg.com/display/hj/{hash}/1600x1200.jpg
    """
    result = {
        "name": "",
        "area": "",
        "location": "",
        "size": "",
        "price": "",
        "decoration": "",
        "floor": "",
        "features": [],
        "image": "",
        "date": datetime.date.today().isoformat(),
    }

    # 1. 提取详情项
    items = re.findall(
        r'<div class="item"><span class="title">([^<]+)</span>\s*[：:]\s*<span class="value">([^<]+)</span>',
        html,
    )
    item_dict = {}
    for k, v in items:
        item_dict[k.strip()] = v.strip()

    # 2. 标题 → 名称和区域
    title_m = re.search(r"<title>(.*?)</title>", html)
    if title_m:
        title = title_m.group(1)
        # 去掉前缀后缀: 【多图】... -深圳58安居客
        name = re.sub(r"^【[^】]*】", "", title)
        # 删除 "-深圳" 开始的后缀（如 "-深圳58安居客"），但保留前面的 "-1200平" 这种面积描述
        name = re.sub(r"-深圳.*$", "", name)
        result["name"] = name.strip()

    # 3. 区域 (从地址提取)
    if "地址" in item_dict:
        addr = item_dict["地址"]
        # "罗湖-东门 深南东路3018号"
        area_parts = addr.split()
        if area_parts:
            full_area = area_parts[0]  # "罗湖-东门"
            result["area"] = full_area

    # 4. 面积
    if "面积" in item_dict:
        size_str = item_dict["面积"]  # "1200m²" or "100~500m²"
        result["size"] = re.sub(r"[mM²]", "", size_str)

    # 5. 价格 (优先日租)
    if "日租" in item_dict:
        result["price"] = item_dict["日租"]  # "2元/㎡/天"
    elif "月租" in item_dict:
        result["price"] = item_dict["月租"]  # "7.2万/月"

    # 6. 装修
    if "装修" in item_dict:
        result["decoration"] = item_dict["装修"]

    # 7. 楼层
    if "楼层" in item_dict:
        result["floor"] = item_dict["楼层"]

    # 8. 特色
    features = []
    if "注册" in item_dict:
        features.append(item_dict["注册"])
    if "分割" in item_dict:
        features.append(item_dict["分割"])
    if "付款" in item_dict:
        features.append(item_dict["付款"])
    if "起租期" in item_dict:
        features.append(item_dict["起租期"])
    result["features"] = features

    # 9. 图片 —— 第一个房源实拍图
    img_patterns = [
        r'src="(https://pic1\.ajkimg\.com/display/hj/[^"]*1600x1200[^"]*\.jpg\?[^"]*)"',
        r'src="(https://pic1\.ajkimg\.com/display/hj/[^"]*1600x1200[^"]*\.jpg)"',
        r'src="(https://pic1\.ajkimg\.com/display/hj/[^"]*\.jpg(?:\?[^"]*)?)"',
    ]
    for pat in img_patterns:
        matches = re.findall(pat, html)
        if matches:
            result["image"] = matches[0]
            break

    # 如果标题不理想，用楼盘名
    if "楼盘" in item_dict and len(result["name"]) < 5:
        result["name"] = item_dict["楼盘"]

    return result


async def scrape_url(url, cookies, delay_range=None):
    """
    采集单个安居客房源URL。
    返回解析后的房源字典，失败返回None。
    """
    if delay_range is None:
        delay_range = (CONFIG["delay_min"], CONFIG["delay_max"])

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 先访问首页设置domain
            await page.goto("https://sz.sydc.anjuke.com/", timeout=CONFIG["timeout"])
            await context.add_cookies(cookies)

            # 访问目标页
            print(f"  Fetching: {url}")
            await page.goto(url, timeout=CONFIG["timeout"])
            await page.wait_for_timeout(3000)

            # 检测验证码
            title = await page.title()
            url_actual = page.url
            html = await page.content()

            cv_keywords = ["验证码", "安全验证", "antibot", "滑块", "频繁"]
            cv_triggered = any(kw in title for kw in cv_keywords) or any(
                kw in html[:2000] for kw in cv_keywords
            )

            if cv_triggered:
                print(f"  ⚠️ 触发验证码! title={title}")
                return None

            # 解析
            data = parse_anjuke(html)
            print(f"  ✓ {data['name'][:30]} | {data['price']} | {data['size']}㎡ | img={'有' if data['image'] else '无'}")
            return data

        except Exception as e:
            print(f"  ✗ 错误: {e}")
            return None
        finally:
            await browser.close()


async def scrape_list_page(list_url, cookies):
    """
    从安居客列表页获取房源URL列表。
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto("https://sz.sydc.anjuke.com/", timeout=CONFIG["timeout"])
            await context.add_cookies(cookies)
            await page.goto(list_url, timeout=CONFIG["timeout"])
            await page.wait_for_timeout(3000)

            html = await page.content()
            
            # 提取房源链接: /xzl-zu/{id}/
            links = re.findall(r'href="(/xzl-zu/\d+/)"', html)
            links = list(set(links))  # 去重
            links = ["https://sz.sydc.anjuke.com" + l for l in links]
            
            print(f"  列表页找到 {len(links)} 个房源链接")
            return links
        except Exception as e:
            print(f"  列表页错误: {e}")
            return []
        finally:
            await browser.close()


async def main():
    """
    主函数: 从 URL 文件读取链接并采集
    """
    # 读取URL
    try:
        with open("urls_anjuke.txt", "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        print("❌ 找不到 urls_anjuke.txt")
        print("请创建该文件，每行一个安居客房源URL，例如：")
        print("  https://sz.sydc.anjuke.com/xzl-zu/7460848243/")
        return

    if not urls:
        print("❌ urls_anjuke.txt 为空")
        return

    print(f"📋 共 {len(urls)} 个URL待采集")
    
    # 加载Cookie
    cookies = load_cookies(CONFIG["cookie_file"])
    print(f"🔑 已加载 {len(cookies)} 个Cookie")

    # 采集
    results = []
    for i, url in enumerate(urls):
        print(f"\n[{i+1}/{len(urls)}]")
        data = await scrape_url(url, cookies)
        if data:
            results.append(data)

        # 随机延迟，避免触发风控
        if i < len(urls) - 1:
            delay = random.randint(CONFIG["delay_min"], CONFIG["delay_max"])
            print(f"  ⏳ 等待 {delay} 秒...")
            await asyncio.sleep(delay)

    # 保存结果
    output_file = "anjuke_scraped.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完成! {len(results)}/{len(urls)} 条采集成功")
    print(f"📁 结果保存到: {output_file}")

    # 统计
    if results:
        areas = {}
        for r in results:
            a = r.get("area", "未知")
            areas[a] = areas.get(a, 0) + 1
        print("\n按区域统计:")
        for a, c in areas.items():
            print(f"  {a}: {c}条")
        print(f"\n有图片: {sum(1 for r in results if r.get('image'))}/{len(results)}")


def cmd_test_url(url):
    """命令行: 测试单个URL"""
    cookies = load_cookies(CONFIG["cookie_file"])
    data = asyncio.run(scrape_url(url, cookies))
    if data:
        print("\n--- 解析结果 ---")
        for k, v in data.items():
            print(f"  {k}: {v}")
    else:
        print("采集失败")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        if len(sys.argv) > 2:
            cmd_test_url(sys.argv[2])
        else:
            cmd_test_url("https://sz.sydc.anjuke.com/xzl-zu/7460848243/")
    elif len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_url = sys.argv[2] if len(sys.argv) > 2 else CONFIG["list_urls"]["宝安"]
        cookies = load_cookies(CONFIG["cookie_file"])
        links = asyncio.run(scrape_list_page(list_url, cookies))
        print("\n".join(links))
    else:
        asyncio.run(main())
