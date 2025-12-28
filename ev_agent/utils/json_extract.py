from __future__ import annotations

import json
import re


def extract_first_json_object(text: str) -> dict:
    """
    Extract the first JSON object from model output.

    Supported:
    - ```json { ... } ```
    - raw { ... } with extra text around
    """
    # Prefer fenced json blocks
    fenced = re.search(r"```json\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1).strip()
        return json.loads(candidate)

    # Fallback: find first {...} span (best-effort)
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("未找到 JSON 对象")
    return json.loads(m.group(0))


