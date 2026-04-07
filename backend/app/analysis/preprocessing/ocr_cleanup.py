"""
OCR Cleanup Module — aggressive noise removal and text repair for food label OCR.

Handles messy mobile-phone OCR on food packaging:
  - Fragmented characters and words
  - Random symbol injection
  - Broken line splits mid-word
  - Mixed nutritional table data with ingredient text
  - Garbled character sequences
"""
from __future__ import annotations

import re
from typing import List, Tuple

from .normalize import build_line_candidates, normalize_text

# ── Noise patterns ──────────────────────────────────────────────────────────

GARBAGE_LINE_RE = re.compile(
    r"^[\s\W\d]{0,3}$"
    r"|^[^\w]*$"
    r"|^(.)\1{3,}$"
    r"|^\W+\s*\W+$"
)

SHORT_CONTINUATION_RE = re.compile(
    r"^(?:ve|veya|with|and|or|contains|içerir|içermektedir|içerebilir"
    r"|may contain|eser miktarda|iz miktarda"
    r"|ile|olan|from|of)\b",
    re.IGNORECASE,
)

NOISE_CHARS_RE = re.compile(r"[§¶†‡°¤¥£€¢©®™¬¦×÷±∞≈≠≤≥∆∑∏√∫µ∂ƒ∅∩∪⊂⊃⊆⊇⊕⊗⊥∴∵∇]")
MULTI_SPECIAL_RE = re.compile(r"[^\w\s,;:.()%/\-]{2,}")

# ── Broken keyword repair ───────────────────────────────────────────────────

BROKEN_ICINDEKILER_PATTERNS = [
    (re.compile(r"[iİıI]\s*[cçCÇ]\s*[iİıI]\s*n\s*d\s*e\s*k\s*[iİıI]\s*l\s*e\s*r", re.IGNORECASE), "İçindekiler"),
    (re.compile(r"\b[iı]?\s*ndeki(?:ler)?\b", re.IGNORECASE), "İçindekiler"),
    (re.compile(r"\biindeki(?:ler)?\b", re.IGNORECASE), "İçindekiler"),
    (re.compile(r"[iİ][çc]in\s+d\s*eki(?:ler)?", re.IGNORECASE), "İçindekiler"),
    (re.compile(r"[IİiıÎ][CÇcç][IİiıÎ]NDEK[IİiıÎ](?:LER)?", re.IGNORECASE), "İçindekiler"),
    (re.compile(r"\b[iI]?C[IİiıÎ]NDEK[IİiıÎ](?:LER)?\b"), "İçindekiler"),
]

BROKEN_INGREDIENTS_PATTERNS = [
    (re.compile(r"[iI]\s*n\s*g\s*r\s*e\s*d\s*i\s*e\s*n\s*t\s*s?", re.IGNORECASE), "Ingredients"),
]


def _repair_broken_keywords(text: str) -> str:
    result = text
    for pattern, replacement in BROKEN_ICINDEKILER_PATTERNS:
        result = pattern.sub(replacement, result)
    for pattern, replacement in BROKEN_INGREDIENTS_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def _remove_noise_chars(text: str) -> str:
    text = NOISE_CHARS_RE.sub(" ", text)
    text = MULTI_SPECIAL_RE.sub(" ", text)
    text = re.sub(r"(?<=\s)[^\w\s](?=\s)", " ", text)
    return text


def _is_garbage_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if len(stripped) <= 2 and not stripped.isalpha():
        return True
    if GARBAGE_LINE_RE.match(stripped):
        return True
    letters = sum(1 for c in stripped if c.isalpha())
    if len(stripped) > 5 and letters / len(stripped) < 0.3:
        return True
    return False


def _merge_fragmented_words(text: str) -> str:
    """Merge single characters that OCR fragmented (e.g. 'b u ğ d a y' -> 'buğday')."""
    def _merge_singles(match: re.Match) -> str:
        return match.group(0).replace(" ", "")

    text = re.sub(
        r"(?<!\w)(\S\s){2,}\S(?!\w)",
        _merge_singles,
        text,
    )
    return text


def merge_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    for line in lines:
        if not merged:
            merged.append(line)
            continue

        prev = merged[-1]

        if len(line) <= 30:
            merged[-1] = f"{prev} {line}".strip()
            continue

        if prev.endswith((",", ";", ":", "(", "-")):
            merged[-1] = f"{prev} {line}".strip()
            continue

        if SHORT_CONTINUATION_RE.match(line):
            merged[-1] = f"{prev} {line}".strip()
            continue

        if line and line[0].islower():
            merged[-1] = f"{prev} {line}".strip()
            continue

        merged.append(line)
    return merged


def cleanup_ocr_text(text: str) -> Tuple[str, List[str]]:
    if not text or not text.strip():
        return "", []

    normalized = normalize_text(text)
    normalized = _repair_broken_keywords(normalized)
    normalized = _remove_noise_chars(normalized)
    normalized = _merge_fragmented_words(normalized)
    normalized = re.sub(r"[ ]{2,}", " ", normalized)
    normalized = re.sub(r"([,:;])(?=\S)", r"\1 ", normalized)
    normalized = re.sub(r"\(\s+", "(", normalized)
    normalized = re.sub(r"\s+\)", ")", normalized)

    raw_lines = build_line_candidates(normalized)
    clean_lines = [line for line in raw_lines if not _is_garbage_line(line)]
    merged = merge_lines(clean_lines)

    return normalized, merged
