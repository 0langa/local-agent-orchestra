from __future__ import annotations

import json


def extract_json_object(raw_text: str) -> str:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output.")
    return raw_text[start : end + 1]


def repair_json_text(raw_text: str) -> str:
    candidate = extract_json_object(raw_text).strip()
    json.loads(candidate)
    return candidate