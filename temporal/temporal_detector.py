import re
from typing import Dict, List


class TemporalDetector:

    def __init__(self):
        self.patterns = [
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            r"\b\d{4}-\d{1,2}-\d{1,2}\b",
            r"\b\d{1,2}[/-]\d{1,2}\b",
            r"\bngày\s+\d{1,2}[/-]\d{1,2}"
            r"(?:[/-]\d{2,4})?\b",
            r"\b\d{1,2}\s+tháng\s+\d{1,2}\b",
            r"\btháng\s+\d{1,2}\b",
            r"\bnăm\s+\d{4}\b",
            r"\bngày\s+\d{1,2}\b",
            r"\b\d+\s+(?:giờ|ngày|tuần|tháng|năm)\b",            
            r"\b\d+\s+"
            r"(?:giờ|ngày|tuần|tháng|năm)"
            r"\s+"
            r"(?:tới|đến|qua|trước|sau)\b",
        ]

        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.patterns
        ]

    def detect(self, text: str) -> Dict:
        if not text or not text.strip():
            return {
                "has_temporal": False,
                "expressions": []
            }

        expressions = []
        for pattern in self.compiled_patterns:
            for match in pattern.finditer(text):
                expression = match.group(0).strip()
                expressions.append({
                    "text": expression,
                    "start": match.start(),
                    "end": match.end()  
                })

        expressions = self._remove_duplicates(expressions)
        expressions = self._remove_overlaps(expressions)
        expressions.sort(key=lambda x: x["start"])

        return {
            "has_temporal": len(expressions) > 0,
            "expressions": expressions
        }

    @staticmethod
    def _remove_duplicates(expressions: List[Dict]) -> List[Dict]:
        seen = set()
        result = []
        for item in expressions:
            key = (item["start"], item["end"])
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    @staticmethod
    def _remove_overlaps(expressions: List[Dict]) -> List[Dict]:
        if not expressions:
            return []

        candidates = sorted(expressions,key=lambda x: (-(x["end"] - x["start"]),x["start"]))
        selected = []
        for candidate in candidates:
            overlap = False
            for existing in selected:
                if (
                    candidate["start"] < existing["end"]
                    and candidate["end"] > existing["start"]
                ):
                    overlap = True
                    break
            if not overlap:
                selected.append(candidate)
        return selected

