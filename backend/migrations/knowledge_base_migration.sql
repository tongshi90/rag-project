-- RAG Knowledge Base Migration Script
-- 添加知识库功能和kb_id关联

-- 1. 创建知识库表
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 2. 为files表添加kb_id字段（如果不存在）
-- SQLite不支持IF NOT EXISTS语法用于添加列，所以需要先检查
-- 执行此脚本时如果kb_id已存在会报错，可以忽略

-- 检查并添加kb_id列（在应用程序中处理）

-- 3. 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_files_kb_id ON files(kb_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_bases_created_at ON knowledge_bases(created_at);
