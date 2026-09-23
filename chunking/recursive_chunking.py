from langchain_text_splitters import RecursiveCharacterTextSplitter
import sqlite3
import re
from datetime import datetime
from config import DB_PATH, CHUNK_SIZE, CHUNK_OVERLAP, CHUNK_SEPARATORS
from temporal.temporal_detector import TemporalDetector
import re

def chunk_text(text) -> list: 
    splitter = RecursiveCharacterTextSplitter( chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, separators=CHUNK_SEPARATORS ) 
    chunks = splitter.split_text(text) 
    return chunks 

temporal_detector = TemporalDetector() 


def canonical_event_date(temporal_expressions: str, published_time: str):
    explicit_match = re.search(
        r"(?:ngày\s+)?(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?",
        temporal_expressions or "",
    )
    if explicit_match:
        day = int(explicit_match.group(1))
        month = int(explicit_match.group(2))
        year_text = explicit_match.group(3)
        year = int(year_text) if year_text else int(published_time[:4])
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return published_time[:10] if published_time else None


def inherit_temporal_context(chunks, published_time):
    """Propagate the nearest article temporal context to chunks without dates."""
    detected = []
    for chunk in chunks:
        temporal_info = temporal_detector.detect(chunk)
        expressions = ", ".join(
            item["text"] for item in temporal_info["expressions"]
        )
        detected.append(expressions)

    first_context = next((value for value in detected if value), "")
    inherited = []
    current_context = first_context
    for expressions in detected:
        if expressions:
            current_context = expressions
            inherited.append((expressions, "content"))
        elif current_context:
            inherited.append((current_context, "inherited"))
        else:
            inherited.append(("", "published_time"))

    return [
        {
            "temporal_expressions": expressions,
            "temporal_source": source,
            "event_date": (
                canonical_event_date(expressions, published_time)
                if expressions
                else (published_time[:10] if published_time else None)
            ),
        }
        for expressions, source in inherited
    ]


TEMPORAL_CONTEXT_VERSION = 2

def process_and_add_article(vector_db, article_id: str, text: str, reference_time: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 from processed_articles WHERE article_id = ?", (article_id,))
    exists = cursor.fetchone()

    if exists:
        existing_chunks = vector_db.collection.get(
            where={"article_id": article_id},
            limit=1,
            include=["metadatas"],
        )
        if not existing_chunks.get("ids"):
            cursor.execute(
                "DELETE FROM processed_articles WHERE article_id = ?",
                (article_id,),
            )
            conn.commit()
            exists = None
        metadata = (existing_chunks.get("metadatas") or [None])[0]
        if exists:
            if metadata and metadata.get("temporal_context_version") == TEMPORAL_CONTEXT_VERSION:
                print(f"bài báo có ID : {article_id} đã tồn tại trong hệ thống, không cập nhật")
                conn.close()
                return False

            existing_data = vector_db.collection.get(
                where={"article_id": article_id},
                include=["documents", "metadatas"],
            )
            existing_documents = existing_data.get("documents") or []
            existing_metadatas = existing_data.get("metadatas") or []
            temporal_contexts = inherit_temporal_context(
                existing_documents,
                reference_time,
            )
            updated_metadatas = []
            for old_metadata, temporal_context in zip(
                existing_metadatas,
                temporal_contexts,
            ):
                updated_metadata = dict(old_metadata or {})
                updated_metadata.update(temporal_context)
                updated_metadata["temporal_context_version"] = TEMPORAL_CONTEXT_VERSION
                updated_metadatas.append(updated_metadata)

            if existing_data.get("ids") and updated_metadatas:
                vector_db.collection.update(
                    ids=existing_data["ids"],
                    metadatas=updated_metadatas,
                )
                print(f"đã cập nhật temporal context cho bài báo {article_id}")
                conn.close()
                return False

            event_date = metadata.get("event_date") if metadata else None
            if event_date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(event_date)):
                print(f"bài báo có ID : {article_id} đã tồn tại trong hệ thống, không cập nhật")
                conn.close()
                return False

            print(f"phát hiện metadata cũ của bài báo {article_id}, tiến hành chuẩn hóa lại")
            vector_db.collection.delete(where={"article_id": article_id})
    print(f"phát hiện bài báo mới có ID {article_id}. Tiến hành cập nhật")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute(
            """
            INSERT INTO processed_articles(article_id, url, fetched_at)
            VALUES (?, ?, ?)
            """,
            (article_id, article_id, current_time),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        print(f" [Chặn trùng] ID {article_id} vừa được luồng khác nạp xong.")
        conn.close()
        return False
    chunks = chunk_text(text)
    print(
        f"Article {article_id} : đã tạo ra {len(chunks)} chunks"
    )

    chunk_metadata = []
    temporal_contexts = inherit_temporal_context(chunks, reference_time)
    for chunk_id, (chunk, temporal_context) in enumerate(
        zip(chunks, temporal_contexts)
    ):
        temporal_expressions = temporal_context["temporal_expressions"]
        temporal_source = temporal_context["temporal_source"]
        event_date = temporal_context["event_date"]

        metadata = {
            "article_id": article_id,
            "chunk_id": chunk_id,
            "fetched_at": reference_time,
            "event_date": event_date,
            "timestamp": int(datetime.now().timestamp()),
            "temporal_expressions": temporal_expressions,
            "temporal_source": temporal_source,
            "temporal_context_version": TEMPORAL_CONTEXT_VERSION,
            "location": "",
            "source": "official_weather"
        }
        chunk_metadata.append(metadata)

        print(
            f"  Chunk {chunk_id}: "
            f"source={temporal_source}, "
            f"temporal={temporal_expressions}"
        )

    vector_db.add_article(article_id = article_id, text_chunks = chunks, metadatas = chunk_metadata)

    conn.close()
    print(f"đã cập nhật xong bài báo có id {article_id} vào 2 database \n")
    return True
