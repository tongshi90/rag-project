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
                 upload_time=None, status='completed', file_path=None, kb_id=None):
        self.id = id
        self.name = name
        self.size = size
        self.file_type = file_type
        self.upload_time = upload_time
        self.status = status
        self.file_path = file_path
        self.kb_id = kb_id

    def to_dict(self):
        """Convert model to dictionary"""
        result = {
            'id': self.id,
            'name': self.name,
            'size': self.size,
            'type': self.file_type,
            'uploadTime': self.upload_time,
            'status': self.status,
        }
        if self.kb_id is not None:
            result['kbId'] = self.kb_id
        return result


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
                kb_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 为已存在的表添加 kb_id 列（如果不存在）
        cursor.execute('PRAGMA table_info(files)')
        columns = [column['name'] for column in cursor.fetchall()]
        if 'kb_id' not in columns:
            cursor.execute('ALTER TABLE files ADD COLUMN kb_id TEXT')

        conn.commit()
        conn.close()

    def insert_file(self, file):
        """Insert a new file record"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check which columns exist
        cursor.execute('PRAGMA table_info(files)')
        columns = [column['name'] for column in cursor.fetchall()]
        has_kb_id = 'kb_id' in columns

        if has_kb_id:
            # New version with kb_id support
            cursor.execute('''
                INSERT INTO files (id, name, size, file_type, upload_time, status, file_path, kb_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (file.id, file.name, file.size, file.file_type, file.upload_time, file.status, file.file_path, file.kb_id))
        else:
            # Oldest version without kb_id
            cursor.execute('''
                INSERT INTO files (id, name, size, file_type, upload_time, status, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (file.id, file.name, file.size, file.file_type, file.upload_time, file.status, file.file_path))

        conn.commit()
        conn.close()

    def get_all_files(self, kb_id: str = None):
        """
        Get all files ordered by upload time desc

        Args:
            kb_id: If provided, only return files in this knowledge base.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check which columns exist
        cursor.execute('PRAGMA table_info(files)')
        columns = [column['name'] for column in cursor.fetchall()]
        has_kb_id = 'kb_id' in columns

        # Build query based on available columns and filters
        select_fields = ['id', 'name', 'size', 'file_type', 'upload_time', 'status']
        if has_kb_id:
            select_fields.append('kb_id')

        select_clause = ', '.join(select_fields)
        where_clauses = []
        params = []

        if kb_id is not None and has_kb_id:
            where_clauses.append('kb_id = ?')
            params.append(kb_id)

        where_clause = 'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''

        query = f'''
            SELECT {select_clause}
            FROM files
            {where_clause}
            ORDER BY created_at DESC
        '''

        cursor.execute(query, tuple(params) if params else ())

        rows = cursor.fetchall()
        conn.close()

        files = []
        for row in rows:
            file_data = {
                'id': row['id'],
                'name': row['name'],
                'size': row['size'],
                'type': row['file_type'],
                'uploadTime': row['upload_time'],
                'status': row['status'],
            }
            if has_kb_id:
                file_data['kbId'] = row['kb_id']
            files.append(file_data)

        return files

    def get_file_by_id(self, file_id):
        """Get a file by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check which columns exist
        cursor.execute('PRAGMA table_info(files)')
        columns = [column['name'] for column in cursor.fetchall()]
        has_kb_id = 'kb_id' in columns

        select_fields = ['id', 'name', 'size', 'file_type', 'upload_time', 'status', 'file_path']
        if has_kb_id:
            select_fields.append('kb_id')

        query = f"SELECT {', '.join(select_fields)} FROM files WHERE id = ?"
        cursor.execute(query, (file_id,))

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
                file_path=row['file_path'],
                kb_id=row['kb_id'] if has_kb_id else None
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

    def get_files_by_kb_id(self, kb_id: str):
        """Get files by knowledge base ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if kb_id column exists
        cursor.execute('PRAGMA table_info(files)')
        columns = [column['name'] for column in cursor.fetchall()]
        has_kb_id = 'kb_id' in columns

        if has_kb_id:
            cursor.execute('''
                SELECT id, name, size, file_type, upload_time, status
                FROM files
                WHERE kb_id = ?
                ORDER BY created_at DESC
            ''', (kb_id,))

            rows = cursor.fetchall()
            conn.close()

            files = []
            for row in rows:
                file_data = {
                    'id': row['id'],
                    'name': row['name'],
                    'size': row['size'],
                    'type': row['file_type'],
                    'uploadTime': row['upload_time'],
                    'status': row['status'],
                }
                files.append(file_data)

            return files
        else:
            conn.close()
            return []

    def delete_files_by_kb_id(self, kb_id: str):
        """Delete all files in a knowledge base and return their IDs"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Check if kb_id column exists
        cursor.execute('PRAGMA table_info(files)')
        columns = [column['name'] for column in cursor.fetchall()]
        has_kb_id = 'kb_id' in columns

        if has_kb_id:
            # Get file IDs before deleting
            cursor.execute('SELECT id FROM files WHERE kb_id = ?', (kb_id,))
            file_ids = [row[0] for row in cursor.fetchall()]

            # Delete records
            cursor.execute('DELETE FROM files WHERE kb_id = ?', (kb_id,))
            conn.commit()
            conn.close()
            return file_ids
        else:
            conn.close()
            return []


# Global database instance
db = Database()
