import json

# 读取 projects.json (109条)
with open('projects.json', 'r', encoding='utf-8') as f:
    new_data = json.load(f)

print(f'projects.json 条数: {len(new_data)}')

# 读取 admin.html
with open('admin.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到 DEFAULT_DATA 的起止行
start_line = None
end_line = None
for i, line in enumerate(lines):
    if 'const DEFAULT_DATA = [' in line:
        start_line = i
    if start_line is not None and line.strip() == '];':
        end_line = i
        break

if start_line is None or end_line is None:
    print(f'ERROR: 找不到 DEFAULT_DATA (start={start_line}, end={end_line})')
    exit(1)

print(f'DEFAULT_DATA 行范围: {start_line+1}-{end_line+1}')

# 生成新的 DEFAULT_DATA 行
new_lines = ['const DEFAULT_DATA = [\n']
for j, d in enumerate(new_data):
    new_lines.append('  ' + json.dumps(d, ensure_ascii=False))
    if j < len(new_data) - 1:
        new_lines.append(',\n')
    else:
        new_lines.append('\n')
new_lines.append('];\n')

# 替换
result_lines = lines[:start_line] + new_lines + lines[end_line+1:]

# 写入
with open('admin.html', 'w', encoding='utf-8') as f:
    f.writelines(result_lines)

print(f'✅ 已更新 admin.html DEFAULT_DATA: {len(new_data)} 条')
