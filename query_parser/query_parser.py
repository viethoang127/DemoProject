import re
import unicodedata
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import dateparser

try:
    from underthesea import ner
except ImportError:  
    ner = None

class QueryParser():
    def __init__(self):
        self.date_settings = {
            'PREFER_DATES_FROM': 'past', 
            'RELATIVE_BASE': datetime.now(),
            'DATE_ORDER': 'DMY' 
        }

    def extract_time_range(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        text_lower = text.lower()
        today = datetime.now()
        range_match = re.search(r"từ\s+(.+?)\s+(đến|tới)\s+(.+?)(\s+năm\s+\d{4}|$|\b)", text_lower)
        if range_match:
            raw_start = range_match.group(1)
            raw_end = range_match.group(3)
            
            d1 = dateparser.parse(raw_start, languages=['vi'], settings=self.date_settings)
            d2 = dateparser.parse(raw_end, languages=['vi'], settings=self.date_settings)
            if d1 and d2:
                if d1.year == 1900: d1 = d1.replace(year=today.year)
                if d2.year == 1900: d2 = d2.replace(year=today.year)
                return d1.strftime("%Y-%m-%d"), d2.strftime("%Y-%m-%d"), range_match.group(0).strip()

        explicit_match = re.search(
            r"(?:ngày\s+)?\(?(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\)?",
            text_lower,
        )
        if explicit_match:
            day = int(explicit_match.group(1))
            month = int(explicit_match.group(2))
            year_text = explicit_match.group(3)
            year = int(year_text) if year_text else today.year
            if year < 100:
                year += 2000
            try:
                explicit_date = datetime(year, month, day).strftime("%Y-%m-%d")
                return explicit_date, explicit_date, explicit_match.group(0).strip()
            except ValueError:
                pass

        future_match = re.search(r"trong\s+(\d+)\s+(ngày|giờ|tiếng)\s+(tới|nữa|tiếp theo)", text_lower)
        if future_match:
            amount = int(future_match.group(1))
            unit = future_match.group(2)
            start_date = today.strftime("%Y-%m-%d")
            
            if "ngày" in unit:
                end_date = (today + timedelta(days=amount)).strftime("%Y-%m-%d")
            else: # giờ / tiếng
                end_date = (today + timedelta(hours=amount)).strftime("%Y-%m-%d")
            return start_date, end_date, future_match.group(0).strip()

        parsed_date = dateparser.parse(text_lower, languages=['vi'], settings=self.date_settings)
        if parsed_date:
            date_str = parsed_date.strftime("%Y-%m-%d")
            return date_str, date_str, None

        return None, None, None

    @staticmethod
    def _normalize_for_match(text: str) -> str:
        text = unicodedata.normalize('NFD', text.lower())
        text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
        return re.sub(r'\s+', ' ', text).strip()

    def extract_location_and_entities(self, query: str) -> Dict[str, List[str]]:
        """Dùng NER để bóc tách địa điểm (Location) và sự kiện (Event/Weather)"""
        text_lower = query.lower().strip()
        normalized_text = self._normalize_for_match(query)
        locations = []

        if ner is not None:
            entities = ner(query)
            for word, pos, chunk, tag in entities:
                if 'LOC' in tag:
                    if re.match(r"^[\d/-]+$", word):
                        continue

                    if word.lower() in ['ngày', 'tháng', 'năm', 'hôm nay', 'hôm qua', 'giờ']:
                        continue
                    locations.append(word.strip())

        if locations:
            return {"locations": list(dict.fromkeys(locations))}

        place_aliases = [
            "đà nẵng", "da nang", "hà nội", "ha noi", "hồ chí minh", "ho chi minh",
            "hải phòng", "hai phong", "cần thơ", "can tho", "đà lạt", "da lat",
            "bắc bộ", "bac bo", "nam bộ", "nam bo", "bắc trung bộ", "bac trung bo",
            "nam trung bộ", "nam trung bo", "tây nguyên", "tay nguyen",
            "đồng bằng sông hồng", "dong bang song hong", "đồng bằng sông cửu long",
            "dong bang song cuu long", "quảng ninh", "quang ninh", "quảng nam", "quang nam",
            "huế", "hue", "nha trang", "vĩnh phúc", "vinh phuc",
            "thành phố hồ chí minh", "thanh pho ho chi minh", "tp hồ chí minh", "tp ho chi minh", "tp.hcm"
        ]

        for place in place_aliases:
            if self._normalize_for_match(place) in normalized_text:
                locations.append(place)

        if not locations:
            matches = re.findall(r"(?:vùng|khu vực|khu vuc|vùng biển|bien|miền|địa điểm|dia diem|tại|ở)\s+([a-zA-ZÀ-ỹ][a-zA-ZÀ-ỹ\s-]{1,40})", query, flags=re.IGNORECASE)
            for match in matches:
                cleaned = re.sub(r"\s+\b(?:có|không|ko|mưa|nắng|gió|gio|gió mạnh|bão|bao)\b.*$", "", match, flags=re.IGNORECASE)
                cleaned = re.sub(r"\s+", " ", cleaned).strip()
                if cleaned and len(cleaned.split()) <= 5:
                    locations.append(cleaned)

        return {
            "locations": list(dict.fromkeys(locations))
        }

    def parse(self, query: str) -> Dict:
        """Main parsing method"""
        start_date, end_date, expr_matched = self.extract_time_range(query)
        ner_res = self.extract_location_and_entities(query)

        # Mặc định nếu không tìm thấy thời gian -> Ngày hiện tại
        if not start_date:
            today_str = datetime.now().strftime("%Y-%m-%d")
            start_date, end_date = today_str, today_str

        cleaned = query
        if expr_matched:
            cleaned = cleaned.replace(expr_matched, "")
        cleaned_query = re.sub(r'\s+', ' ', cleaned).strip()
        result = {
            "original_query": query,
            "time_info": {
                "start_date": start_date,
                "end_date": end_date,
                "is_range": start_date != end_date,
                "raw_expression": expr_matched
            },
            "locations": ner_res["locations"],
            "cleaned_query": cleaned_query,
            "date": start_date,
            "date_expr": expr_matched or "today",
        }

        if start_date != end_date:
            result["date_range"] = {"start": start_date, "end": end_date}

        return result


