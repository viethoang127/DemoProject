from datetime import datetime
from collection.crawl_official_data import crawl_article_content, get_link
from clean_data.normalize import normalize_text
from clean_data.tokenization import tokenize_text
from chunking.recursive_chunking import process_and_add_article
from model_embedding.embedding import load_data, WeatherVectorDB
from storage.db import insert_article, delete_old_data
from storage.init_db import init_sqlite_db
from config import DEFAULT_URLS
from temporal.temporal_detector import TemporalDetector


def crawl_and_sync(urls=None):
    if urls is None:
        urls = DEFAULT_URLS

    init_sqlite_db()
    delete_old_data()

    

    all_links = []
    seen_urls = set()
    for url in urls:
        links = get_link(url)
        for link in links:
            if link['link'] not in seen_urls:
                seen_urls.add(link['link'])
                all_links.append(link)

    inserted_articles = 0
    for link in all_links:
        crawl_data = crawl_article_content(link['link'], link['main_title'])
        if not crawl_data:
            continue
        fetched_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cleaned_content = normalize_text(crawl_data['content'])
        cleaned_content = tokenize_text(cleaned_content)

        if insert_article(
            source='trung tam khi tuong thuy van',
            url=crawl_data['link'],
            main_title=crawl_data['main_title'],
            title=crawl_data['title'],
            content=cleaned_content,
            fetched_at=fetched_at,
        ):
            inserted_articles += 1

    vector_db = WeatherVectorDB()
    ids, texts, fetched_times = load_data()
    vector_db.clear_expired_data()

    synced_articles = 0
    for article_id, text, fetched_at in zip(ids, texts, fetched_times):
        if process_and_add_article(vector_db=vector_db, article_id=article_id, text=text, reference_time=fetched_at):
            # Removed duplicate synchronization call
            synced_articles += 1

    return vector_db, inserted_articles, synced_articles
