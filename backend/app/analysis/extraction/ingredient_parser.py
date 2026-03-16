from __future__ import annotations

import re
from typing import List

from ..preprocessing.normalize import normalize_for_matching
from ..schemas import CandidateSpan, TextBlock

INGREDIENT_HEADER_RE = re.compile(
    r"\b(içindekiler|icindekiler|ingredients|ingredient list|bileşenler|bilesenler|içerik|icerik)\b\s*[:.]?",
    re.IGNORECASE,
)

SKIP_FRAGMENT_RE = re.compile(
    r"\b(iz miktarda|eser miktarda|may contain|içerebilir|icerebilir|içermez|icermez|yoktur|bulunmaz)\b",
    re.IGNORECASE,
)

PERCENT_RE = re.compile(r"\b\d+(?:[.,]\d+)?\s*%")
ONLY_NONWORD_RE = re.compile(r"^[\W_]+$")
HAS_LETTER_RE = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşü]")

BRACKET_TRANSLATION = str.maketrans({
    "(": ",",
    ")": ",",
    "[": ",",
    "]": ",",
    "{": ",",
    "}": ",",
    "（": ",",
    "）": ",",
    "【": ",",
    "】": ",",
    "〔": ",",
    "〕": ",",
    "［": ",",
    "］": ",",
    "｛": ",",
    "｝": ",",
    "<": ",",
    ">": ",",
    "〈": ",",
    "〉": ",",
    "«": ",",
    "»": ",",
})

SEPARATOR_RE = re.compile(r"[,;\n/|•·]+")
MULTISPACE_RE = re.compile(r"\s+")
EDGE_PUNCT_RE = re.compile(r"^[\s\-–—:;,.]+|[\s\-–—:;,.]+$")


def _prepare_text(text: str) -> str:
    value = str(text or "")
    value = INGREDIENT_HEADER_RE.sub("", value)
    value = value.translate(BRACKET_TRANSLATION)
    value = value.replace(";", ",").replace("/", ",").replace("|", ",")
    value = re.sub(r"\s*,\s*", ",", value)
    value = MULTISPACE_RE.sub(" ", value).strip()
    return value


def _clean_fragment(fragment: str) -> str:
    value = str(fragment or "")
    value = PERCENT_RE.sub("", value)
    value = EDGE_PUNCT_RE.sub("", value)
    value = MULTISPACE_RE.sub(" ", value).strip()
    return value


def extract_from_ingredient_block(block: TextBlock) -> List[CandidateSpan]:
    prepared = _prepare_text(block.raw_text)
    raw_fragments = SEPARATOR_RE.split(prepared)

    spans: List[CandidateSpan] = []
    seen = set()

    for raw in raw_fragments:
        cleaned = _clean_fragment(raw)

        if not cleaned:
            continue

        if ONLY_NONWORD_RE.match(cleaned):
            continue

        if not HAS_LETTER_RE.search(cleaned):
            continue

        if SKIP_FRAGMENT_RE.search(cleaned):
            continue

        normalized = normalize_for_matching(cleaned)
        if not normalized or len(normalized) < 2:
            continue

        if normalized in seen:
            continue
        seen.add(normalized)

        spans.append(
            CandidateSpan(
                raw_text=cleaned,
                normalized_text=normalized,
                section_type=block.section_type,
                polarity="present",
                category_hint="ingredient",
                evidence=block.raw_text,
            )
        )

    return spans
