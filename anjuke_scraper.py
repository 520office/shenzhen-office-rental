"""
安居客 (Anjuke) 办公室房源采集器 v2.0
===================================
改进：一个浏览器跑全部URL，加真人操作模拟，降低反爬触发率

需要用户提供已登录安居客的Cookie才能使用。
Cookie 获取方式：浏览器登录 anjuke.com → F12 → Console → document.cookie
"""

import asyncio
import json
import datetime
import random
import sys
import re
from playwright.async_api import async_playwright


# === 采集配置 ===
CONFIG = {
    "cookie_file": "anjuke_cookies.txt",   # Cookie 文件路径
    "delay_min": 5,                         # 每条URL最小延迟(秒)
    "delay_max": 12,                        # 每条URL最大延迟(秒)
    "timeout": 30000,                       # 页面加载超时(ms)
    "headless": False,                      # 有头模式（可观察、手动解验证码）
}


def load_cookies(filename):
    """从文件加载 Cookie"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except FileNotFoundError:
        print(f"❌ Cookie 文件不存在: {filename}")
        print("请将 Cookie 粘贴到 anjuke_cookies.txt 文件中")
        sys.exit(1)

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


def normalize_area_name(area):
    """
    归一化区域名：去掉「南山-」「宝安-」等区名前缀，统一为纯区域名。
    例如：「宝安-西乡」→「西乡」、「南山-前海」→「前海」、「南山科技园」→「科技园」
    """
    area = area.strip()
    # 去掉 "XX-" 前缀（XX为2-3个中文字符）
    area = re.sub(r'^[一-龥]{2,3}-', '', area)
    # 已知特例映射
    SPECIAL = {
        '南山科技园': '科技园',
        '深圳湾科技生态园': '深圳湾科技生态园',  # 保持不变
    }
    return SPECIAL.get(area, area)


def parse_anjuke(html):
    """
    从安居客房源页面HTML中提取数据。
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
        name = re.sub(r"^【[^】]*】", "", title)
        name = re.sub(r"-深圳.*$", "", name)
        result["name"] = name.strip()

    # 3. 区域和位置 (从地址提取)
    if "地址" in item_dict:
        addr = item_dict["地址"]
        area_parts = addr.split(None, 1)
        if area_parts:
            full_area = area_parts[0]
            result["area"] = normalize_area_name(full_area)
        addr_clean = addr.strip()
        if addr_clean:
            result["location"] = "深圳市" + addr_clean

    # 4. 面积
    if "面积" in item_dict:
        size_str = item_dict["面积"]
        result["size"] = re.sub(r"[mM²]", "", size_str)

    # 5. 价格 (统一转换为月租单价，元/㎡/月)
    if "日租" in item_dict:
        daily = item_dict["日租"]
        m = re.search(r"([\d.]+)", daily)
        if m:
            monthly = float(m.group(1)) * 30
            result["price"] = f"{monthly:.0f}元/㎡/月"
    elif "月租" in item_dict:
        monthly_price = item_dict["月租"]
        if "㎡" in monthly_price:
            result["price"] = monthly_price
        elif result["size"]:
            m = re.search(r"([\d.]+)", monthly_price)
            size_m = re.search(r"([\d.]+)", result["size"])
            if m and size_m:
                total = float(m.group(1))
                sz = float(size_m.group(1))
                result["price"] = f"{total/sz:.0f}元/㎡/月"
            else:
                result["price"] = monthly_price

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

    # 9. 图片
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

    # 名字优先用楼盘项目名
    if "楼盘" in item_dict and item_dict["楼盘"].strip():
        result["name"] = item_dict["楼盘"].strip()

    return result


async def human_delay(page, min_sec=1, max_sec=3):
    """模拟人类操作的随机延迟"""
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)


async def scrape_url_with_page(page, url):
    """
    使用已有的 page 对象采集单个安居客房源URL。
    返回解析后的房源字典，失败返回None。
    """
    try:
        print(f"  📡 正在访问: {url}")
        
        # 模拟人类：先滚到页面中间再加载
        await page.goto(url, timeout=CONFIG["timeout"], wait_until="domcontentloaded")
        
        # 等待页面渲染
        await page.wait_for_timeout(random.randint(2000, 4000))
        
        # 模拟滚动（人类会看页面）
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
        await human_delay(page, 0.5, 1.5)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 1.5)")
        await human_delay(page, 0.5, 1.5)
        await page.evaluate("window.scrollTo(0, 0)")
        await human_delay(page, 0.3, 1.0)

        # 检测验证码
        title = await page.title()
        html = await page.content()
        
        cv_keywords = ["验证码", "安全验证", "antibot", "滑块", "频繁", "captcha", "verify", "请输入验证码"]
        cv_triggered = any(kw in title for kw in cv_keywords) or any(
            kw in html[:3000] for kw in cv_keywords
        )

        if cv_triggered:
            print(f"  ⚠️ 触发验证码! title={title[:50]}")
            return None

        # 解析
        data = parse_anjuke(html)
        name_short = data['name'][:25] if data['name'] else '(无名称)'
        img_status = '有图' if data['image'] else '无图'
        print(f"  ✅ {name_short} | {data['price']} | {data['size']}㎡ | {img_status}")
        return data

    except Exception as e:
        print(f"  ❌ 错误: {type(e).__name__}: {e}")
        return None


async def main():
    """
    主函数: 一个浏览器跑全部URL
    """
    # 读取URL
    try:
        with open("urls_anjuke.txt", "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        print("❌ 找不到 urls_anjuke.txt")
        print("请创建该文件，每行一个安居客房源URL")
        return

    if not urls:
        print("❌ urls_anjuke.txt 为空")
        return

    print(f"📋 共 {len(urls)} 个URL待采集")
    
    # 加载Cookie
    cookies = load_cookies(CONFIG["cookie_file"])
    print(f"🔑 已加载 {len(cookies)} 个Cookie")

    # 启动浏览器（只启一次）【改进点】
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=CONFIG["headless"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # 先访问首页，设置Cookie
            print("  🌐 正在访问安居客首页设置Cookie...")
            await page.goto("https://sz.sydc.anjuke.com/", timeout=CONFIG["timeout"])
            await context.add_cookies(cookies)
            await page.wait_for_timeout(2000)
            print("  ✓ Cookie 已设置")

            # 采集所有URL
            results = []
            for i, url in enumerate(urls):
                print(f"\n[{i+1}/{len(urls)}]")
                data = await scrape_url_with_page(page, url)
                if data:
                    results.append(data)

                # 随机延迟
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

        finally:
            await browser.close()


def cmd_test_url(url):
    """命令行: 测试单个URL"""
    cookies = load_cookies(CONFIG["cookie_file"])
    
    async def _test():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=CONFIG["headless"])
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("https://sz.sydc.anjuke.com/", timeout=CONFIG["timeout"])
            await context.add_cookies(cookies)
            data = await scrape_url_with_page(page, url)
            await browser.close()
            return data
    
    data = asyncio.run(_test())
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
    else:
        asyncio.run(main())
