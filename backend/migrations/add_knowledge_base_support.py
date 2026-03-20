"""
数据库迁移脚本：添加知识库支持

此脚本将：
1. 创建 knowledge_bases 表
2. 为 files 表添加 kb_id 字段

执行方法：
    cd backend
    python migrations/add_knowledge_base_support.py
"""

import sqlite3
import sys
from pathlib import Path


def get_db_path():
    """获取数据库路径"""
    # 尝试从环境变量获取
    import os
    env_db_path = os.getenv('DATABASE_PATH')
    if env_db_path:
        return env_db_path

    # 默认路径
    script_dir = Path(__file__).parent.parent
    db_path = script_dir / 'data' / 'rag.db'
    return str(db_path)


def migrate():
    """执行迁移"""
    db_path = get_db_path()

    # 检查数据库文件是否存在
    if not Path(db_path).exists():
        print(f"错误：数据库文件不存在: {db_path}")
        print("请先启动应用创建数据库，或检查路径是否正确。")
        return False

    print(f"正在迁移数据库: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. 创建 knowledge_bases 表
        print("正在创建 knowledge_bases 表...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        print("✓ knowledge_bases 表已创建")

        # 2. 检查 files 表是否有 kb_id 字段
        cursor.execute("PRAGMA table_info(files)")
        columns = [column[1] for column in cursor.fetchall()]
        has_kb_id = 'kb_id' in columns

        if not has_kb_id:
            print("正在为 files 表添加 kb_id 字段...")
            # SQLite 的 ALTER TABLE 只能添加列到末尾
            cursor.execute("ALTER TABLE files ADD COLUMN kb_id TEXT")
            print("✓ kb_id 字段已添加到 files 表")
        else:
            print("✓ files 表已有 kb_id 字段，跳过")

        # 3. 验证迁移结果
        print("\n验证迁移结果:")

        # 检查 knowledge_bases 表
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_bases'"
        )
        if cursor.fetchone():
            print("✓ knowledge_bases 表已存在")
        else:
            print("✗ knowledge_bases 表创建失败")
            return False

        # 检查 files 表结构
        cursor.execute("PRAGMA table_info(files)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'kb_id' in columns:
            print("✓ files 表包含 kb_id 字段")
        else:
            print("✗ files 表缺少 kb_id 字段")
            return False

        conn.commit()
        conn.close()

        print("\n✓ 迁移完成！")
        return True

    except sqlite3.Error as e:
        print(f"\n✗ 迁移失败: {e}")
        return False


def rollback():
    """回滚迁移"""
    db_path = get_db_path()
    print(f"正在回滚数据库: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 删除 knowledge_bases 表
        print("正在删除 knowledge_bases 表...")
        cursor.execute("DROP TABLE IF EXISTS knowledge_bases")
        print("✓ knowledge_bases 表已删除")

        # 注意：SQLite 不支持删除列，所以 kb_id 字段会保留
        # 如果需要删除，需要重建表
        print("注意：kb_id 字段会保留（SQLite 不支持删除列）")

        conn.commit()
        conn.close()

        print("\n✓ 回滚完成！")
        return True

    except sqlite3.Error as e:
        print(f"\n✗ 回滚失败: {e}")
        return False


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        success = rollback()
    else:
        success = migrate()

    sys.exit(0 if success else 1)
