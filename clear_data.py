#!/usr/bin/env python
"""清理知识库数据脚本"""
import shutil
import sqlite3
import os
import subprocess
import time
from pathlib import Path

def kill_python_processes():
    """停止所有 Python 进程"""
    try:
        result = subprocess.run(['taskkill', '/F', '/IM', 'python.exe'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ 已停止 Python 进程")
            time.sleep(1)  # 等待文件释放
            return True
        else:
            return False
    except Exception as e:
        print(f"停止进程失败: {e}")
        return False

def clear_directory(path: Path):
    """清空目录内容但保留目录本身"""
    if path.exists():
        for item in list(path.iterdir()):  # 使用 list 避免迭代时修改
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            except PermissionError as e:
                print(f"  ! 无法删除 {item.name}: 文件被占用")
                return False
        return True
    return False

def main():
    base = Path('F:/rag_project/backend/data')

    print("=" * 50)
    print("开始清理知识库数据...")
    print("=" * 50)

    # 尝试停止后端服务
    print("\n检查并停止后端服务...")
    kill_python_processes()

    # 1. 清空向量数据库
    print("\n[1/5] 清空向量数据库...")
    vector_db = base / 'vector_db'
    if clear_directory(vector_db):
        print("✓ 向量数据库 (vector_db) 已清空")
    else:
        print("✗ 向量数据库清理失败（可能有进程仍在使用）")

    # 2. 清空知识图谱
    print("\n[2/5] 清空知识图谱...")
    graph = base / 'graph'
    if clear_directory(graph):
        print("✓ 知识图谱 (graph) 已清空")
    else:
        print("✗ 知识图谱清理失败")

    # 3. 清空关键字索引
    print("\n[3/5] 清空关键字索引...")
    keyword_index = base / 'keyword_index'
    if clear_directory(keyword_index):
        print("✓ 关键字索引 (keyword_index) 已清空")
    else:
        print("✗ 关键字索引清理失败")

    # 4. 清空上传文件
    print("\n[4/5] 清空上传文件...")
    upload = base / 'upload'
    if clear_directory(upload):
        print("✓ 上传文件 (upload) 已清空")
    else:
        print("✗ 上传文件清理失败")

    # 5. 清空数据库中的文件记录（保留 skill_cards 和 knowledge_bases）
    print("\n[5/5] 清空数据库文件记录...")
    db_path = base / 'rag.db'
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 删除文件记录
        cursor.execute("DELETE FROM files")
        files_deleted = cursor.rowcount
        print(f"✓ 已删除 {files_deleted} 条文件记录")

        # 删除检索测试历史
        cursor.execute("DELETE FROM retrieval_test_history")
        history_deleted = cursor.rowcount
        print(f"✓ 已删除 {history_deleted} 条检索测试历史记录")

        # 检查保留的数据
        cursor.execute("SELECT COUNT(*) FROM skill_cards")
        skill_count = cursor.fetchone()[0]
        print(f"✓ 保留 {skill_count} 条技能卡片记录")

        cursor.execute("SELECT COUNT(*) FROM knowledge_bases")
        kb_count = cursor.fetchone()[0]
        print(f"✓ 保留 {kb_count} 条知识库分组记录")

        conn.commit()
        conn.close()
    else:
        print("✗ 数据库文件不存在")

    print("\n" + "=" * 50)
    print("清理完成！")
    print("=" * 50)
    print("\n保留的数据:")
    print("  - 技能卡片数据库 (skill_cards)")
    print("  - 知识库分组 (knowledge_bases)")
    print("  - backend/skills/ 文件夹中的所有技能文件")
    print("\n提示: 如果仍有文件被占用，请手动停止后端服务后重试")

if __name__ == '__main__':
    main()
