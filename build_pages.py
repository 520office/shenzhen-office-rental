#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_pages.py — 从 projects.json 生成所有静态页面
用法: python build_pages.py
输出: index.html（目录门户）+ 13个区域独立页面 + sitemap.xml
"""
import json
import os
import sys
from datetime import datetime

# Windows Git Bash UTF-8 编码修复
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# --- 配置 ---
CONTACT_NAME = "谢经理"
CONTACT_PHONE = "15914050727"
SITE_URL = os.environ.get("SITE_URL", "https://example.com")  # 部署后替换为实际域名
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 深圳常见区域 → 拼音 slug 映射（用于自动生成新区页面）
PINYIN_SLUG = {
    "南山科技园": "nanshan-kejiyuan", "科技园": "nanshan-kejiyuan",
    "前海": "qianhai",
    "宝安中心": "baoan-zhongxin", "宝安中心区": "baoan-zhongxin",
    "西乡": "xixiang", "翻身": "fanshen", "新安": "xinan",
    "兴东": "xingdong", "坪洲": "pingzhou", "碧海湾": "bihaiwan",
    "固戍": "gushu", "福永": "fuyong", "沙井": "shajing", "塘尾": "tangwei",
    "会展新城": "huizhan-xincheng", "南山中心区": "nanshan-zhongxinqu",
    "龙华": "longhua", "龙岗": "longgang", "光明": "guangming",
    "罗湖": "luohu", "福田": "futian", "盐田": "yantian",
    "坪山": "pingshan", "大鹏": "dapeng", "布吉": "buji",
    "坂田": "bantian", "横岗": "henggang", "观澜": "guanlan",
    "民治": "minzhi", "平湖": "pinghu", "南头": "nantou",
    "蛇口": "shekou", "后海": "houhai", "白石洲": "baishizhou",
    "西丽": "xili", "笋岗": "sungang", "石岩": "shiyan",
    "松岗": "songgang", "燕罗": "yanluo", "公明": "gongming",
    "葵涌": "kuichong", "南澳": "nanao", "南山": "nanshan-qu",
    "蔡屋围": "caiwuwei", "车公庙": "chegongmiao", "华强北": "huaqiangbei",
    "香蜜湖": "xiangmihu", "梅林": "meilin", "上梅林": "shangmeilin",
    "皇岗": "huanggang", "保税区": "baoshuiqu",
}

# 13个已知区域的完整定义（手写元数据，SEO 最优）
AREAS = [
    {"name": "南山科技园", "slug": "nanshan-kejiyuan",  "full_name": "南山·科技园",
     "seo_kw": "南山科技园办公室出租,科技园写字楼租赁,南山科技园写字楼招商",
     "desc": "南山科技园核心区域办公室出租，近地铁，配套完善，多种面积可选，精装修拎包入驻。"},
    {"name": "前海",       "slug": "qianhai",           "full_name": "前海自贸区",
     "seo_kw": "前海办公室出租,前海写字楼租赁,前海自贸区写字楼",
     "desc": "前海自贸区核心区域办公室出租，政策优惠，一线海景，甲级写字楼，可注册公司。"},
    {"name": "宝安中心",   "slug": "baoan-zhongxin",    "full_name": "宝安·宝安中心区",
     "seo_kw": "宝安中心办公室出租,宝安中心区写字楼租赁,宝安中心甲级写字楼",
     "desc": "宝安中心区核心地段办公室出租，近地铁，商业配套成熟，甲级写字楼，拎包入驻。"},
    {"name": "西乡",       "slug": "xixiang",           "full_name": "宝安·西乡",
     "seo_kw": "西乡办公室出租,西乡写字楼租赁,宝安西乡写字楼招商",
     "desc": "西乡片区办公室出租，交通便利，价格实惠，适合初创企业和中小企业。"},
    {"name": "翻身",       "slug": "fanshen",           "full_name": "宝安·翻身",
     "seo_kw": "翻身办公室出租,翻身写字楼租赁,宝安翻身写字楼",
     "desc": "翻身片区办公室出租，近前海，交通便捷，性价比高，多种户型可选。"},
    {"name": "新安",       "slug": "xinan",             "full_name": "宝安·新安",
     "seo_kw": "新安办公室出租,新安写字楼租赁,宝安新安写字楼",
     "desc": "新安片区办公室出租，宝安老城区核心地段，配套成熟，生活便利。"},
    {"name": "兴东",       "slug": "xingdong",          "full_name": "宝安·兴东",
     "seo_kw": "兴东办公室出租,兴东写字楼租赁,宝安兴东写字楼",
     "desc": "兴东片区办公室出租，近地铁兴东站，产业园区集中，适合科技企业。"},
    {"name": "坪洲",       "slug": "pingzhou",          "full_name": "宝安·坪洲",
     "seo_kw": "坪洲办公室出租,坪洲写字楼租赁,宝安坪洲写字楼",
     "desc": "坪洲片区办公室出租，近地铁坪洲站，周边商业繁华，办公生活两相宜。"},
    {"name": "碧海湾",     "slug": "bihaiwan",          "full_name": "宝安·碧海湾",
     "seo_kw": "碧海湾办公室出租,碧海湾写字楼租赁,宝安碧海湾写字楼",
     "desc": "碧海湾片区办公室出租，近地铁碧海湾站，海景办公，环境优美。"},
    {"name": "固戍",       "slug": "gushu",             "full_name": "宝安·固戍",
     "seo_kw": "固戍办公室出租,固戍写字楼租赁,宝安固戍写字楼招商",
     "desc": "固戍片区办公室出租，近地铁固戍站，租金实惠，适合仓储办公一体化。"},
    {"name": "福永",       "slug": "fuyong",             "full_name": "宝安·福永",
     "seo_kw": "福永办公室出租,福永写字楼租赁,宝安福永写字楼招商,会展湾办公室",
     "desc": "福永片区办公室出租，近深圳国际会展中心、地铁11号线，甲级写字楼，配套食堂。"},
    {"name": "沙井",       "slug": "shajing",           "full_name": "宝安·沙井",
     "seo_kw": "沙井办公室出租,沙井写字楼租赁,宝安沙井写字楼招商",
     "desc": "沙井片区办公室出租，大空港辐射区，交通便利，发展潜力大。"},
    {"name": "会展新城",   "slug": "huizhan-xincheng",  "full_name": "宝安·会展新城",
     "seo_kw": "会展新城办公室出租,会展新城写字楼租赁,深圳国际会展中心附近办公室",
     "desc": "会展新城片区办公室出租，紧邻深圳国际会展中心，配套完善，全新写字楼。"},
]


# ===== 动态区域支持 =====

def make_slug(name):
    """根据区域中文名生成 URL slug（优先查表，找不到用作 hash fallback）"""
    if name in PINYIN_SLUG:
        return PINYIN_SLUG[name]
    # fallback: 用 hash 保证唯一且稳定
    return "area-" + str(abs(hash(name)) % 10000).zfill(4)


def extract_area_name(raw_area):
    """从原始 area 字段提取纯区域名（如 '宝安-龙华' → '龙华'）"""
    # 去掉前缀如 "宝安-" "南山-" "福田-" 等
    for prefix in ["宝安-", "南山-", "福田-", "罗湖-", "龙华-", "龙岗-", "光明-", "盐田-", "坪山-"]:
        if raw_area.startswith(prefix):
            return raw_area[len(prefix):]
    return raw_area.strip()


def auto_generate_area_info(name):
    """为新区自动生成 area_info 字典"""
    slug = make_slug(name)
    return {
        "name": name,
        "slug": slug,
        "full_name": f"深圳·{name}",
        "seo_kw": f"{name}办公室出租,{name}写字楼租赁,{name}写字楼招商",
        "desc": f"{name}片区办公室出租，交通便利，多种面积可选，精装修拎包入驻。",
        "auto": True,  # 标记为自动生成
    }


def resolve_dynamic_areas(projects):
    """
    核心：动态解析所有区域。
    1. 先用已知 AREAS 匹配
    2. 未匹配的自动生成新区
    3. 返回 (all_areas, grouped) — all_areas 包含已知+自动，grouped 按 slug 分组
    """
    # 已知区域 slug → area_info
    known_by_slug = {a["slug"]: a for a in AREAS}
    known_by_name = {a["name"]: a for a in AREAS}

    # 初始化分组（已知区域）
    grouped = {a["slug"]: [] for a in AREAS}

    # 收集未匹配房源的原始区域名
    unmatched_raw = set()

    for proj in projects:
        raw = proj.get("area", "")
        found = False
        for a in AREAS:
            if match_area(raw, a):
                grouped[a["slug"]].append(proj)
                found = True
                break
        if not found:
            # 提取纯区域名
            name = extract_area_name(raw)
            if name not in known_by_name:
                unmatched_raw.add(name)
            # 暂存，等新区创建后再分配
            proj["_auto_area"] = name

    # 为未匹配区域自动生成 area_info
    auto_areas = []
    for name in sorted(unmatched_raw):
        info = auto_generate_area_info(name)
        auto_areas.append(info)
        grouped[info["slug"]] = []
        print(f"  🆕 自动创建区域: {name} → {info['slug']}.html")

    # 把暂存的房源分配到新区
    for proj in projects:
        auto_name = proj.pop("_auto_area", None)
        if auto_name:
            for a in auto_areas:
                if a["name"] == auto_name:
                    grouped[a["slug"]].append(proj)
                    break

    # 构建完整的区域列表（已知 + 自动），已知排在前面
    all_areas = list(AREAS) + auto_areas

    # 删除空的新区（不该出现但安全起见）
    all_areas = [a for a in all_areas if grouped.get(a["slug"])]

    return all_areas, grouped


def load_projects():
    """加载房源数据"""
    path = os.path.join(SCRIPT_DIR, "projects.json")
    if not os.path.exists(path):
        print(f"❌ 未找到 {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        projects = json.load(f)
    print(f"📂 加载了 {len(projects)} 条房源数据")
    return projects


def match_area(project_area, area_info):
    """判断房源是否属于某个区域"""
    area_name = area_info["name"]
    pa = project_area.replace("-", "").replace(" ", "").lower()
    # 直接匹配
    if area_name in pa:
        return True
    # 特殊映射：覆盖各种 region-子区域 的写法
    maps_all = {
        "南山科技园": ["南山科技园", "科技园"],
        "前海":       ["前海"],
        "宝安中心":   ["宝安中心区", "宝安中心"],
        "西乡":       ["西乡"],
        "翻身":       ["翻身"],
        "新安":       ["新安"],
        "兴东":       ["兴东"],
        "坪洲":       ["坪洲"],
        "碧海湾":     ["碧海湾", "碧海"],
        "固戍":       ["固戍"],
        "福永":       ["福永"],
        "沙井":       ["沙井"],
        "会展新城":   ["会展新城", "会展湾"],
    }
    for kw in maps_all.get(area_name, [area_name]):
        if kw.lower() in pa:
            return True
    return False


def group_by_area(projects):
    """按区域分组"""
    grouped = {}
    for area_info in AREAS:
        grouped[area_info["slug"]] = []
    for proj in projects:
        found = False
        for area_info in AREAS:
            if match_area(proj.get("area", ""), area_info):
                grouped[area_info["slug"]].append(proj)
                found = True
                break
        if not found:
            # 放到"其他"（暂用福永）
            grouped["fuyong"].append(proj)
            print(f"⚠️  无法匹配区域: {proj.get('name')} (area={proj.get('area')})")
    return grouped


def card_html(proj):
    """生成单个房源卡片的 HTML"""
    img_html = ""
    if proj.get("image"):
        img_html = f'<img class="card-image" src="{proj["image"]}" alt="{proj["name"]}" loading="lazy" onerror="this.parentElement.innerHTML=\'<div class=card-image-placeholder>🏢</div>\'">'
    else:
        img_html = '<div class="card-image-placeholder">🏢</div>'

    tags_html = "".join(f'<span class="card-tag">{t}</span>' for t in (proj.get("features") or []))
    date_str = proj.get("date", "").replace("-", "/") if proj.get("date") else ""

    return f"""
            <div class="project-card">
                <div style="position:relative;">
                    {img_html}
                    <span class="card-badge">{proj.get('area', '')}</span>
                </div>
                <div class="card-body">
                    <div class="card-title">{proj.get('name', '')}</div>
                    <div class="card-location">📍 {proj.get('location', '')}</div>
                    {"<div style=\"font-size:12px;color:#94a3b8;margin-top:-6px;margin-bottom:12px;\">📅 更新于 "+date_str+"</div>" if date_str else ""}
                    <div class="card-meta">
                        <div class="meta-item">
                            <span class="meta-label">面积</span>
                            <span class="meta-value">{proj.get('size', '')}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">价格</span>
                            <span class="meta-value price">{proj.get('price', '')}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">装修</span>
                            <span class="meta-value" style="font-size:14px;color:#64748b;">{proj.get('decoration', '')}</span>
                        </div>
                        <div class="meta-item">
                            <span class="meta-label">楼层</span>
                            <span class="meta-value" style="font-size:14px;color:#64748b;">{proj.get('floor', '')}</span>
                        </div>
                    </div>
                    <div class="card-tags">{tags_html}</div>
                    <div class="card-footer">
                        <span style="font-size:13px;color:#94a3b8;">☎️ {CONTACT_NAME} {CONTACT_PHONE}</span>
                        <a href="tel:{CONTACT_PHONE}" class="card-contact-btn">马上咨询</a>
                    </div>
                </div>
            </div>"""


def make_html_head(area_info=None):
    """生成 HTML <head> 部分"""
    if area_info:
        title = f"{area_info['full_name']}办公室出租 | {area_info['name']}写字楼租赁 | {CONTACT_NAME}{CONTACT_PHONE}"
        desc = area_info["desc"]
        kw = area_info["seo_kw"]
        og_title = f"{area_info['full_name']}办公室出租 | {area_info['name']}写字楼租赁"
        canonical = f"{SITE_URL}/{area_info['slug']}.html"
    else:
        title = f"深圳办公室出租 | 南山科技园·前海·宝安 | {CONTACT_NAME}{CONTACT_PHONE}"
        desc = "深圳南山科技园、前海、宝安13大区域办公室出租，精装修拎包入驻，多种面积可选，价格实惠，联系谢经理15914050727"
        kw = "深圳办公室出租,南山科技园写字楼,前海办公室,宝安办公室出租,深圳写字楼招商,办公室租赁"
        og_title = f"深圳办公室出租 | 南山科技园·前海·宝安 | {CONTACT_NAME}{CONTACT_PHONE}"
        canonical = f"{SITE_URL}/"

    return f"""    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{desc}">
    <meta name="keywords" content="{kw}">
    <meta name="author" content="{CONTACT_NAME} {CONTACT_PHONE}">
    <meta property="og:title" content="{og_title}">
    <meta property="og:description" content="{desc}">
    <meta property="og:type" content="website">
    <link rel="canonical" href="{canonical}">
    <title>{title}</title>"""


def area_nav_html(all_areas, current_slug=None):
    """生成区域导航标签"""
    tags = []
    for a in all_areas:
        active = ' active' if a["slug"] == current_slug else ''
        tags.append(f'                <a href="{a["slug"]}.html" class="filter-tag{active}">{a["name"]}</a>')
    return "\n".join(tags)


def area_directory_html(all_areas, grouped):
    """生成主门户页面 - 区域目录"""
    rows = []
    for a in all_areas:
        count = len(grouped.get(a["slug"], []))
        badge = f'<span class="badge-count">{count}套房源</span>' if count > 0 else '<span class="badge-empty">暂无房源</span>'
        rows.append(f"""                <a href="{a['slug']}.html" class="area-card">
                    <div class="area-card-header">
                        <span class="area-card-title">{a['name']}</span>
                        {badge}
                    </div>
                    <div class="area-card-desc">{a['desc']}</div>
                </a>""")

    return "\n".join(rows)


def area_schema_json(all_areas, grouped):
    """生成首页的 Schema.org 结构化数据"""
    items = []
    for a in all_areas:
        for proj in grouped.get(a["slug"], []):
            items.append({
                "@type": "Product",
                "name": proj.get("name", ""),
                "description": f"{a['name']} {proj.get('size', '')} 办公室出租，{proj.get('decoration', '')}，{proj.get('price', '')}",
                "offers": {
                    "@type": "Offer",
                    "price": proj.get("price", "").replace("元/㎡/月", ""),
                    "priceCurrency": "CNY",
                    "areaServed": {"@type": "City", "name": "深圳"},
                }
            })
    return json.dumps(items, ensure_ascii=False, indent=4)


def area_schema_for_page(area_info, projects):
    """生成区域页面的 Schema.org 结构化数据"""
    items = []
    for proj in projects:
        items.append({
            "@type": "Product",
            "name": proj.get("name", ""),
            "description": f"{area_info['name']} {proj.get('size', '')} 办公室出租，{proj.get('decoration', '')}，{proj.get('price', '')}",
            "offers": {
                "@type": "Offer",
                "price": proj.get("price", "").replace("元/㎡/月", ""),
                "priceCurrency": "CNY",
                "areaServed": {"@type": "City", "name": "深圳"},
            }
        })
    return json.dumps(items, ensure_ascii=False, indent=4)


# ===== 共享 CSS =====
SHARED_CSS = r"""
        /* ===== CSS Reset & Base ===== */
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --accent: #f59e0b;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --text-light: #64748b;
            --border: #e2e8f0;
            --radius: 12px;
            --shadow: 0 4px 24px rgba(0,0,0,0.08);
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            color: var(--text);
            background: var(--bg);
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }

        /* ===== Header ===== */
        .header {
            background: white;
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        }
        .header-inner {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px;
            height: 64px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .logo {
            font-size: 20px;
            font-weight: 700;
            color: var(--primary);
            text-decoration: none;
        }
        .logo span { color: var(--accent); }
        .header-phone {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 600;
            color: var(--primary);
            text-decoration: none;
            font-size: 16px;
        }
        .header-phone::before { content: "📞"; font-size: 18px; }

        /* ===== Hero ===== */
        .hero {
            background: linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #60a5fa 100%);
            color: white;
            padding: 80px 24px 60px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        .hero::before {
            content: "";
            position: absolute;
            inset: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 320"><path fill="%23ffffff" fill-opacity="0.05" d="M0,192L48,176C96,160,192,128,288,138.7C384,149,480,203,576,213.3C672,224,768,192,864,181.3C960,171,1056,181,1152,186.7C1248,192,1344,192,1392,192L1440,192L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"></path></svg>') bottom center / cover no-repeat;
            pointer-events: none;
        }
        .hero h1 { font-size: 42px; font-weight: 800; margin-bottom: 16px; position: relative; }
        .hero h1 em { font-style: normal; color: var(--accent); }
        .hero p { font-size: 18px; opacity: 0.9; max-width: 600px; margin: 0 auto 32px; position: relative; }
        .hero-cta {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: var(--accent);
            color: white;
            padding: 14px 36px;
            border-radius: 50px;
            font-size: 18px;
            font-weight: 700;
            text-decoration: none;
            position: relative;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 20px rgba(245,158,11,0.4);
        }
        .hero-cta:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(245,158,11,0.5); }

        /* ===== Breadcrumb ===== */
        .breadcrumb {
            max-width: 1200px;
            margin: 0 auto;
            padding: 16px 24px;
            font-size: 14px;
            color: var(--text-light);
        }
        .breadcrumb a { color: var(--primary); text-decoration: none; }
        .breadcrumb a:hover { text-decoration: underline; }

        /* ===== Navigation Bar ===== */
        .nav-section {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px 20px;
        }
        .nav-bar {
            background: white;
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 20px 24px;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
        }
        .nav-label { font-weight: 600; color: var(--text); margin-right: 8px; white-space: nowrap; }
        .filter-tag {
            display: inline-block;
            padding: 8px 18px;
            border-radius: 50px;
            border: 1.5px solid var(--border);
            background: white;
            color: var(--text-light);
            font-size: 14px;
            text-decoration: none;
            transition: all 0.2s;
            white-space: nowrap;
        }
        .filter-tag:hover, .filter-tag.active {
            border-color: var(--primary);
            color: var(--primary);
            background: #eff6ff;
        }
        .filter-tag.active { background: var(--primary); color: white; border-color: var(--primary); }

        /* ===== Area Directory Cards (index page) ===== */
        .area-grid {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px;
        }
        .area-cards {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
            margin-bottom: 40px;
        }
        .area-card {
            background: white;
            border-radius: var(--radius);
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
            padding: 20px 24px;
            text-decoration: none;
            transition: transform 0.2s, box-shadow 0.2s;
            border: 1px solid var(--border);
            display: block;
        }
        .area-card:hover { transform: translateY(-3px); box-shadow: 0 8px 30px rgba(0,0,0,0.12); }
        .area-card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
        .area-card-title { font-size: 18px; font-weight: 700; color: var(--text); }
        .area-card-desc { font-size: 13px; color: var(--text-light); line-height: 1.5; }
        .badge-count {
            background: #dcfce7;
            color: #166534;
            padding: 3px 10px;
            border-radius: 50px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-empty {
            background: #f1f5f9;
            color: #94a3b8;
            padding: 3px 10px;
            border-radius: 50px;
            font-size: 12px;
        }

        /* ===== Projects Grid ===== */
        .projects-section {
            max-width: 1200px;
            margin: 40px auto;
            padding: 0 24px;
        }
        .section-title { font-size: 28px; font-weight: 800; margin-bottom: 8px; }
        .section-subtitle { color: var(--text-light); margin-bottom: 32px; font-size: 16px; }
        .projects-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 24px;
        }

        /* ===== Project Card ===== */
        .project-card {
            background: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            transition: transform 0.25s, box-shadow 0.25s;
            border: 1px solid var(--border);
        }
        .project-card:hover { transform: translateY(-4px); box-shadow: 0 12px 40px rgba(0,0,0,0.12); }
        .card-image { width: 100%; height: 220px; object-fit: cover; display: block; background: #e2e8f0; }
        .card-image-placeholder {
            width: 100%; height: 220px;
            background: linear-gradient(135deg, #cbd5e1, #94a3b8);
            display: flex; align-items: center; justify-content: center;
            color: white; font-size: 48px;
        }
        .card-badge {
            position: absolute; top: 12px; left: 12px;
            background: var(--primary); color: white;
            padding: 4px 12px; border-radius: 50px;
            font-size: 12px; font-weight: 600;
        }
        .card-body { padding: 20px; }
        .card-title { font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text); }
        .card-location { display: flex; align-items: center; gap: 4px; color: var(--text-light); font-size: 14px; margin-bottom: 12px; }
        .card-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px; }
        .meta-item { display: flex; flex-direction: column; }
        .meta-label { font-size: 12px; color: var(--text-light); }
        .meta-value { font-size: 16px; font-weight: 700; color: var(--primary); }
        .meta-value.price { color: #dc2626; }
        .card-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
        .card-tag { padding: 3px 10px; border-radius: 50px; background: #f1f5f9; font-size: 12px; color: var(--text-light); }
        .card-footer {
            display: flex; align-items: center; justify-content: space-between;
            padding-top: 16px; border-top: 1px solid var(--border);
        }
        .card-contact-btn {
            display: inline-flex; align-items: center; gap: 6px;
            background: var(--primary); color: white;
            padding: 8px 20px; border-radius: 50px;
            font-size: 14px; font-weight: 600; text-decoration: none;
            transition: background 0.2s;
        }
        .card-contact-btn:hover { background: var(--primary-dark); }

        /* ===== Info Section (index only) ===== */
        .info-section {
            max-width: 1200px;
            margin: 40px auto;
            padding: 0 24px;
        }
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 16px;
        }
        .info-card {
            background: white;
            border-radius: var(--radius);
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
            padding: 24px;
            border: 1px solid var(--border);
        }
        .info-card h3 { font-size: 16px; font-weight: 700; margin-bottom: 8px; color: var(--text); }
        .info-card p { font-size: 13px; color: var(--text-light); line-height: 1.6; }

        /* ===== Contact Banner ===== */
        .contact-banner {
            background: linear-gradient(135deg, #1e40af, #3b82f6);
            color: white;
            padding: 60px 24px;
            text-align: center;
        }
        .contact-banner h2 { font-size: 32px; font-weight: 800; margin-bottom: 12px; }
        .contact-banner p { font-size: 18px; opacity: 0.9; margin-bottom: 32px; }
        .contact-cards {
            display: flex; justify-content: center; gap: 24px;
            flex-wrap: wrap; max-width: 800px; margin: 0 auto;
        }
        .contact-card {
            background: rgba(255,255,255,0.15);
            backdrop-filter: blur(10px);
            border-radius: var(--radius);
            padding: 24px 32px;
            min-width: 220px;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .contact-card-icon { font-size: 32px; margin-bottom: 12px; }
        .contact-card-label { font-size: 14px; opacity: 0.8; margin-bottom: 4px; }
        .contact-card-value { font-size: 20px; font-weight: 700; }
        .contact-card-value a { color: white; text-decoration: none; }

        /* ===== Footer ===== */
        .footer {
            background: #0f172a;
            color: #94a3b8;
            padding: 40px 24px;
            text-align: center;
            font-size: 14px;
        }
        .footer a { color: #60a5fa; text-decoration: none; }
        .footer-links { display: flex; flex-wrap: wrap; justify-content: center; gap: 12px; margin-bottom: 16px; }
        .footer-links a { color: #94a3b8; text-decoration: none; font-size: 13px; }

        /* ===== Responsive ===== */
        @media (max-width: 768px) {
            .hero h1 { font-size: 28px; }
            .hero p { font-size: 16px; }
            .projects-grid, .area-cards { grid-template-columns: 1fr; }
            .nav-bar { overflow-x: auto; flex-wrap: nowrap; padding: 16px; }
            .filter-tag { flex-shrink: 0; }
            .contact-cards { flex-direction: column; align-items: center; }
            .header-inner { padding: 0 16px; }
            .header-phone span { display: none; }
        }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* ===== Search Box ===== */
        .search-section {
            padding: 0 0 20px;
        }
        .search-box-wrap {
            background: white;
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 16px 24px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .search-icon { font-size: 20px; color: var(--text-light); flex-shrink: 0; }
        .search-input {
            flex: 1;
            border: none;
            outline: none;
            font-size: 16px;
            color: var(--text);
            background: transparent;
            min-width: 0;
        }
        .search-input::placeholder { color: #94a3b8; }
        .search-clear {
            background: none;
            border: none;
            font-size: 20px;
            color: var(--text-light);
            cursor: pointer;
            padding: 0 4px;
            display: none;
        }
        .search-clear.visible { display: inline; }
        .search-count {
            font-size: 13px;
            color: var(--text-light);
            white-space: nowrap;
        }
        .search-no-result {
            text-align: center;
            padding: 60px 24px;
            color: var(--text-light);
            font-size: 16px;
            display: none;
        }
        .search-no-result.visible { display: block; }
        .highlight { background: #fef08a; border-radius: 2px; padding: 0 2px; }
"""

# ===== 搜索框 HTML =====
def search_box_html():
    """生成搜索框 HTML"""
    return """    <!-- Search -->
    <div class="search-section">
        <div class="search-box-wrap">
            <span class="search-icon">🔍</span>
            <input type="text" class="search-input" id="searchInput" placeholder="搜索项目名称、位置、面积..." autocomplete="off">
            <button class="search-clear" id="searchClear" onclick="clearSearch()" title="清除搜索">✕</button>
            <span class="search-count" id="searchCount"></span>
        </div>
    </div>"""


# ===== 搜索功能 JavaScript =====
SEARCH_JS = r"""
        var _totalCards = 0;
        var _timer = null;

        document.addEventListener('DOMContentLoaded', function() {
            var input = document.getElementById('searchInput');
            var clearBtn = document.getElementById('searchClear');
            if (!input) return;

            _totalCards = document.querySelectorAll('.project-card').length;

            // 输入防抖
            input.addEventListener('input', function() {
                if (_timer) clearTimeout(_timer);
                _timer = setTimeout(doSearch, 250);
                updateClearBtn();
            });

            // 回车立即搜索
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    if (_timer) clearTimeout(_timer);
                    doSearch();
                }
                if (e.key === 'Escape') {
                    input.value = '';
                    doSearch();
                    updateClearBtn();
                }
            });
        });

        function updateClearBtn() {
            var input = document.getElementById('searchInput');
            var btn = document.getElementById('searchClear');
            if (input && btn) {
                if (input.value.length > 0) btn.classList.add('visible');
                else btn.classList.remove('visible');
            }
        }

        function clearSearch() {
            var input = document.getElementById('searchInput');
            if (input) { input.value = ''; updateClearBtn(); }
            doSearch();
            var inputEl = document.getElementById('searchInput');
            if (inputEl) inputEl.focus();
        }

        function doSearch() {
            var input = document.getElementById('searchInput');
            var query = (input ? input.value.trim().toLowerCase() : '');
            var cards = document.querySelectorAll('.project-card');
            var countEl = document.getElementById('searchCount');
            var noResultEl = document.getElementById('searchNoResult');
            var gridEl = document.querySelector('.projects-grid');
            var visibleCount = 0;

            cards.forEach(function(card) {
                // 清除之前的高亮
                var prev = card.querySelectorAll('.highlight');
                prev.forEach(function(h) {
                    h.outerHTML = h.textContent;
                });

                if (!query) {
                    card.style.display = '';
                    visibleCount++;
                    return;
                }

                // 搜索文本内容
                var text = (card.textContent || '').toLowerCase();
                if (text.indexOf(query) !== -1) {
                    card.style.display = '';
                    visibleCount++;
                    // 高亮匹配文字
                    highlightText(card.querySelector('.card-title'), query);
                    highlightText(card.querySelector('.card-location'), query);
                } else {
                    card.style.display = 'none';
                }
            });

            // 更新计数
            if (countEl) {
                if (query) {
                    countEl.textContent = visibleCount + '/' + _totalCards + ' 条';
                } else {
                    countEl.textContent = '';
                }
            }

            // 无结果提示
            if (noResultEl) {
                if (query && visibleCount === 0) {
                    noResultEl.classList.add('visible');
                } else {
                    noResultEl.classList.remove('visible');
                }
            }
        }

        function highlightText(el, query) {
            if (!el || !query) return;
            var html = el.innerHTML;
            // 避免重复高亮已高亮的内容
            if (html.indexOf('highlight') !== -1) return;
            var regex = new RegExp('(' + escapeRegExp(query) + ')', 'gi');
            el.innerHTML = html.replace(regex, '<span class="highlight">$1</span>');
        }

        function escapeRegExp(s) {
            return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        }
"""


def search_script_tag():
    """返回搜索脚本标签"""
    return f"    <script>{SEARCH_JS}\n    </script>"


def build_index(all_areas, grouped):
    """生成主门户页面"""
    total = sum(len(v) for v in grouped.values())
    area_count = len(all_areas)

    # 区域卡片
    area_cards = area_directory_html(all_areas, grouped)

    # 精选推荐：每个有房源的区域取一条最新房源
    featured_cards = []
    for a in all_areas:
        items = grouped.get(a["slug"], [])
        if items:
            # 取最新的一条（已排序）
            items.sort(key=lambda p: p.get("date", "2000-01-01"), reverse=True)
            featured_cards.append(card_html(items[0]))

    featured_html = "\n".join(featured_cards) if featured_cards else '<p style="text-align:center;color:#94a3b8;padding:40px;">暂无房源，请联系谢经理获取最新信息</p>'

    # 底部各区域链接
    footer_links = " | ".join(f'<a href="{a["slug"]}.html">{a["name"]}办公室出租</a>' for a in all_areas)

    # 动态区域名词列表（前8个+等）
    area_names = [a["name"] for a in all_areas]
    if len(area_names) > 8:
        area_summary = "、".join(area_names[:8]) + f"等{area_count}大核心商务区域"
    else:
        area_summary = "、".join(area_names) + "核心商务区域"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
{make_html_head(None)}
    <!-- Schema.org Structured Data -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "RealEstateAgent",
      "name": "谢经理办公室租赁",
      "description": "深圳南山科技园、前海、宝安区域办公室出租服务",
      "telephone": "{CONTACT_PHONE}",
      "areaServed": {{
        "@type": "City",
        "name": "深圳"
      }},
      "makesOffer": {area_schema_json(all_areas, grouped)}
    }}
    </script>
    <style>{SHARED_CSS}
    </style>
</head>
<body>

    <!-- Header -->
    <header class="header">
        <div class="header-inner">
            <a href="/" class="logo">🏢 深圳<span>办公室出租</span></a>
            <a href="tel:{CONTACT_PHONE}" class="header-phone"><span>{CONTACT_NAME}</span> {CONTACT_PHONE}</a>
        </div>
    </header>

    <!-- Hero -->
    <section class="hero">
        <h1>深圳<em>办公室出租</em></h1>
        <p>南山科技园 · 前海 · 宝安 | {area_count}大区域覆盖 | 精装修拎包入驻 | 多面积可选</p>
        <a href="tel:{CONTACT_PHONE}" class="hero-cta">📞 立即咨询 {CONTACT_NAME} {CONTACT_PHONE}</a>
    </section>

    <!-- Area Directory -->
    <section class="projects-section">
        <h2 class="section-title">📍 选择区域</h2>
        <p class="section-subtitle">覆盖深圳{area_count}大核心商务区域，共 <strong style="color:var(--primary);">{total}</strong> 套房源任您挑选</p>
{search_box_html()}
        <div class="area-cards">
{area_cards}
        </div>
    </section>

    <!-- Featured Listings -->
    <section class="projects-section">
        <h2 class="section-title">✨ 精选推荐</h2>
        <p class="section-subtitle">各区域优质房源推荐，更多选择请进入区域页面查看</p>
    </section>
    <section class="projects-section" style="margin-top:0;">
        <div class="projects-grid">
{featured_html}
        </div>
        <p class="search-no-result" id="searchNoResult">😕 未找到匹配的房源，试试换个关键词吧！<br>📞 联系{CONTACT_NAME} {CONTACT_PHONE} 获取更多房源</p>
    </section>

    <!-- Service Info -->
    <section class="info-section">
        <h2 class="section-title" style="margin-bottom:24px;">💼 服务优势</h2>
        <div class="info-grid">
            <div class="info-card">
                <h3>🏢 {area_count}大区域覆盖</h3>
                <p>{area_summary}，全深圳核心商务区房源一网打尽。</p>
            </div>
            <div class="info-card">
                <h3>📐 面积灵活</h3>
                <p>从100㎡到800㎡以上，小户型到大平层，满足不同规模企业需求。初创团队到中大型企业，总有一款适合您。</p>
            </div>
            <div class="info-card">
                <h3>🔑 精装拎包入驻</h3>
                <p>全部房源精装修/豪华装修，配家私、空调、网络齐全，签约即可办公，省去装修时间和成本。</p>
            </div>
            <div class="info-card">
                <h3>📋 可注册公司</h3>
                <p>所有房源均支持工商注册，提供红本租赁凭证，助您快速完成公司注册和地址变更。</p>
            </div>
        </div>
    </section>

    <!-- Contact Banner -->
    <section class="contact-banner">
        <h2>📞 立即联系看房</h2>
        <p>专业顾问免费带看，帮您找到最适合的办公空间</p>
        <div class="contact-cards">
            <div class="contact-card">
                <div class="contact-card-icon">📱</div>
                <div class="contact-card-label">联系电话</div>
                <div class="contact-card-value"><a href="tel:{CONTACT_PHONE}">{CONTACT_PHONE}</a></div>
            </div>
            <div class="contact-card">
                <div class="contact-card-icon">👤</div>
                <div class="contact-card-label">联系人</div>
                <div class="contact-card-value">{CONTACT_NAME}</div>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
        <div class="footer-links">
            {footer_links}
        </div>
        <p>© 2026 深圳办公室出租 | 联系人：{CONTACT_NAME} | 电话：{CONTACT_PHONE}</p>
        <p style="margin-top:4px;font-size:12px;">
            <a href="sitemap.xml">站点地图 (Sitemap)</a>
        </p>
    </footer>

{search_script_tag()}
</body>
</html>"""

    path = os.path.join(SCRIPT_DIR, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 生成 index.html（门户目录，{total} 套房源）")


def latest_date(projects):
    """取房源列表中最新的日期，用于页面更新时间显示"""
    dates = [p.get("date", "") for p in projects if p.get("date")]
    return max(dates) if dates else datetime.now().strftime("%Y-%m-%d")


def fmt_date(iso):
    """2026-06-08 → 2026年06月08日"""
    try:
        y, m, d = iso.split("-")
        return f"{y}年{int(m)}月{int(d)}日"
    except Exception:
        return iso


def build_area_page(all_areas, area_info, projects):
    """生成一个区域独立页面"""
    slug = area_info["slug"]

    # 按日期排序
    projects.sort(key=lambda p: p.get("date", "2000-01-01"), reverse=True)

    cards = "\n".join(card_html(p) for p in projects) if projects else '<p style="text-align:center;color:#94a3b8;padding:60px;font-size:18px;">该区域暂无房源<br>📞 联系{CONTACT_NAME}获取最新信息 {CONTACT_PHONE}</p>'

    # 底部各区域链接
    footer_links = " | ".join(f'<a href="{a["slug"]}.html">{a["name"]}办公室出租</a>' for a in all_areas)

    # 页面更新时间 = 房源中最新的日期
    ld = latest_date(projects)
    update_str = fmt_date(ld) if projects else datetime.now().strftime("%Y年%m月%d日")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
{make_html_head(area_info)}
    <!-- Schema.org Structured Data -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "RealEstateAgent",
      "name": "{CONTACT_NAME}办公室租赁 - {area_info['name']}",
      "description": "{area_info['desc']}",
      "telephone": "{CONTACT_PHONE}",
      "areaServed": {{
        "@type": "City",
        "name": "深圳"
      }},
      "makesOffer": {area_schema_for_page(area_info, projects)}
    }}
    </script>
    <style>{SHARED_CSS}
    </style>
</head>
<body>

    <!-- Header -->
    <header class="header">
        <div class="header-inner">
            <a href="index.html" class="logo">🏢 深圳<span>办公室出租</span></a>
            <a href="tel:{CONTACT_PHONE}" class="header-phone"><span>{CONTACT_NAME}</span> {CONTACT_PHONE}</a>
        </div>
    </header>

    <!-- Breadcrumb -->
    <div class="breadcrumb">
        <a href="index.html">🏠 首页</a> &raquo; <strong>{area_info['full_name']}办公室出租</strong>
    </div>

    <!-- Hero -->
    <section class="hero">
        <h1><em>{area_info['name']}</em>办公室出租</h1>
        <p>{area_info['desc']}</p>
        <a href="tel:{CONTACT_PHONE}" class="hero-cta">📞 立即咨询 {CONTACT_NAME} {CONTACT_PHONE}</a>
    </section>

    <!-- Navigation -->
    <div class="nav-section">
        <div class="nav-bar">
            <span class="nav-label">📍 区域切换</span>
{area_nav_html(all_areas, slug)}
        </div>
    </div>

{search_box_html()}

    <!-- Listings -->
    <section class="projects-section">
        <h2 class="section-title">{area_info['name']}在租房源</h2>
        <p class="section-subtitle">{area_info['full_name']}区域共 <strong style="color:var(--primary);">{len(projects)}</strong> 套办公室出租，更新时间：{update_str}</p>
        <div class="projects-grid">
{cards}
        </div>
        <p class="search-no-result" id="searchNoResult">😕 未找到匹配的房源，试试换个关键词吧！<br>📞 联系{CONTACT_NAME} {CONTACT_PHONE} 获取更多房源</p>
    </section>

    <!-- Contact Banner -->
    <section class="contact-banner">
        <h2>📞 预约看房</h2>
        <p>免费带看{area_info['name']}区域办公室，帮您找到最佳办公空间</p>
        <div class="contact-cards">
            <div class="contact-card">
                <div class="contact-card-icon">📱</div>
                <div class="contact-card-label">联系电话</div>
                <div class="contact-card-value"><a href="tel:{CONTACT_PHONE}">{CONTACT_PHONE}</a></div>
            </div>
            <div class="contact-card">
                <div class="contact-card-icon">👤</div>
                <div class="contact-card-label">联系人</div>
                <div class="contact-card-value">{CONTACT_NAME}</div>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
        <div class="footer-links">
            {footer_links}
        </div>
        <p>© 2026 深圳办公室出租 | 联系人：{CONTACT_NAME} | 电话：{CONTACT_PHONE}</p>
        <p style="margin-top:4px;font-size:12px;">
            <a href="index.html">返回首页</a> | <a href="sitemap.xml">站点地图</a>
        </p>
    </footer>

{search_script_tag()}
</body>
</html>"""

    filename = f"{slug}.html"
    path = os.path.join(SCRIPT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✅ 生成 {filename}（{area_info['name']}，{len(projects)} 套房源）")


def build_sitemap(all_areas, grouped):
    """生成 sitemap.xml — lastmod 使用真实最新日期"""
    # 首页：所有房源中最新的日期
    all_projects = []
    for v in grouped.values():
        all_projects.extend(v)
    home_lastmod = latest_date(all_projects)

    urls = [f"""  <url>
    <loc>{SITE_URL}/</loc>
    <lastmod>{home_lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>"""]

    for a in all_areas:
        projects = grouped.get(a["slug"], [])
        lastmod = latest_date(projects) if projects else datetime.now().strftime("%Y-%m-%d")
        urls.append(f"""  <url>
    <loc>{SITE_URL}/{a['slug']}.html</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""

    path = os.path.join(SCRIPT_DIR, "sitemap.xml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"✅ 生成 sitemap.xml（{len(urls)} 个 URL）")


def main():
    print("=" * 60)
    print("🏗️  深圳办公室出租 - 静态页面生成器")
    print(f"📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    projects = load_projects()

    # 动态区域解析（已知区域 + 自动发现新区）
    print("\n🔍 解析区域...")
    all_areas, grouped = resolve_dynamic_areas(projects)

    # 统计
    total_matched = sum(len(v) for v in grouped.values())

    print(f"\n📊 房源分布（{len(all_areas)} 个区域）:")
    for a in all_areas:
        count = len(grouped[a["slug"]])
        bar = "█" * min(count, 20)
        tag = " 🆕" if a.get("auto") else ""
        print(f"  {a['name']:6s} {count:3d}套 {bar}{tag}")

    print(f"\n🔨 开始生成页面...\n")

    # 1. 生成主门户
    build_index(all_areas, grouped)

    # 2. 生成每个区域页面
    print()
    for a in all_areas:
        build_area_page(all_areas, a, grouped[a["slug"]])

    # 3. 生成 sitemap
    print()
    build_sitemap(all_areas, grouped)

    print(f"\n{'=' * 60}")
    print(f"🎉 全部完成！共生成 {1 + len(all_areas)} 个 HTML 页面 + 1 个 sitemap.xml")
    print(f"   主门户: index.html")
    for a in all_areas:
        tag = " 🆕(自动)" if a.get("auto") else ""
        print(f"   区域页: {a['slug']}.html ({a['name']}{tag})")
    print(f"   站点地图: sitemap.xml")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
