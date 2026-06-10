import json
import random

# 可用的办公楼图片（Unsplash 免费图库）
FALLBACK_IMAGES = [
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1497366216548-37526070297c?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1497366811353-6870744d04b2?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1577495508048-b635879837f1?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1486718448742-163732cd1544?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1554469384-e58fac16e23a?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1464938050520-ef2270bb8ce8?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1503387762-592deb58ef4e?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1497215842964-222b430dc094?w=600&h=400&fit=crop",
    "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=600&h=400&fit=crop",
]

with open('projects.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

fixed = 0
# 使用随机种子保证同一楼盘的图片稳定
random.seed(42)
for rec in data:
    if not rec.get("image"):
        # 根据楼盘名取稳定的随机图片
        idx = hash(rec.get("name", "")) % len(FALLBACK_IMAGES)
        rec["image"] = FALLBACK_IMAGES[abs(idx)]
        fixed += 1

with open('projects.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Fixed {fixed} records with fallback images")
print(f"Total records: {len(data)}")
