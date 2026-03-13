"""
Skill Card Model for SQLite Database
"""
from datetime import datetime
import sqlite3
import os
from pathlib import Path

from app.config.paths import get_db_path


class SkillCard:
    """Skill card model representing skills in the system"""

    def __init__(self, id=None, title=None, description=None,
                 skill_code=None, published=False, created_at=None, updated_at=None):
        self.id = id
        self.title = title
        self.description = description
        self.skill_code = skill_code
        self.published = published
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'skillCode': self.skill_code,
            'published': self.published,
            'createdAt': self.created_at,
            'updatedAt': self.updated_at,
        }


class SkillCardDatabase:
    """Database manager for skill cards"""

    def __init__(self, db_path: str = None):
        """
        Initialize database

        Args:
            db_path: Database path, uses default if None
        """
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
        """Initialize database and create skill_cards table"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_cards (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                skill_code TEXT,
                published INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 检查并添加缺失的字段（兼容性处理）
        cursor.execute('''
            SELECT COUNT(*) as column_exists
            FROM pragma_table_info('skill_cards')
            WHERE name='published'
        ''')
        result = cursor.fetchone()

        if result and result[0] == 0:
            cursor.execute('ALTER TABLE skill_cards ADD COLUMN published INTEGER DEFAULT 0')

        # 检查是否有 skill_code 字段，如果有 api_code 但没有 skill_code，则重命名
        cursor.execute('''
            SELECT COUNT(*) as column_exists
            FROM pragma_table_info('skill_cards')
            WHERE name='skill_code'
        ''')
        skill_code_exists = cursor.fetchone()[0]

        if skill_code_exists == 0:
            cursor.execute('''
                SELECT COUNT(*) as column_exists
                FROM pragma_table_info('skill_cards')
                WHERE name='api_code'
            ''')
            api_code_exists = cursor.fetchone()[0]

            if api_code_exists > 0:
                # 重命名 api_code 为 skill_code
                cursor.execute('ALTER TABLE skill_cards RENAME COLUMN api_code TO skill_code')
            else:
                # 添加 skill_code 字段
                cursor.execute('ALTER TABLE skill_cards ADD COLUMN skill_code TEXT')

        conn.commit()
        conn.close()

    def insert_skill_card(self, skill_card):
        """Insert a new skill card"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO skill_cards (id, title, description, skill_code, published)
            VALUES (?, ?, ?, ?, ?)
        ''', (skill_card.id, skill_card.title, skill_card.description, skill_card.skill_code, 1 if skill_card.published else 0))

        conn.commit()
        conn.close()

    def get_all_skill_cards(self):
        """Get all skill cards ordered by created_at desc"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, title, description, skill_code, published, created_at, updated_at
            FROM skill_cards
            ORDER BY created_at DESC
        ''')

        rows = cursor.fetchall()
        conn.close()

        skill_cards = []
        for row in rows:
            skill_cards.append({
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'skillCode': row['skill_code'],
                'published': bool(row['published']),
                'createdAt': row['created_at'],
                'updatedAt': row['updated_at'],
            })

        return skill_cards

    def search_skill_cards(self, keyword):
        """Search skill cards by title or description"""
        conn = self.get_connection()
        cursor = conn.cursor()

        search_pattern = f'%{keyword}%'
        cursor.execute('''
            SELECT id, title, description, skill_code, published, created_at, updated_at
            FROM skill_cards
            WHERE title LIKE ? OR description LIKE ?
            ORDER BY created_at DESC
        ''', (search_pattern, search_pattern))

        rows = cursor.fetchall()
        conn.close()

        skill_cards = []
        for row in rows:
            skill_cards.append({
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'skillCode': row['skill_code'],
                'published': bool(row['published']),
                'createdAt': row['created_at'],
                'updatedAt': row['updated_at'],
            })

        return skill_cards

    def get_skill_card_by_id(self, card_id):
        """Get a skill card by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, title, description, skill_code, published, created_at, updated_at
            FROM skill_cards
            WHERE id = ?
        ''', (card_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return SkillCard(
                id=row['id'],
                title=row['title'],
                description=row['description'],
                skill_code=row['skill_code'],
                published=bool(row['published']),
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
        return None

    def get_skill_card_by_code(self, skill_code):
        """Get a skill card by skill code (case-insensitive)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, title, description, skill_code, published, created_at, updated_at
            FROM skill_cards
            WHERE skill_code COLLATE NOCASE = ?
        ''', (skill_code,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return SkillCard(
                id=row['id'],
                title=row['title'],
                description=row['description'],
                skill_code=row['skill_code'],
                published=bool(row['published']),
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
        return None

    def is_skill_code_exists(self, skill_code, exclude_id=None):
        """Check if skill code already exists (case-insensitive)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if exclude_id:
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM skill_cards
                WHERE skill_code COLLATE NOCASE = ? AND id != ?
            ''', (skill_code, exclude_id))
        else:
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM skill_cards
                WHERE skill_code COLLATE NOCASE = ?
            ''', (skill_code,))

        count = cursor.fetchone()[0]
        conn.close()

        return count > 0

    def update_skill_card(self, card_id, title=None, description=None, skill_code=None, published=None):
        """Update a skill card"""
        conn = self.get_connection()
        cursor = conn.cursor()

        updates = []
        params = []

        if title is not None:
            updates.append('title = ?')
            params.append(title)
        if description is not None:
            updates.append('description = ?')
            params.append(description)
        if skill_code is not None:
            updates.append('skill_code = ?')
            params.append(skill_code)
        if published is not None:
            updates.append('published = ?')
            params.append(1 if published else 0)

        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(card_id)

        cursor.execute(f'''
            UPDATE skill_cards
            SET {', '.join(updates)}
            WHERE id = ?
        ''', params)

        conn.commit()
        conn.close()

    def delete_skill_card(self, card_id):
        """Delete a skill card by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM skill_cards WHERE id = ?', (card_id,))
        conn.commit()
        conn.close()

    def delete_all_skill_cards(self):
        """Delete all skill cards"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM skill_cards')
        conn.commit()
        conn.close()


# Global database instance
skill_card_db = SkillCardDatabase()
