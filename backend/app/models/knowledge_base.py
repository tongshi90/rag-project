"""
Knowledge Base Model for SQLite Database
"""
from datetime import datetime
import sqlite3
import os
from pathlib import Path

from app.config.paths import get_db_path


class KnowledgeBase:
    """Knowledge Base model representing a RAG knowledge base"""

    def __init__(self, id=None, name=None, description=None,
                 created_at=None, updated_at=None):
        self.id = id
        self.name = name
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'createdAt': self.created_at,
            'updatedAt': self.updated_at,
        }


class KnowledgeBaseDatabase:
    """Database manager for knowledge base storage"""

    def __init__(self, db_path: str = None):
        """
        初始化数据库

        Args:
            db_path: 数据库路径，如果为 None 则使用默认路径
        """
        # 优先使用环境变量，其次使用传入路径，最后使用默认路径
        env_db_path = os.getenv('DATABASE_PATH')

        if env_db_path:
            self.db_path = env_db_path
        elif db_path:
            self.db_path = db_path
        else:
            self.db_path = get_db_path()

        self.init_db()

    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database and create knowledge_bases table"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()

    def insert_knowledge_base(self, kb: KnowledgeBase):
        """Insert a new knowledge base"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO knowledge_bases (id, name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (kb.id, kb.name, kb.description, kb.created_at, kb.updated_at))

        conn.commit()
        conn.close()

    def get_all_knowledge_bases(self):
        """Get all knowledge bases ordered by created_at desc"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, description, created_at, updated_at
            FROM knowledge_bases
            ORDER BY created_at DESC
        ''')

        rows = cursor.fetchall()
        conn.close()

        kbs = []
        for row in rows:
            kb = {
                'id': row['id'],
                'name': row['name'],
                'description': row['description'],
                'createdAt': row['created_at'],
                'updatedAt': row['updated_at'],
            }
            kbs.append(kb)

        return kbs

    def get_knowledge_base_by_id(self, kb_id):
        """Get a knowledge base by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, description, created_at, updated_at
            FROM knowledge_bases
            WHERE id = ?
        ''', (kb_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return KnowledgeBase(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
        return None

    def update_knowledge_base(self, kb_id, name=None, description=None):
        """Update knowledge base"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if name and description:
            cursor.execute('''
                UPDATE knowledge_bases
                SET name = ?, description = ?, updated_at = ?
                WHERE id = ?
            ''', (name, description, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), kb_id))
        elif name:
            cursor.execute('''
                UPDATE knowledge_bases
                SET name = ?, updated_at = ?
                WHERE id = ?
            ''', (name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), kb_id))
        elif description:
            cursor.execute('''
                UPDATE knowledge_bases
                SET description = ?, updated_at = ?
                WHERE id = ?
            ''', (description, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), kb_id))

        conn.commit()
        conn.close()

    def delete_knowledge_base(self, kb_id):
        """Delete a knowledge base by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM knowledge_bases WHERE id = ?', (kb_id,))
        conn.commit()
        conn.close()

    def get_knowledge_base_file_count(self, kb_id):
        """Get the number of files in a knowledge base"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if kb_id column exists in files table
        cursor.execute('PRAGMA table_info(files)')
        columns = [column['name'] for column in cursor.fetchall()]
        has_kb_id = 'kb_id' in columns

        if has_kb_id:
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM files
                WHERE kb_id = ?
            ''', (kb_id,))
            row = cursor.fetchone()
            count = row['count'] if row else 0
        else:
            count = 0

        conn.close()
        return count


# Global database instance
knowledge_base_db = KnowledgeBaseDatabase()
