import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import pandas as pd

from services.sync import crawl_and_sync
from LLM_reasoning.LLM_reasoning import llm_reasoning, LLMClient
from model_embedding.embedding import WeatherVectorDB
from query_parser.query_parser import QueryParser
from config import LLM_MODEL_ID, VECTOR_DB_SCORE_THRESHOLD
import traceback

def predict(query, vector_db, query_parser, llm):

    
    parsed_query = query_parser.parse(query)

    time_info = parsed_query.get("time_info", {})
    start_date = time_info.get("start_date")
    end_date = time_info.get("end_date")

    
    raw_results = vector_db.search_relevant_chunks(
        query_comment=parsed_query["cleaned_query"],
        start_date=start_date,
        end_date=end_date,
        target_locations=parsed_query.get("locations", [])
    )

    results = [
        r for r in raw_results
        if r["score"] >= VECTOR_DB_SCORE_THRESHOLD
    ]

    if not results:
        return "UNCERTAIN"

    detection = llm_reasoning(
        llm,
        query,
        results,
        parsed_query_info=parsed_query
    )

    return detection.get("label", "UNCERTAIN")




def main():

    print("Đồng bộ dữ liệu...")

    vector_db, inserted_articles, synced_articles = crawl_and_sync()

    print("Khởi tạo Query Parser...")
    query_parser = QueryParser()

    print("Khởi tạo LLM...")
    llm = LLMClient(model_id=LLM_MODEL_ID)

    current_folder = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_folder, "test.csv")
    df = pd.read_csv(csv_path)
    num_true_label = 0
    for _,row in df.iterrows():
        query = row['query']
        label = row['label']
        prediction = predict(query, vector_db, query_parser, llm)
        if prediction == label:
            num_true_label +=1

    accuracy = num_true_label / len(df) if len(df) else 0.0
    print(f"Accuracy: {accuracy:.2%} ({num_true_label}/{len(df)})")

if __name__ == "__main__":
    main()