
from services.sync import crawl_and_sync
from LLM_reasoning.LLM_reasoning import llm_reasoning, LLMClient
from model_embedding.embedding import WeatherVectorDB
from query_parser.query_parser import QueryParser
from config import LLM_MODEL_ID, VECTOR_DB_SCORE_THRESHOLD
import traceback


def main():
    try:
        print("Bắt đầu đồng bộ dữ liệu...", flush=True)
        vector_db, inserted_articles, synced_articles = crawl_and_sync()
        print(f"Đã chèn {inserted_articles} bài báo mới và đồng bộ {synced_articles} bài lên Vector DB.", flush=True)

        llm = None
        query_parser = QueryParser()

        print("Hệ thống đã sẵn sàng. ", flush=True)
        print("Pipeline: Query → Parser (extract date/location/event) → Vector Search → LLM Reasoning", flush=True)
        while True:
            print("\nNhập câu hỏi hoặc gõ 'exit' để thoát.", flush=True)
            try:
                query = input("> ").strip()
            except EOFError:
                print("\nKết thúc chương trình (EOF).", flush=True)
                break

            if not query:
                continue
            if query.lower() == 'exit':
                break

            # ========== STEP 1: Parse Query ==========
            print("\n[STEP 1] Phân tích temporal expression trong câu hỏi...", flush=True)
            parsed_query = query_parser.parse(query)
            time_info = parsed_query.get('time_info', {})
            start_date = time_info.get('start_date')
            end_date = time_info.get('end_date')
            print(f"   Ngày: {start_date} -> {end_date} ({parsed_query.get('date_expr', 'current date')})", flush=True)
            print(f"   Query sạch để embedding: '{parsed_query['cleaned_query']}'", flush=True)
            print(f"   Location/Event: {parsed_query.get('locations', [])}", flush=True)
            print("\n[STEP 2] Tìm kiếm evidence từ Vector DB...", flush=True)
            raw_results = vector_db.search_relevant_chunks(
                query_comment=parsed_query['cleaned_query'],
                start_date=start_date,
                end_date=end_date,
                target_locations=parsed_query.get('locations', [])
            )
            results = [r for r in raw_results if r["score"] >= VECTOR_DB_SCORE_THRESHOLD]            
            if not results:
                print(" Không tìm thấy tài liệu đối chứng đủ độ tin cậy.", flush=True)
                continue
            
            print(f" Tìm thấy {len(results)} evidence phù hợp:", flush=True)
            for i, r in enumerate(results, 1):
                print(f"  [{i}] Score: {r['score']:.2%} | {r['text'][:60]}...", flush=True)

            if llm is None:
                try:
                    print("\n[STEP 3] Khởi tạo LLM client... (có thể mất thời gian)", flush=True)
                    llm = LLMClient(model_id=LLM_MODEL_ID)
                    print(" LLM client đã sẵn sàng.", flush=True)
                except Exception as e:
                    print(" Không thể khởi tạo LLM client:", str(e), flush=True)
                    traceback.print_exc()
                    print("LLM không khả dụng; trả về đoạn văn bản đối chứng thay vì gọi LLM.", flush=True)
                    print({
                        "label": "UNCERTAIN",
                        "reason": "LLM không khả dụng; đây là các đoạn văn bản đối chứng:",
                        "matches": results
                    }, flush=True)
                    continue

            try:
                print("\n[STEP 4] LLM suy luận với temporal context...", flush=True)
                detection = llm_reasoning(llm, query, results, parsed_query_info=parsed_query)
                # Format output
                output = f"""

                KẾT LUẬN: {detection.get('label', 'UNCERTAIN'):12} 
                Lý do: {detection.get('reason', 'N/A')} 
                Nguồn: {detection.get('source', 'unknown')[:30]:30} 
                Độ khớp: {detection.get('score', 0):25.2%} 

            """
                print(output, flush=True)
            except Exception as e:
                print(f" ERROR khi gọi LLM: {str(e)}", flush=True)
                traceback.print_exc()
                continue

    except Exception as e:
        print("Lỗi khi chạy chương trình:", str(e), flush=True)
        traceback.print_exc()


if __name__ == '__main__':
    main()

