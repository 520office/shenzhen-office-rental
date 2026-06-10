#!/usr/bin/env python3
"""更新 admin.html 中的 DEFAULT_DATA"""
import json
import re
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 读取最新的 projects.json
with open(os.path.join(SCRIPT_DIR, "projects.json"), "r", encoding="utf-8") as f:
    projects = json.load(f)

print(f"projects.json: {len(projects)} 条")

# 读取 admin.html
admin_path = os.path.join(SCRIPT_DIR, "admin.html")
with open(admin_path, "r", encoding="utf-8") as f:
    content = f.read()

# 新的 DEFAULT_DATA JSON（紧凑格式，保持和原格式一致）
new_data_json = json.dumps(projects, ensure_ascii=False, indent=2)
new_block = f"const DEFAULT_DATA = {new_data_json};"

# 替换 DEFAULT_DATA 块
pattern = r"const DEFAULT_DATA = \[.*?\];"
new_content = re.sub(pattern, new_block, content, count=1, flags=re.DOTALL)

if new_content == content:
    print("⚠ 未找到 DEFAULT_DATA 块，未做修改")
else:
    with open(admin_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"✅ admin.html 已更新，DEFAULT_DATA 现在包含 {len(projects)} 条记录")
