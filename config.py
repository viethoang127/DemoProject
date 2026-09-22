DB_PATH = "data.db"
CHROMA_DB_PATH = "./chroma_db"

EMBEDDING_MODEL_NAME = "keepitreal/vietnamese-sbert"
EMBEDDING_COLLECTION_NAME = "weather_news_vietnamese_sbert"


CHUNK_SIZE = 150  
CHUNK_OVERLAP = 30
CHUNK_SEPARATORS = ["\n\n", "\n", "."]


EMBEDDING_MAX_LENGTH = 256


LLM_MODEL_ID = "Qwen/Qwen2.5-3B-Instruct"  
DEFAULT_URLS = [
    'https://nchmf.gov.vn/kttv/vi-VN/1/thoi-tiet-1-15.html',
    'https://nchmf.gov.vn/kttv/vi-VN/1/khi-hau-7-15.html',
    'https://nchmf.gov.vn/kttv/vi-VN/1/thuy-van-12-18.html',
    'https://nchmf.gov.vn/kttv/vi-VN/1/hai-van-22-15.html'
]
VECTOR_DB_TOP_K = 5
VECTOR_DB_SCORE_THRESHOLD = 0.35  
VECTOR_DB_TIME_WINDOW_DAYS = 2

LLM_MAX_TOKENS = 512
LLM_TEMPERATURE = 0.1
