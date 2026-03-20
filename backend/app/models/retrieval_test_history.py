"""
Retrieval Test History Model for SQLite Database
"""
from datetime import datetime
import sqlite3
import os
from pathlib import Path

from app.config.paths import get_db_path


class RetrievalTestHistory:
    """Retrieval Test History model"""

    def __init__(self, id=None, kb_id=None, query=None, timestamp=None):
        self.id = id
        self.kb_id = kb_id
        self.query = query
        self.timestamp = timestamp

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'kbId': self.kb_id,
            'query': self.query,
            'timestamp': self.timestamp,
        }


class RetrievalTestHistoryDatabase:
    """Database manager for retrieval test history"""

    def __init__(self, db_path: str = None):
        """Initialize database"""
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
        """Initialize database and create retrieval_test_history table"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS retrieval_test_history (
                id TEXT PRIMARY KEY,
                kb_id TEXT NOT NULL,
                query TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
            )
        ''')

        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_retrieval_history_kb_id
            ON retrieval_test_history(kb_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_retrieval_history_timestamp
            ON retrieval_test_history(timestamp DESC)
        ''')

        conn.commit()
        conn.close()

    def add_history(self, kb_id: str, query: str) -> RetrievalTestHistory:
        """Add a new retrieval test history record"""
        conn = self.get_connection()
        cursor = conn.cursor()

        history_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('''
            INSERT INTO retrieval_test_history (id, kb_id, query, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (history_id, kb_id, query, timestamp))

        conn.commit()
        conn.close()

        return RetrievalTestHistory(
            id=history_id,
            kb_id=kb_id,
            query=query,
            timestamp=timestamp
        )

    def get_history_by_kb_id(self, kb_id: str, limit: int = None, offset: int = 0):
        """Get retrieval test history for a knowledge base"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = '''
            SELECT id, kb_id, query, timestamp
            FROM retrieval_test_history
            WHERE kb_id = ?
            ORDER BY timestamp DESC
        '''

        if limit:
            query += ' LIMIT ? OFFSET ?'
            cursor.execute(query, (kb_id, limit, offset))
        else:
            cursor.execute(query, (kb_id,))

        rows = cursor.fetchall()
        conn.close()

        histories = []
        for row in rows:
            histories.append({
                'id': row['id'],
                'kbId': row['kb_id'],
                'query': row['query'],
                'timestamp': row['timestamp'],
            })

        return histories

    def get_history_count_by_kb_id(self, kb_id: str) -> int:
        """Get total count of retrieval test history for a knowledge base"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) as count
            FROM retrieval_test_history
            WHERE kb_id = ?
        ''', (kb_id,))

        row = cursor.fetchone()
        conn.close()

        return row['count'] if row else 0

    def delete_history(self, history_id: str) -> bool:
        """Delete a retrieval test history record"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM retrieval_test_history WHERE id = ?', (history_id,))
        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()

        return affected_rows > 0

    def clear_history_by_kb_id(self, kb_id: str) -> int:
        """Clear all retrieval test history for a knowledge base"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM retrieval_test_history WHERE kb_id = ?', (kb_id,))
        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()

        return affected_rows


# Global database instance
retrieval_test_history_db = RetrievalTestHistoryDatabase()
