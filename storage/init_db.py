import sqlite3
from config import DB_PATH


def init_sqlite_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raw_official_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        url TEXT NOT NULL UNIQUE,
        main_title TEXT,
        title TEXT,
        content TEXT NOT NULL,
        fetched_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_articles (
        article_id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        fetched_at TEXT
    );
    """)

    processed_columns = {
        row[1] for row in cursor.execute("PRAGMA table_info(processed_articles)")
    }
    if "url" not in processed_columns:
        cursor.execute("ALTER TABLE processed_articles ADD COLUMN url TEXT")
        cursor.execute(
            "UPDATE processed_articles SET url = article_id WHERE url IS NULL"
        )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fact_check_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_query TEXT,
        ai_label TEXT,
        ai_reason TEXT,
        checked_at TEXT
    );
    """)

    try:
        cursor.execute(
            """
            DELETE FROM raw_official_data
            WHERE id NOT IN (
                SELECT MIN(id) FROM raw_official_data GROUP BY url
            )
            """
        )
    except Exception:
        pass
    try:
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_official_data_url ON raw_official_data(url)"
        )
    except Exception:
        pass

    conn.commit()
    conn.close()

