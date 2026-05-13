-- 迁移002：教材体系统一 + 学习工具表 + 公告问答 + 配置
-- 执行日期：2026-04-28

-- 1. 创建笔记表
CREATE TABLE IF NOT EXISTS chapter_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT (datetime('now')),
    updated_at TIMESTAMP DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (chapter_id) REFERENCES chapters(id)
);

-- 2. 创建书签表
CREATE TABLE IF NOT EXISTS chapter_bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    note VARCHAR(200),
    created_at TIMESTAMP DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (chapter_id) REFERENCES chapters(id),
    UNIQUE(user_id, class_id, chapter_id)
);

-- 3. 创建公告表
CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    created_by INTEGER,
    pinned BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT (datetime('now')),
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 4. 创建问答表
CREATE TABLE IF NOT EXISTS qa_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    reply TEXT,
    replied_by INTEGER,
    replied_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT (datetime('now')),
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (replied_by) REFERENCES users(id)
);

-- 5. 创建系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    updated_at TIMESTAMP DEFAULT (datetime('now'))
);

-- 6. 新增字段：tab_switch_count（防作弊）
-- 注意：如果表已存在，SQLite 不支持 ALTER TABLE ADD COLUMN IF NOT EXISTS
-- 请确认 chapter_progress 表是否有 tab_switch_count 列
-- 如果不存在，手动执行：
-- ALTER TABLE chapter_progress ADD COLUMN tab_switch_count INTEGER DEFAULT 0;
-- ALTER TABLE test_results ADD COLUMN tab_switch_count INTEGER DEFAULT 0;

-- 7. 迁移互动教材记录到统一表
INSERT OR IGNORE INTO class_textbooks (class_id, textbook_id, resource_type, added_at)
SELECT cti.class_id, cti.textbook_id, 'interactive',
    COALESCE(cti.added_at, datetime('now'))
FROM class_textbooks_interactive cti
WHERE NOT EXISTS (
    SELECT 1 FROM class_textbooks ct
    WHERE ct.class_id = cti.class_id AND ct.textbook_id = cti.textbook_id
);

-- 8. 清理 resource_type
UPDATE class_textbooks SET resource_type = 'pdf' WHERE resource_type IS NULL OR resource_type = '';

-- 9. 创建索引
CREATE INDEX IF NOT EXISTS idx_class_textbooks_type ON class_textbooks(class_id, resource_type);
CREATE INDEX IF NOT EXISTS idx_chapter_notes_user ON chapter_notes(user_id, class_id);
CREATE INDEX IF NOT EXISTS idx_chapter_bookmarks_user ON chapter_bookmarks(user_id, class_id);
CREATE INDEX IF NOT EXISTS idx_announcements_class ON announcements(class_id, pinned);
CREATE INDEX IF NOT EXISTS idx_qa_class ON qa_questions(class_id);

-- 10. 确认迁移成功后可选删除旧表
-- DROP TABLE IF EXISTS class_textbooks_interactive;
