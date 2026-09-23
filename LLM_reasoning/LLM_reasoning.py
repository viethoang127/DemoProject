import json
import re
import numpy as np
from transformers import AutoTokenizer, pipeline
import torch
from config import LLM_MAX_TOKENS, LLM_TEMPERATURE

class LLMClient:
    def __init__(self, model_id):
        print(f"Khởi tạo model {model_id}...", flush=True)
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, padding_side="left", trust_remote_code=True)
        
        try:
            self.generator = pipeline(
                "text-generation", 
                model=model_id,
                tokenizer=self.tokenizer,
                device="cpu",
                trust_remote_code=True
            )
            print(f" Model {model_id} khởi tạo thành công!", flush=True)
        except Exception as e:
            print(f"  Lỗi khi load với CPU: {e}. Đang thử với GPU...", flush=True)
            self.generator = pipeline(
                "text-generation", 
                model=model_id,
                tokenizer=self.tokenizer,
                trust_remote_code=True
            )

    def generate(self, system_message: str, user_message: str) -> str:
        prompt_text = f"System: {system_message}\n\nUser: {user_message}\n\nAssistant:"
        try:
            output = self.generator(
                prompt_text,
                max_new_tokens=LLM_MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
                do_sample=False,  
                num_beams=1,
            )
            
            
            if isinstance(output, list) and len(output) > 0:
                result = output[0].get('generated_text', '')
                
                if 'Assistant:' in result:
                    result = result.split('Assistant:')[-1].strip()
                return result if result else "{}"
            else:
                return "{}"
        except Exception as e:
            print(f" Lỗi generate: {e}", flush=True)
            return "{}"

def build_reasoning_prompt(
            query,
            evidence,
            parsed_query_info=None
        ):
        
        query_date = "N/A"
        query_end_date = "N/A"
        query_date_expr = "N/A"

        if parsed_query_info:
            query_date = parsed_query_info.get(
                "date",
                "N/A"
            )

            query_date_expr = parsed_query_info.get(
                "date_expr",
                "N/A"
            )
            time_info = parsed_query_info.get("time_info", {})
            query_end_date = time_info.get("end_date", query_date)


        context_parts = []

        for item in evidence:

            temporal_expressions = item[
                "temporal_expressions"
            ]

            event_date = item.get("event_date", "")
            fetched_at = item[
                "fetched_at"
            ]

            temporal_source = item[
                "temporal_source"
            ]

            if temporal_expressions:
                temporal_info = (
                    f"Temporal expression: "
                    f"{temporal_expressions}\n"
                    f"Temporal source: content\n"
                    f"Event date metadata: {event_date}"
                )
            else:
                temporal_info = (
                    f"Temporal expression: NONE\n"
                    f"Temporal source: fetched_at fallback\n"
                    f"Fetched at: {fetched_at}"
                )

            context_parts.append(
                f"""
    [EVIDENCE {item["id"]}]
    Content:
    {item["text"]}
    {temporal_info}
    Semantic similarity:
    {item["score"]:.4f}
    """
            )
        context = "\n".join(context_parts)
        return f"""
    Bạn là hệ thống xác minh thông tin thiên tai.

    Hãy xác minh câu hỏi dựa CHỈ trên các evidence chính thống
    được cung cấp.

    [QUERY]

    Câu hỏi gốc:
    {query}

    Ngày được xác định từ query:
    {query_date}

    Ngày kết thúc của query:
    {query_end_date}

    Biểu thức thời gian trong query:
    {query_date_expr}


    [EVIDENCE]

    {context}


    [QUY TẮC QUYẾT ĐỊNH NGHIÊM NGẶT]

    1. Ưu tiên thời gian được biểu diễn trực tiếp trong nội dung
    evidence và Event date metadata.

    2. Nếu evidence ghi một khoảng thời gian, ví dụ "21/9 đến 23/9",
    thì thông tin áp dụng cho mọi ngày trong khoảng đó, bao gồm cả
    ngày bắt đầu và ngày kết thúc. Vì vậy, ngày 22/9 nằm trong khoảng
    21/9 đến 23/9.

    3. Nếu evidence không chứa temporal expression thì chỉ dùng
    fetched_at fallback như ngày tham chiếu gần đúng, không gọi đó là
    thời gian sự kiện chắc chắn.

    4. Không được mặc định rằng fetched_at là thời gian của sự kiện
    nếu evidence đã có temporal expression.

    5. So sánh toàn bộ khoảng thời gian của query với thời gian hoặc
    khoảng thời gian của evidence trước khi kết luận.

    6. Nếu evidence nói về một thời điểm khác với query và không
    có cơ sở để suy ra rằng thông tin áp dụng cho query,
    không được dùng evidence đó để xác nhận query.

    7. Nếu evidence khớp địa điểm, thời gian và hiện tượng được hỏi,
    ưu tiên REAL dù câu chữ evidence không giống hệt query.

    8. Nếu query phát biểu phủ định một hiện tượng thời tiết, nhưng
    evidence cùng thời gian và địa điểm cho thấy hiện tượng đó xảy ra,
    phải chọn FAKE.

    9. Chỉ chọn UNCERTAIN khi evidence không đủ thông tin để xác định
    rõ thời gian, địa điểm hoặc sự kiện, hoặc khi các dữ liệu mâu thuẫn
    mà không có căn cứ rõ ràng.

    10. KHÔNG được trả về UNCERTAIN chỉ vì vẫn muốn "an toàn". Nếu
    evidence đã đủ để khẳng định hoặc bác bỏ, hãy quyết định.


    [OUTPUT]

    Chỉ trả về JSON:

    {{
        "label": "REAL" hoặc "FAKE" hoặc "UNCERTAIN",
        "reason": "giải thích ngắn gọn và trực tiếp",
        "source_id": "ID evidence"
    }}
    """


def parse_json_safe(text, results):
    """Parse JSON từ LLM output - nếu fail thì fallback"""
    text = text.strip()
    match = re.search(r'\{[^{}]*"label"[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if "label" in data and data["label"] in ["REAL", "FAKE", "UNCERTAIN"]:
                source_id = data.get("source_id", "1")
                try:
                    idx = int(source_id) - 1
                except (TypeError, ValueError):
                    idx = 0
                if not 0 <= idx < len(results):
                    idx = 0
                data["source"] = results[idx].get("id", "unknown") if results else "unknown"
                data["score"] = results[idx].get("score", 0) if results else 0
                return data
        except json.JSONDecodeError:
            pass
    
    text_upper = text.upper()
    if "REAL" in text_upper:
        label = "REAL"
    elif "FAKE" in text_upper:
        label = "FAKE"
    else:
        label = "UNCERTAIN"
    
    return {
        "label": label,
        "reason": text[:100],
        "source": results[0].get("id", "unknown") if results else "unknown",
        "score": results[0].get("score", 0) if results else 0
    }


def llm_reasoning(llm_client: LLMClient, query: str, results: list, parsed_query_info=None) -> dict:
        evidence = []
        for i, r in enumerate(results, 1):
            evidence.append({
            "id": i,
            "text": r.get("text", ""),
            "temporal_expressions": r.get("metadata", {}).get(
                "temporal_expressions",
                r.get("temporal_expressions", "")
            ),
            "temporal_source": r.get("metadata", {}).get(
                "temporal_source",
                r.get("temporal_source", "")
            ),
            "fetched_at": r.get("metadata", {}).get(
                "fetched_at",
                r.get("fetched_at", "")
            ),
            "event_date": r.get("metadata", {}).get("event_date", ""),
            "score": r.get("score", 0)
        })

        user_prompt = build_reasoning_prompt(
                    query,
                    evidence,
                    parsed_query_info
                )
        system_prompt = (
            "Bạn là chuyên gia phát hiện tin giả thời tiết. "
            "Không được trả về UNCERTAIN khi evidence đã đủ để xác nhận hoặc bác bỏ. "
            "Nếu query phủ định một hiện tượng nhưng evidence cùng thời gian và địa điểm cho thấy hiện tượng đó xảy ra, phải trả về FAKE. "
            "Nếu evidence khớp thời gian, địa điểm và hiện tượng, phải trả về REAL. "
            "Chỉ trả về JSON đúng định dạng: {\"label\":\"REAL|FAKE|UNCERTAIN\",\"reason\":\"...\",\"source_id\":\"...\"}."
        )
        raw_response = llm_client.generate(system_message=system_prompt, user_message=user_prompt)
        return parse_json_safe(raw_response, results)

