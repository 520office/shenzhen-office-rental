import json
import re

with open('projects.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

fix_log = []

for rec in data:
    # ===== Issue 1: Missing location =====
    if not rec.get('location', '').strip():
        area = rec.get('area', '')
        # 从 area 提取区位信息
        if '前海' in area or '南山' in area:
            rec['location'] = '南山-前海'
        elif '宝安' in area:
            rec['location'] = '宝安中心'
        elif '西乡' in area:
            rec['location'] = '西乡'
        elif '福永' in area:
            rec['location'] = '福永'
        else:
            rec['location'] = area
        fix_log.append(f"补区位: {rec['name'][:20]} → {rec['location']}")

    # ===== Issue 3: 元/月 → 元/㎡/月 =====
    price = rec.get('price', '')
    if price and '元/月' in price and '元/㎡/月' not in price and '元/m²/月' not in price:
        m = re.search(r'([\d.]+)\s*元/月', price)
        if m:
            monthly_total = float(m.group(1))
            size_str = rec.get('size', '')
            # 从面积提取数字
            sm = re.search(r'([\d.]+)', size_str)
            if sm:
                size = float(sm.group(1))
                if size > 0:
                    per_sqm = round(monthly_total / size)
                    old_price = rec['price']
                    rec['price'] = f"{per_sqm}元/㎡/月"
                    fix_log.append(f"改价格: {rec['name'][:20]} | {old_price}({size_str}) → {rec['price']}")

with open('projects.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

for line in fix_log:
    print(line)

print(f"\n共修复 {len(fix_log)} 处")
