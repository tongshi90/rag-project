"""
清空所有数据脚本

清空：
- SQLite 数据库 (rag.db)
- 向量数据库 (vector_db)
- 知识图谱 (graph)
- 关键字索引 (keyword_index)
- 上传文件 (upload)
"""
import os
import shutil
from pathlib import Path

# 数据目录
DATA_DIR = Path(__file__).parent / 'data'

# 需要删除的文件/目录
ITEMS_TO_DELETE = [
    'rag.db',
    'vector_db',
    'graph',
    'keyword_index',
]

print("开始清空数据...")
print(f"数据目录: {DATA_DIR}")

# 删除指定文件/目录
for item in ITEMS_TO_DELETE:
    item_path = DATA_DIR / item
    if item_path.exists():
        if item_path.is_file():
            item_path.unlink()
            print(f"  [删除文件] {item}")
        elif item_path.is_dir():
            shutil.rmtree(item_path)
            print(f"  [删除目录] {item}")
    else:
        print(f"  [跳过] {item} (不存在)")

# 清空 upload 目录（保留目录）
upload_dir = DATA_DIR / 'upload'
if upload_dir.exists():
    for file in upload_dir.iterdir():
        if file.is_file():
            file.unlink()
        elif file.is_dir():
            shutil.rmtree(file)
    print(f"  [清空目录] upload")

# 确保目录结构存在
for dir_name in ['vector_db', 'graph', 'keyword_index', 'upload']:
    (DATA_DIR / dir_name).mkdir(parents=True, exist_ok=True)

print("\n数据清空完成！")
print(f"当前 data 目录内容:")
for item in DATA_DIR.iterdir():
    print(f"  - {item.name}")
