"""
File Model for SQLite Database
"""
from datetime import datetime
import sqlite3
import os
from pathlib import Path

from app.config.paths import get_db_path


class File:
    """File model representing uploaded files"""

    def __init__(self, id=None, name=None, size=None, file_type=None,
                 upload_time=None, status='completed', file_path=None):
        self.id = id
        self.name = name
        self.size = size
        self.file_type = file_type
        self.upload_time = upload_time
        self.status = status
        self.file_path = file_path

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'size': self.size,
            'type': self.file_type,
            'uploadTime': self.upload_time,
            'status': self.status,
        }


class Database:
    """Database manager for file storage"""

    def __init__(self, db_path: str = None):
        """
        初始化数据库

        Args:
            db_path: 数据库路径，如果为 None 则使用默认路径
                    支持相对路径或绝对路径
                    环境变量 DATABASE_PATH 可覆盖默认路径
        """
        # 优先使用环境变量，其次使用传入路径，最后使用默认路径
        env_db_path = os.getenv('DATABASE_PATH')

        if env_db_path:
            # 环境变量优先级最高（Docker 部署时使用）
            self.db_path = env_db_path
        elif db_path:
            # 使用传入的路径
            self.db_path = db_path
        else:
            # 使用默认路径（从 config.paths 获取）
            self.db_path = get_db_path()

        self.init_db()

    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database and create tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                size INTEGER NOT NULL,
                file_type TEXT NOT NULL,
                upload_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'completed',
                file_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def insert_file(self, file):
        """Insert a new file record"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO files (id, name, size, file_type, upload_time, status, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (file.id, file.name, file.size, file.file_type, file.upload_time, file.status, file.file_path))

        conn.commit()
        conn.close()

    def get_all_files(self):
        """Get all files ordered by upload time desc"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, size, file_type, upload_time, status
            FROM files
            ORDER BY created_at DESC
        ''')

        rows = cursor.fetchall()
        conn.close()

        files = []
        for row in rows:
            files.append({
                'id': row['id'],
                'name': row['name'],
                'size': row['size'],
                'type': row['file_type'],
                'uploadTime': row['upload_time'],
                'status': row['status'],
            })

        return files

    def get_file_by_id(self, file_id):
        """Get a file by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, size, file_type, upload_time, status, file_path
            FROM files
            WHERE id = ?
        ''', (file_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return File(
                id=row['id'],
                name=row['name'],
                size=row['size'],
                file_type=row['file_type'],
                upload_time=row['upload_time'],
                status=row['status'],
                file_path=row['file_path']
            )
        return None

    def delete_file(self, file_id):
        """Delete a file by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
        conn.commit()
        conn.close()

    def delete_all_files(self):
        """Delete all files and return their file paths"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get all file paths before deleting
        cursor.execute('SELECT file_path FROM files')
        file_paths = [row[0] for row in cursor.fetchall()]

        # Delete all records
        cursor.execute('DELETE FROM files')
        conn.commit()
        conn.close()

        return file_paths

    def update_file_status(self, file_id: str, status: str):
        """Update file parsing status"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('UPDATE files SET status = ? WHERE id = ?', (status, file_id))
        conn.commit()
        conn.close()


# Global database instance
db = Database()
