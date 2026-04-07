from __future__ import annotations

import re
from typing import List

from ..schemas import CandidateSpan, TextBlock
from ..preprocessing.normalize import normalize_for_matching
from ..rules.exclusion_rules import should_ignore_candidate

NEGATIVE_PATTERNS = [
    re.compile(r"(.+?)\b(?:içermez|icermez|yoktur|bulunmaz)\b", re.IGNORECASE),
    re.compile(r"(?:does not contain|contains no|free from)\s+(.+)", re.IGNORECASE),
]

MAY_CONTAIN_PATTERNS = [
    re.compile(r"(?:eser miktarda|iz miktarda)\s+(.+?)\s+içerebilir", re.IGNORECASE),
    re.compile(r"may contain(?: traces of)?\s+(.+)", re.IGNORECASE),
    re.compile(r"traces of\s+(.+)", re.IGNORECASE),
    re.compile(r"(.+?)\s+içerebilir", re.IGNORECASE),
]

PRESENCE_PATTERNS = [
    re.compile(r"(.+?)\s+içermektedir", re.IGNORECASE),
    re.compile(r"(.+?)\s+içerir", re.IGNORECASE),
    re.compile(r"contains\s+(.+)", re.IGNORECASE),
]

INTRO_PREFIX_RE = re.compile(
    r"^(?:bu ürün(?:de)?|bu urun(?:de)?|ürün(?:de)?|urun(?:de)?|ürünümüzde|urunumuzde|"
    r"this product|product|üründe|urunde|içeriğinde|iceriginde|"
    r"alerjen uyarısı|alerjen uyarisi|allergen warning|allergens?)\s*[:\-]?\s*",
    re.IGNORECASE,
)

MAY_PREFIX_RE = re.compile(
    r"^(?:eser miktarda|iz miktarda|traces of|trace of|may contain)\s+",
    re.IGNORECASE,
)

TAIL_VERB_RE = re.compile(
    r"\b(içerir|icerir|içermektedir|icermektedir|içerebilir|icerebilir|"
    r"içermez|icermez|yoktur|bulunmaz|contains|does not contain)\b",
    re.IGNORECASE,
)


def cleanup_claim_segment(text: str, polarity: str) -> str:
    text = text.strip(" -:;,.")
    text = INTRO_PREFIX_RE.sub("", text)
    if polarity == "may_contain":
        text = MAY_PREFIX_RE.sub("", text)
    text = TAIL_VERB_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" -:;,.")
    return text


def split_claim_items(text: str, polarity: str) -> List[str]:
    text = cleanup_claim_segment(text, polarity)
    parts = re.split(r",|/|\bve\b|\band\b", text, flags=re.IGNORECASE)
    cleaned = []
    for part in parts:
        item = cleanup_claim_segment(part, polarity)
        if item:
            cleaned.append(item)
    return cleaned


def build_spans(items: List[str], block: TextBlock, polarity: str, category_hint: str) -> List[CandidateSpan]:
    spans: List[CandidateSpan] = []
    for item in items:
        item = cleanup_claim_segment(item, polarity)
        if should_ignore_candidate(item):
            continue
        spans.append(
            CandidateSpan(
                raw_text=item,
                normalized_text=normalize_for_matching(item),
                section_type=block.section_type,
                polarity=polarity,
                category_hint=category_hint,
                evidence=block.raw_text,
            )
        )
    return spans


def extract_claim_spans(block: TextBlock) -> List[CandidateSpan]:
    text = block.raw_text
    results: List[CandidateSpan] = []

    if block.section_type == "free_from_section":
        for pattern in NEGATIVE_PATTERNS:
            for match in pattern.finditer(text):
                segment = match.group(1).strip()
                results.extend(build_spans(split_claim_items(segment, "absent"), block, "absent", "ingredient"))
        return results

    if block.section_type == "may_contain_section":
        for pattern in MAY_CONTAIN_PATTERNS:
            for match in pattern.finditer(text):
                segment = match.group(1).strip()
                results.extend(build_spans(split_claim_items(segment, "may_contain"), block, "may_contain", "allergen"))
        return results

    if block.section_type == "allergen_section":
        lowered = text.lower()

        if "alerjen" in lowered or "allergen" in lowered:
            segment = re.split(r"[:.]", text, maxsplit=1)
            target = segment[1] if len(segment) > 1 else text
            results.extend(build_spans(split_claim_items(target, "present"), block, "present", "allergen"))

        for pattern in PRESENCE_PATTERNS:
            for match in pattern.finditer(text):
                segment = match.group(1).strip()
                results.extend(build_spans(split_claim_items(segment, "present"), block, "present", "allergen"))
        return results

    return results
