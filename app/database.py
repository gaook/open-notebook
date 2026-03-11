"""SQLite 数据库初始化与连接管理"""

import sqlite3
from pathlib import Path

_db_path: str = ""


def init_db(data_dir: str):
    """初始化数据库，创建所有表"""
    global _db_path
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    _db_path = str(Path(data_dir) / "open_notebook.db")

    conn = sqlite3.connect(_db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS notebooks (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL DEFAULT '未命名笔记本',
            description TEXT DEFAULT '',
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS documents (
            id           TEXT PRIMARY KEY,
            notebook_id  TEXT NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
            filename     TEXT NOT NULL,
            file_type    TEXT NOT NULL,
            file_size    INTEGER NOT NULL,
            file_path    TEXT NOT NULL,
            full_text    TEXT NOT NULL DEFAULT '',
            chunk_count  INTEGER NOT NULL DEFAULT 0,
            status       TEXT NOT NULL DEFAULT 'processing'
                         CHECK(status IN ('processing', 'ready', 'error')),
            error_msg    TEXT,
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_documents_notebook
            ON documents(notebook_id);

        CREATE TABLE IF NOT EXISTS messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            notebook_id  TEXT NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
            role         TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content      TEXT NOT NULL,
            sources      TEXT,
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_messages_notebook
            ON messages(notebook_id, id);

        CREATE TABLE IF NOT EXISTS generated_content (
            id           TEXT PRIMARY KEY,
            notebook_id  TEXT NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
            content_type TEXT NOT NULL
                         CHECK(content_type IN ('summary', 'faq', 'study_guide', 'timeline', 'note')),
            title        TEXT NOT NULL,
            content      TEXT NOT NULL,
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_generated_notebook
            ON generated_content(notebook_id);
    """)

    # 迁移：如果旧表没有 'note' 类型，重建表
    try:
        conn.execute("INSERT INTO generated_content (id, notebook_id, content_type, title, content) VALUES ('_test', '_', 'note', '', '')")
        conn.execute("DELETE FROM generated_content WHERE id = '_test'")
    except sqlite3.IntegrityError:
        # 旧 CHECK 约束不包含 'note'，需要重建
        conn.executescript("""
            ALTER TABLE generated_content RENAME TO _gc_old;
            CREATE TABLE generated_content (
                id           TEXT PRIMARY KEY,
                notebook_id  TEXT NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
                content_type TEXT NOT NULL
                             CHECK(content_type IN ('summary', 'faq', 'study_guide', 'timeline', 'note')),
                title        TEXT NOT NULL,
                content      TEXT NOT NULL,
                created_at   TEXT NOT NULL DEFAULT (datetime('now'))
            );
            INSERT INTO generated_content SELECT * FROM _gc_old;
            DROP TABLE _gc_old;
            CREATE INDEX IF NOT EXISTS idx_generated_notebook ON generated_content(notebook_id);
        """)

    conn.close()


def get_conn() -> sqlite3.Connection:
    """获取数据库连接（启用外键和 Row 工厂）"""
    conn = sqlite3.connect(_db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn
