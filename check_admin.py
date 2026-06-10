import json

# 读取 admin.html
with open('admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 DEFAULT_DATA 的位置
start_marker = 'const DEFAULT_DATA = ['
start_idx = content.find(start_marker)
if start_idx == -1:
    print('ERROR: 找不到 DEFAULT_DATA')
    exit(1)

# 找到对应的结束位置
rest = content[start_idx + len(start_marker):]
end_idx = rest.find('];')
if end_idx == -1:
    print('ERROR: 找不到结束 ];')
    exit(1)

end_idx_absolute = start_idx + len(start_marker) + end_idx
print(f'DEFAULT_DATA 位置: {start_idx} -> {end_idx_absolute}')

# 提取 DEFAULT_DATA 内容并解析
default_data_str = content[start_idx:end_idx_absolute + 2]
# 尝试解析 JSON
try:
    # 去掉 "const DEFAULT_DATA = " 前缀
    json_str = default_data_str.replace('const DEFAULT_DATA = ', '')
    data = json.loads(json_str)
    print(f'✅ DEFAULT_DATA 包含 {len(data)} 条数据')
    
    # 检查第一条和最后一条
    if len(data) > 0:
        print(f'第一条: {data[0].get("name", "")} - {data[0].get("area", "")}')
        print(f'最后一条: {data[-1].get("name", "")} - {data[-1].get("area", "")}')
except Exception as e:
    print(f'❌ 解析失败: {e}')
    print(f'前500字符: {default_data_str[:500]}')
