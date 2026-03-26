"""
清空内容数据脚本（保留知识库分组）

清空：
- files 表（文件列表）
- retrieval_test_history 表（召回测试历史）
- 向量数据库 (vector_db)
- 知识图谱 (graph)
- 关键字索引 (keyword_index)
- 上传文件 (upload)

保留：
- knowledge_bases 表（知识库分组）
- skill_cards 表（技能卡片）
"""
import os
import sqlite3
import shutil
from pathlib import Path

# 数据目录
DATA_DIR = Path(__file__).parent / 'data'
DB_PATH = DATA_DIR / 'rag.db'

print("=" * 60)
print("清空内容数据（保留知识库分组和技能卡片）")
print("=" * 60)

# 1. 清空数据库中的文件相关表
if DB_PATH.exists():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 清空 files 表
    cursor.execute('DELETE FROM files')
    files_count = cursor.rowcount
    print(f"  [清空] files 表: {files_count} 条记录")

    # 清空 retrieval_test_history 表
    cursor.execute('DELETE FROM retrieval_test_history')
    history_count = cursor.rowcount
    print(f"  [清空] retrieval_test_history 表: {history_count} 条记录")

    # 保留 knowledge_bases 和 skill_cards
    cursor.execute('SELECT COUNT(*) FROM knowledge_bases')
    kb_count = cursor.fetchone()[0]
    print(f"  [保留] knowledge_bases 表: {kb_count} 条记录")

    cursor.execute('SELECT COUNT(*) FROM skill_cards')
    skill_count = cursor.fetchone()[0]
    print(f"  [保留] skill_cards 表: {skill_count} 条记录")

    conn.commit()
    conn.close()
else:
    print(f"  [跳过] 数据库文件不存在: {DB_PATH}")

# 2. 删除向量数据库
vector_db_path = DATA_DIR / 'vector_db'
if vector_db_path.exists():
    shutil.rmtree(vector_db_path)
    print(f"  [删除] vector_db 目录")
else:
    print(f"  [跳过] vector_db 目录不存在")

# 3. 删除知识图谱
graph_path = DATA_DIR / 'graph'
if graph_path.exists():
    shutil.rmtree(graph_path)
    print(f"  [删除] graph 目录")
else:
    print(f"  [跳过] graph 目录不存在")

# 4. 删除关键字索引
keyword_index_path = DATA_DIR / 'keyword_index'
if keyword_index_path.exists():
    shutil.rmtree(keyword_index_path)
    print(f"  [删除] keyword_index 目录")
else:
    print(f"  [跳过] keyword_index 目录不存在")

# 5. 清空上传文件目录
upload_path = DATA_DIR / 'upload'
if upload_path.exists():
    for item in upload_path.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)
    print(f"  [清空] upload 目录")
else:
    print(f"  [跳过] upload 目录不存在")

# 6. 重新创建必要的目录结构
for dir_name in ['vector_db', 'graph', 'keyword_index', 'upload']:
    (DATA_DIR / dir_name).mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("清空完成！")
print("=" * 60)
