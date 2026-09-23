import sqlite3
import re
from sentence_transformers import SentenceTransformer
import os
import chromadb
from datetime import datetime
from datetime import datetime, timedelta
from config import (
    DB_PATH,
    CHROMA_DB_PATH,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_COLLECTION_NAME,
    VECTOR_DB_TIME_WINDOW_DAYS,
    EMBEDDING_MAX_LENGTH,
)


def load_data(db_path=DB_PATH):

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            url,
            content,
            fetched_at
        FROM raw_official_data
    """)

    rows = cursor.fetchall()

    conn.close()

    urls = [row[0] for row in rows]
    texts = [row[1] for row in rows]
    fetched_times = [row[2] for row in rows]

    return urls, texts, fetched_times

class WeatherVectorDB:
    def __init__(self, db_path=CHROMA_DB_PATH, model_name=EMBEDDING_MODEL_NAME):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name=EMBEDDING_COLLECTION_NAME,
            metadata={'hnsw:space': 'cosine'}
        )
        self.embedding_model = SentenceTransformer(model_name)
        self.embedding_model.max_seq_length = EMBEDDING_MAX_LENGTH
        print(f"Đã tải mô hình {model_name} thành công")
        print(f"Cơ sở dữ liệu đang chạy tại {os.path.abspath(db_path)} \n")

    def get_embedding(self, text: str):
        return self.embedding_model.encode(text, normalize_embeddings=True).tolist()

    @staticmethod
    def _date_parts(value: str):
        matches = re.findall(
            r"(?<!\d)(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?(?!\d)",
            value or "",
        )
        dates = []
        for day, month, year in matches:
            dates.append((int(day), int(month), int(year) if year else None))
        return dates

    @classmethod
    def _date_ranges(cls, value: str):
        """Expand Vietnamese date ranges such as 21/9 đến 23/9."""
        date_pattern = re.compile(
            r"(?:ngày\s+)?(\d{1,2})[/-](\d{1,2})"
            r"(?:[/-](\d{2,4}))?",
            re.IGNORECASE,
        )
        ranges = []
        matches = list(date_pattern.finditer(value or ""))
        for first, second in zip(matches, matches[1:]):
            connector = value[first.end():second.start()]
            connector_lower = connector.lower()
            if not (
                "\u0111\u1ebfn" in connector_lower
                or "t\u1edbi" in connector_lower
                or "-" in connector
                or "–" in connector
                or "—" in connector
            ):
                continue
            start_day, start_month, start_year = first.groups()
            end_day, end_month, end_year = second.groups()
            start_year = int(start_year) if start_year else None
            end_year = int(end_year) if end_year else start_year
            if start_year is None and end_year is None:
                start_day = int(start_day)
                start_month = int(start_month)
                end_day = int(end_day)
                end_month = int(end_month)
                if not (1 <= start_month <= 12 and 1 <= end_month <= 12):
                    continue
                if not (1 <= start_day <= 31 and 1 <= end_day <= 31):
                    continue
                ranges.append((start_day, start_month, end_day, end_month))
        return ranges

    @classmethod
    def _matches_requested_dates(cls, metadata, start_date, end_date, text=""):
        """Match a query against every date in a chunk, not only event_date."""
        if not start_date or not end_date:
            return True

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        if start > end:
            start, end = end, start

        requested = {
            (current.day, current.month)
            for offset in range((end - start).days + 1)
            for current in [start + timedelta(days=offset)]
        }
        metadata_dates = cls._date_parts(
            metadata.get("temporal_expressions", "")
        )
        metadata_dates.extend(cls._date_parts(text))

        for range_value in (
            metadata.get("temporal_expressions", ""),
            text,
        ):
            for start_day, start_month, end_day, end_month in cls._date_ranges(
                range_value
            ):
                try:
                    range_start = datetime(start.year, start_month, start_day)
                    range_end = datetime(start.year, end_month, end_day)
                except ValueError:
                    continue
                if range_end < range_start:
                    range_end = range_end.replace(year=range_end.year + 1)
                if any(
                    range_start.date() <= current.date() <= range_end.date()
                    for current in (
                        start + timedelta(days=offset)
                        for offset in range((end - start).days + 1)
                    )
                ):
                    return True

        for day, month, year in metadata_dates:
            if (day, month) in requested:
                return True

        event_date = metadata.get("event_date")
        if event_date:
            try:
                event = datetime.strptime(str(event_date), "%Y-%m-%d")
                return (event.day, event.month) in requested
            except ValueError:
                pass
        return False
    
    def add_article(self, article_id: str, text_chunks: list, metadatas: list):
        if not text_chunks:
            return
        
        ids = [f"{article_id}_chunk_{i}" for i in range(len(text_chunks))]
        embeddings = [self.get_embedding(chunk) for chunk in text_chunks]
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=text_chunks,
            metadatas=metadatas
        )
        print(f"Đã lưu thành công {len(text_chunks)} chunks cho bài viết {article_id}")

    def search_relevant_chunks(
        self, 
        query_comment: str, 
        top_k: int = 5, 
        start_date: str = None, 
        end_date: str = None, 
        target_locations: list = None,
        target_date: str = None
    ) -> list:
        
        if target_date and not start_date and not end_date:
            start_date = target_date
            end_date = target_date

        query_vector = self.get_embedding(query_comment)
        conditions = []
        indexed_locations = False
        if target_locations and len(target_locations) > 0:
            try:
                indexed_locations = bool(
                    self.collection.get(
                        where={"location": {"$ne": ""}},
                        limit=1,
                    ).get("ids")
                )
            except Exception:
                indexed_locations = False

        if indexed_locations:
            loc_conditions = []
            for loc in target_locations:
                location = str(loc).strip()
                if location:
                    loc_conditions.append({"location": {"$contains": location}})
            
            if len(loc_conditions) == 1:
                conditions.append(loc_conditions[0])
            elif len(loc_conditions) >= 2:
                conditions.append({"$or": loc_conditions})
        if len(conditions) == 1:
            where_clause = conditions[0]
        elif len(conditions) > 1:
            where_clause = {"$and": conditions}
        else:
            where_clause = None

        query_args = {
            "query_embeddings": [query_vector],
            "n_results": max(top_k, self.collection.count()),
        }
        if where_clause is not None:
            query_args["where"] = where_clause

        response = self.collection.query(**query_args)

        results = []
        if response and response['documents'] and response['documents'][0]:
            for i in range(len(response['documents'][0])):
                metadata = response['metadatas'][0][i]
                if not self._matches_requested_dates(
                    metadata,
                    start_date,
                    end_date,
                    response['documents'][0][i],
                ):
                    continue
                similarity_score = 1 - response['distances'][0][i]
                results.append({
                    "id": response['ids'][0][i],
                    "text": response['documents'][0][i],
                    "score": round(similarity_score, 4),
                    "metadata": metadata
                })
        results.sort(key=lambda item: item["score"], reverse=True)
        results = results[:top_k]
        return results

    def clear_expired_data(self):
        print("🧹 [HỆ THỐNG DỌN DẸP] Đang quét dữ liệu hết hạn...")
        forty_eight_hours_ago = int(datetime.now().timestamp()) - (VECTOR_DB_TIME_WINDOW_DAYS * 24 * 3600)
        self.collection.delete(
            where={"timestamp": {"$lt": forty_eight_hours_ago}}
        )
