-- ============================================
-- RAG知识库功能 - 数据库迁移SQL脚本
-- ============================================
--
-- 使用方法：
--   1. 打开命令行，进入 backend 目录
--   2. 执行: sqlite3 data/rag.db < migrations/add_knowledge_base_support.sql
--   3. 或者手动打开数据库: sqlite3 data/rag.db
--      然后输入: .read migrations/add_knowledge_base_support.sql
--
-- ============================================

-- 1. 创建 knowledge_bases 表
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 2. 检查是否需要添加 kb_id 列到 files 表
-- 注意：SQLite 不支持 IF NOT EXISTS 语法添加列
-- 如果 kb_id 列已存在，下面的语句会报错，可以忽略

-- 首先检查 kb_id 列是否存在
-- 如果下面的语句报错说 "duplicate column name"，说明列已存在，可以忽略
ALTER TABLE files ADD COLUMN kb_id TEXT;

-- ============================================
-- 验证迁移结果
-- ============================================

-- 查看 knowledge_bases 表
-- SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_bases';

-- 查看 files 表结构
-- PRAGMA table_info(files);

-- ============================================
-- 注意事项
-- ============================================
--
-- 1. 执行前建议先备份数据库：
--    cp data/rag.db data/rag.db.backup
--
-- 2. 如果 kb_id 列已存在，ALTER TABLE 语句会报错，可以忽略
--
-- 3. 现有文件的 kb_id 会是 NULL，不影响原有功能
--
-- 4. 新上传到知识库的文件会关联对应的 kb_id
--
-- ============================================
