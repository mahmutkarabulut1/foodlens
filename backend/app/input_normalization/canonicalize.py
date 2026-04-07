"""
Input Canonicalization — prepare raw OCR/manual text for the analysis pipeline.

Key improvements over the original:
  - Does NOT blindly prepend "İçindekiler:" to all text
  - Uses content analysis to decide if text looks like ingredients
  - Handles edge cases: very short text, pure nutrition tables, garbled OCR
  - Only adds the ingredient header when confident the text IS ingredients
"""
from __future__ import annotations

import re

# Explicit ingredient section headers
CUE_RE = re.compile(
    r'(?:içindekiler|icindekiler|ingredients|ingredient list|bileşenler|bilesenler|içerik|icerik)'
    r'\s*[:：.]?',
    re.IGNORECASE,
)

# Words that are strong signals the text is an ingredient list
INGREDIENT_SIGNAL_WORDS = {
    "şeker", "seker", "süt", "sut", "un", "unu", "yağ", "yag",
    "kakao", "tuz", "aroma", "nişasta", "nisasta", "lesitin",
    "emülgatör", "emulgator", "koruyucu", "renklendirici",
    "sugar", "milk", "flour", "oil", "salt", "water", "cocoa",
    "lecithin", "starch", "flavour", "flavor", "preservative",
    "soya", "gluten", "palm", "bitkisel",
}

# E-code pattern
ECODE_RE = re.compile(r"\be[\s\-]?\d{3,4}[a-z]?\b", re.IGNORECASE)


def _looks_like_ingredient_list(text: str) -> bool:
    """
    Heuristic check: does this text look like an ingredient list?
    Used to decide whether to prepend "İçindekiler:" for the parser.
    """
    lowered = text.lower()
    words = lowered.split()

    # Already has a cue keyword
    if CUE_RE.search(text):
        return False  # Don't need to add one

    # Count ingredient signal words
    signal_count = sum(1 for w in INGREDIENT_SIGNAL_WORDS if w in lowered)

    # Count separators
    separator_count = text.count(",") + text.count(";")

    # Count E-codes
    ecode_count = len(ECODE_RE.findall(text))

    # Strong signal: multiple ingredient words + separators
    if signal_count >= 2 and separator_count >= 2:
        return True

    # E-codes present with separators
    if ecode_count >= 1 and separator_count >= 1:
        return True

    # Short text that's comma-separated (manual entry)
    if len(words) <= 8 and separator_count >= 1:
        return True

    # Single-line comma-separated text
    if "\n" not in text and separator_count >= 2:
        return True

    return False


def canonicalize_analysis_text(text: str) -> str:
    """
    Normalize input text for the analysis pipeline.
    Only prepends "İçindekiler:" when confident the text is an ingredient list
    without an existing header.
    """
    value = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()

    if not value:
        return ""

    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{2,}", "\n", value).strip()

    # If the text already has a cue keyword, pass through as-is
    if CUE_RE.search(value):
        return value

    # If the text looks like an ingredient list without a header, add one
    # This helps the parser's section classifier to properly identify the block
    if _looks_like_ingredient_list(value):
        value = f"İçindekiler: {value}"

    return value
