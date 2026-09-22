import sqlite3
from config import DB_PATH


def insert_article(source, url, main_title, title, content, fetched_at):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT OR IGNORE INTO raw_official_data
            (source, url, main_title, title, content, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (source, url, main_title, title, content, fetched_at),
        )
        conn.commit()
        return cursor.rowcount == 1
    except sqlite3.IntegrityError:
        print(f"ERROR duplicate url: {url}")
        return False
    finally:
        conn.close()


def delete_old_data(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = """
    DELETE FROM raw_official_data
    WHERE fetched_at < datetime('now', '-2 days', 'localtime')
    """
    cursor.execute(query)
    conn.commit()
    conn.close()
    print("đã dọn dẹp xong dữ liệu trong data.db")
