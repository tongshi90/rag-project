# RAG知识库功能 - 数据库迁移指南

本文档描述如何将现有数据库升级以支持知识库功能。

## 迁移内容

1. **创建 knowledge_bases 表** - 存储知识库信息
2. **为 files 表添加 kb_id 字段** - 关联文件到知识库

## 方法一：自动迁移（推荐）

应用启动时会自动检测并处理数据库结构的兼容性，无需手动执行迁移。

**注意**：应用会自动创建 `knowledge_bases` 表，但 `kb_id` 字段需要手动添加（见方法二）。

## 方法二：使用迁移脚本

### 1. 备份现有数据库（推荐）

```bash
cd backend
cp data/rag.db data/rag.db.backup
```

### 2. 执行迁移脚本

```bash
cd backend
python migrations/add_knowledge_base_support.py
```

### 3. 验证迁移结果

```bash
sqlite3 backend/data/rag.db
```

在 SQLite 命令行中执行：

```sql
-- 查看 knowledge_bases 表
SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_bases';

-- 查看 files 表结构
PRAGMA table_info(files);
```

### 4. 回滚（如需要）

```bash
cd backend
python migrations/add_knowledge_base_support.py rollback
```

然后恢复备份：

```bash
cp backend/data/rag.db.backup backend/data/rag.db
```

## 方法三：手动 SQL 迁移

### 1. 创建 knowledge_bases 表

```sql
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 2. 添加 kb_id 字段到 files 表

```sql
ALTER TABLE files ADD COLUMN kb_id TEXT;
```

## 数据库结构

### knowledge_bases 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT | 知识库唯一标识 |
| name | TEXT | 知识库名称 |
| description | TEXT | 知识库描述 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### files 表（新增字段）

| 字段 | 类型 | 说明 |
|------|------|------|
| kb_id | TEXT | 关联的知识库ID（可为NULL） |

## 迁移后注意事项

1. **现有文件**：现有文件的 `kb_id` 为 NULL，它们不属于任何知识库
2. **兼容性**：应用代码已处理向后兼容，可以继续使用原有功能
3. **新上传文件**：通过知识库上传的文件会关联 `kb_id`

## 常见问题

### Q: 迁移后原有数据会丢失吗？
A: 不会。迁移只是添加新表和新字段，不会删除或修改现有数据。

### Q: 可以跳过迁移直接使用吗？
A: 可以。应用代码会自动处理兼容性问题，但为了完整功能，建议执行迁移。

### Q: 迁移失败怎么办？
A: 恢复备份文件 `data/rag.db.backup`，然后重新执行迁移。
