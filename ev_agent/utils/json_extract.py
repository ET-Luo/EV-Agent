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

    # Fallback: locate a valid JSON object by scanning for balanced braces.
    starts = [m.start() for m in re.finditer(r"\{", text)]
    if not starts:
        raise ValueError("未找到 JSON 对象")

    for i in starts:
        frag = _extract_balanced_object(text, i)
        if frag is None:
            continue
        try:
            return json.loads(frag)
        except Exception:
            continue

    raise ValueError("找到疑似 JSON，但解析失败（可能包含多余文本或不完整）")


def _extract_balanced_object(s: str, start_idx: int) -> str | None:
    """
    Return the smallest substring starting at start_idx that forms a balanced JSON object.
    Handles strings/escapes so braces inside strings don't count.
    """
    if start_idx < 0 or start_idx >= len(s) or s[start_idx] != "{":
        return None
    depth = 0
    in_str = False
    esc = False
    for j in range(start_idx, len(s)):
        ch = s[j]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        else:
            if ch == '"':
                in_str = True
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start_idx : j + 1]
            # ignore other chars
    return None


