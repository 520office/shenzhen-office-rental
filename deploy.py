#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deploy.py — 一键部署脚本
1. 检测 Downloads 目录中最新的 projects.json
2. 恢复 id 字段（admin 导出会去掉 id）
3. 展示数据变更摘要
4. 运行 build_pages.py 生成静态页面
5. 更新 admin.html 的 EMBEDDED_DATA
6. git commit（不 push，push 需手动）
"""

import json
import os
import re
import sys
import subprocess
import datetime
import glob
from pathlib import Path

# Windows 编码修复
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# === 配置 ===
SCRIPT_DIR = Path(__file__).parent.resolve()
DOWNLOADS_DIR = Path.home() / "Downloads"
PROJECT_FILE = SCRIPT_DIR / "projects.json"
ADMIN_FILE = SCRIPT_DIR / "admin.html"
PYTHON_EXE = sys.executable  # 当前 Python 解释器


def find_latest_export():
    """在 Downloads 目录找最新的 projects.json"""
    candidates = list(DOWNLOADS_DIR.glob("projects*.json"))
    if not candidates:
        print("❌ 没找到导出的 projects.json")
        print(f"   请确认文件在: {DOWNLOADS_DIR}")
        return None
    
    # 按修改时间排序，取最新
    candidates.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    latest = candidates[0]
    mtime = datetime.datetime.fromtimestamp(latest.stat().st_mtime)
    
    if len(candidates) > 1:
        print(f"📁 找到 {len(candidates)} 个文件，取最新的: {latest.name}")
    print(f"   修改时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   文件大小: {latest.stat().st_size:,} 字节")
    
    return latest


def restore_ids(current_data, new_data):
    """恢复 id 字段 — 按位置匹配（admin 导出不改变顺序）"""
    current_ids = [d.get("id", i + 1) for i, d in enumerate(current_data)]
    
    for i, d in enumerate(new_data):
        if i < len(current_ids):
            d["id"] = current_ids[i]
        else:
            d["id"] = max(current_ids) + (i - len(current_ids)) + 1
    
    return new_data


def find_changes(old_data, new_data):
    """对比找出实际数据变更"""
    old_map = {}
    for d in old_data:
        sid = d.get("id", "")
        old_map[sid] = d
    
    new_map = {}
    for d in new_data:
        sid = d.get("id", "")
        new_map[sid] = d
    
    added = [d for sid, d in new_map.items() if sid not in old_map]
    removed = [d for sid, d in old_map.items() if sid not in new_map]
    
    modified = []
    for sid, new_d in new_map.items():
        if sid in old_map:
            old_d = old_map[sid]
            changed = {}
            for key in ["name", "area", "location", "size", "price", "decoration", "floor", "image"]:
                if old_d.get(key) != new_d.get(key):
                    changed[key] = (old_d.get(key, ""), new_d.get(key, ""))
            if changed:
                modified.append({"id": sid, "name": new_d.get("name", ""), "changes": changed})
    
    return added, removed, modified


def update_admin_html(data):
    """更新 admin.html 中的 EMBEDDED_DATA"""
    with open(ADMIN_FILE, "r", encoding="utf-8") as f:
        html = f.read()
    
    new_line = "var EMBEDDED_DATA = " + json.dumps(data, ensure_ascii=False) + ";"
    html = re.sub(r"var EMBEDDED_DATA = \[.*?\];", new_line, html, count=1, flags=re.DOTALL)
    
    with open(ADMIN_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ admin.html 已更新，嵌入 {len(data)} 条数据")


def run_build():
    """运行 build_pages.py"""
    print("🔨 运行 build_pages.py...")
    build_script = SCRIPT_DIR / "build_pages.py"
    result = subprocess.run(
        [sys.executable, str(build_script)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(SCRIPT_DIR)
    )
    if result.returncode != 0:
        print("❌ build_pages.py 执行失败:")
        print(result.stderr)
        return False
    return True


def git_commit(msg):
    """Git add + commit"""
    files = ["admin.html", "projects.json"]
    
    # 添加所有生成的 HTML 页面
    html_files = list(SCRIPT_DIR.glob("*.html"))
    for f in html_files:
        if f.name != "admin.html":
            files.append(f.name)
    # sitemap
    if (SCRIPT_DIR / "sitemap.xml").exists():
        files.append("sitemap.xml")
    
    print(f"📦 git add {' '.join(files[:5])}...")
    subprocess.run(["git", "add"] + files, cwd=str(SCRIPT_DIR), check=True)
    
    print(f"📝 git commit -m \"{msg}\"")
    subprocess.run(["git", "commit", "-m", msg], cwd=str(SCRIPT_DIR), check=True)
    print("✅ 已提交")


def main():
    print("=" * 60)
    print("🚀 深圳办公室出租 - 一键部署")
    print(f"📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    # 1. 找导出文件
    export_file = find_latest_export()
    if not export_file:
        input("\n按任意键退出...")
        sys.exit(1)
    
    print()
    
    # 2. 加载新旧数据
    with open(PROJECT_FILE, "r", encoding="utf-8") as f:
        old_data = json.load(f)
    with open(export_file, "r", encoding="utf-8") as f:
        new_data = json.load(f)
    
    print(f"📊 当前数据: {len(old_data)} 条")
    print(f"📊 导出数据: {len(new_data)} 条")
    
    # 3. 恢复 ID
    new_data = restore_ids(old_data, new_data)
    
    # 4. 对比变更
    added, removed, modified = find_changes(old_data, new_data)
    
    total_changes = len(added) + len(removed) + len(modified)
    
    if added:
        print(f"\n➕ 新增 {len(added)} 条:")
        for d in added:
            print(f"   [{d.get('id', '?')}] {d.get('name', '?')[:25]:25s} | {d.get('size', '?'):>6s}㎡ | {d.get('price', '?')}")
    
    if removed:
        print(f"\n➖ 删除 {len(removed)} 条:")
        for d in removed:
            print(f"   [{d.get('id', '?')}] {d.get('name', '?')[:25]:25s}")
    
    if modified:
        print(f"\n✏️  修改 {len(modified)} 处:")
        for m in modified:
            print(f"   [{m['id']}] {m['name'][:25]:25s}:")
            for field, (old, new) in m["changes"].items():
                if field == "price":
                    print(f"       💰 {field}: {old} → {new}")
                elif field == "image":
                    print(f"       🖼️  {field}: {'有图→有图' if old and new else '图变更'}")
                else:
                    print(f"       📋 {field}: {old} → {new}")
    
    if total_changes == 0:
        print("\n😴 无数据变更，无需部署")
        return
    
    print()
    
    # 5. 确认
    resp = input("⚠️  确认部署以上变更？[Y/n] ").strip().lower()
    if resp and resp not in ("y", "yes", "是", "ok"):
        print("已取消")
        return
    
    # 6. 保存
    with open(PROJECT_FILE, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    print("✅ projects.json 已更新")
    
    # 7. 构建
    if not run_build():
        input("\n按任意键退出...")
        sys.exit(1)
    
    # 8. 更新 admin.html
    update_admin_html(new_data)
    
    # 9. Commit
    print()
    msg_parts = []
    if added:
        names = ", ".join(d.get("name", "?")[:15] for d in added[:3])
        if len(added) > 3:
            names += f"+{len(added)-3}"
        msg_parts.append(f"新增{len(added)}条: {names}")
    if removed:
        msg_parts.append(f"删除{len(removed)}条")
    if modified:
        fields = set()
        for m in modified:
            fields.update(m["changes"].keys())
        if "price" in fields:
            price_count = sum(1 for m in modified if "price" in m["changes"])
            msg_parts.append(f"修正{price_count}条价格")
        else:
            msg_parts.append(f"更新{len(modified)}条")
    
    commit_msg = "; ".join(msg_parts) if msg_parts else "数据更新"
    print()
    git_commit(commit_msg)
    
    print()
    print("=" * 60)
    print("🎉 部署完成！")
    print()
    print("⚠️  最后一步：手动 git push")
    print("=" * 60)
    
    input("\n按任意键退出...")


if __name__ == "__main__":
    main()
