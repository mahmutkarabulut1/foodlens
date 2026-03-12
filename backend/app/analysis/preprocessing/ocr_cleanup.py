from __future__ import annotations

import re

from .normalize import build_line_candidates, normalize_text


SHORT_CONTINUATION_RE = re.compile(
    r"^(ve|veya|with|and|or|contains|içerir|içermektedir|içerebilir|may contain|eser miktarda)\b",
    re.IGNORECASE,
)


def merge_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    for line in lines:
        if not merged:
            merged.append(line)
            continue

        prev = merged[-1]
        if len(line) <= 24:
            merged[-1] = f"{prev} {line}".strip()
            continue

        if prev.endswith((",", ";", ":", "(")):
            merged[-1] = f"{prev} {line}".strip()
            continue

        if SHORT_CONTINUATION_RE.match(line):
            merged[-1] = f"{prev} {line}".strip()
            continue

        merged.append(line)
    return merged


def cleanup_ocr_text(text: str) -> tuple[str, list[str]]:
    normalized = normalize_text(text)
    normalized = re.sub(r"[ ]{2,}", " ", normalized)
    normalized = re.sub(r"([,:;])(?=\S)", r"\1 ", normalized)
    normalized = re.sub(r"\(\s+", "(", normalized)
    normalized = re.sub(r"\s+\)", ")", normalized)
    lines = merge_lines(build_line_candidates(normalized))
    return normalized, lines
