"""
Ingredient Parser — extract individual ingredient spans from ingredient blocks.

Key improvements:
  - Handles nested parenthetical sub-ingredients (e.g. "bitkisel yağ (palm, ayçiçek)")
  - Strips role prefixes ("emülgatör: soya lesitini" -> extracts "soya lesitini")
  - Handles percentage noise gracefully
  - Recovers from corrupted/missing separators using heuristics
  - Extracts E-codes as standalone items even when embedded in garbled text
"""
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

PERCENT_RE = re.compile(r"\(?\s*%\s*\d+[.,]?\d*\s*\)?|\b\d+[.,]?\d*\s*%")
ONLY_NONWORD_RE = re.compile(r"^[\W_]+$")
HAS_LETTER_RE = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşü]")

# E-code pattern — extract these even from garbled text
ECODE_RE = re.compile(r"\b(e[\s\-]?\d{3,4}[a-z]?)\b", re.IGNORECASE)

# Role prefixes that precede the actual ingredient name
ROLE_PREFIX_RE = re.compile(
    r"^(?:emülgatör(?:ler)?|emulgator(?:ler)?|koruyucu(?:lar)?|renklendirici(?:ler)?|"
    r"renk verici(?:ler)?|tatlandırıcı(?:lar)?|tatlandirici(?:lar)?|"
    r"kabartıcı(?:lar)?|kabartici(?:lar)?|stabilizör(?:ler)?|stabilizer(?:s)?|"
    r"kıvam arttırıcı(?:lar)?|kivam arttirici(?:lar)?|antioksidan(?:lar)?|"
    r"aroma verici(?:ler)?|asitlik düzenleyici(?:ler)?|asitlik duzenleyici(?:ler)?|"
    r"acidity regulator(?:s)?|raising agent(?:s)?|thickener(?:s)?|"
    r"preservative(?:s)?|emulsifier(?:s)?|colour(?:s)?|color(?:s)?|"
    r"sweetener(?:s)?|flavouring(?:s)?|flavoring(?:s)?|antioxidant(?:s)?)\s*[:(\-]?\s*",
    re.IGNORECASE,
)

# Nutritional noise patterns that slip into ingredient blocks
NUTRITION_NOISE_RE = re.compile(
    r"(?:"
    r"\b\d+\s*(?:kcal|kj)\b"
    r"|\b(?:enerji|energy)\s*/\s*(?:energy|enerji)"
    r"|\bbesin\s+(?:öğeleri|değer)"
    r"|\bnutrition(?:al)?\s+(?:information|facts|value)"
    r"|\bper\s+\d+\s*(?:g|ml)\b"
    r"|\b\d+\s*g\s+\d+\s*g\b"  # "14g 2g" table values
    r")",
    re.IGNORECASE,
)

# All bracket types -> commas for splitting
BRACKET_TRANSLATION = str.maketrans({
    "[": ",", "]": ",",
    "{": ",", "}": ",",
    "（": ",", "）": ",",
    "【": ",", "】": ",",
    "〔": ",", "〕": ",",
    "［": ",", "］": ",",
    "｛": ",", "｝": ",",
    "«": ",", "»": ",",
})

SEPARATOR_RE = re.compile(r"[,;]+")
MULTISPACE_RE = re.compile(r"\s+")
EDGE_PUNCT_RE = re.compile(r"^[\s\-–—:;,.]+|[\s\-–—:;,.]+$")


def _flatten_parentheticals(text: str) -> str:
    """
    Convert parenthetical sub-ingredients into comma-separated items.
    "bitkisel yağ (palm, ayçiçek)" -> "bitkisel yağ, palm, ayçiçek"
    But preserve E-code parentheticals: "(E330)" -> "E330"
    """
    result = []
    depth = 0
    current = []

    for ch in text:
        if ch == "(":
            depth += 1
            if depth == 1:
                # Flush what we have before the paren
                result.append("".join(current).strip())
                current = []
                result.append(",")
                continue
            current.append(ch)
        elif ch == ")":
            depth -= 1
            if depth == 0:
                inner = "".join(current).strip()
                if inner:
                    result.append(inner)
                    result.append(",")
                current = []
                continue
            current.append(ch)
        else:
            current.append(ch)

    remaining = "".join(current).strip()
    if remaining:
        result.append(remaining)

    return "".join(result)


def _prepare_text(text: str) -> str:
    """Prepare raw ingredient block text for splitting."""
    value = str(text or "")

    # Remove ingredient headers
    value = INGREDIENT_HEADER_RE.sub("", value)

    # Remove nutritional noise that leaked into ingredient blocks
    value = NUTRITION_NOISE_RE.sub(" ", value)

    # Flatten parentheticals into comma-separated items
    value = _flatten_parentheticals(value)

    # Translate remaining brackets
    value = value.translate(BRACKET_TRANSLATION)

    # Normalize separators
    value = value.replace(";", ",").replace("|", ",")
    value = re.sub(r"\s*,\s*", ",", value)
    value = MULTISPACE_RE.sub(" ", value).strip()

    return value


def _clean_fragment(fragment: str) -> str:
    """Clean a single ingredient fragment."""
    value = str(fragment or "")

    # Remove percentage values
    value = PERCENT_RE.sub("", value)

    # Strip role prefixes: "emülgatör: soya lesitini" -> "soya lesitini"
    value = ROLE_PREFIX_RE.sub("", value)

    # Clean edges
    value = EDGE_PUNCT_RE.sub("", value)
    value = MULTISPACE_RE.sub(" ", value).strip()

    return value


def _extract_ecodes_from_text(text: str) -> List[str]:
    """Extract all E-codes from raw text as standalone items."""
    matches = ECODE_RE.findall(text)
    # Normalize: remove spaces/hyphens, uppercase E
    ecodes = []
    for m in matches:
        normalized = re.sub(r"[\s\-]", "", m).upper()
        if normalized.startswith("E") and len(normalized) >= 4:
            ecodes.append(normalized)
    return list(set(ecodes))


def _is_noise_fragment(text: str) -> bool:
    """Check if a fragment is noise that should be filtered out."""
    if not text:
        return True
    if ONLY_NONWORD_RE.match(text):
        return True
    if not HAS_LETTER_RE.search(text):
        return True
    if len(text) < 2:
        return True
    # Pure numbers with optional units
    if re.match(r"^\d+[.,]?\d*\s*(?:g|mg|ml|kg|l)?$", text, re.IGNORECASE):
        return True
    return False


def extract_from_ingredient_block(block: TextBlock) -> List[CandidateSpan]:
    """
    Extract candidate ingredient spans from an ingredient section block.
    """
    raw_text = block.raw_text
    prepared = _prepare_text(raw_text)
    raw_fragments = SEPARATOR_RE.split(prepared)

    spans: List[CandidateSpan] = []
    seen_normalized = set()
    seen_ecodes = set()

    # First pass: split by separators and process each fragment
    for raw in raw_fragments:
        cleaned = _clean_fragment(raw)

        if not cleaned:
            continue

        if _is_noise_fragment(cleaned):
            continue

        if SKIP_FRAGMENT_RE.search(cleaned):
            continue

        normalized = normalize_for_matching(cleaned)
        if not normalized or len(normalized) < 2:
            continue

        if normalized in seen_normalized:
            continue
        seen_normalized.add(normalized)

        # Track E-codes we've already added via fragments
        ecode_match = re.match(r"^e\s*\d{3,4}[a-z]?$", normalized, re.IGNORECASE)
        if ecode_match:
            seen_ecodes.add(re.sub(r"\s", "", normalized).lower())

        spans.append(
            CandidateSpan(
                raw_text=cleaned,
                normalized_text=normalized,
                section_type=block.section_type,
                polarity="present",
                category_hint="ingredient",
                evidence=raw_text,
            )
        )

    # Second pass: extract E-codes directly from raw text
    # This catches E-codes that were embedded in garbled text and not properly separated
    for ecode in _extract_ecodes_from_text(raw_text):
        ecode_lower = ecode.lower()
        if ecode_lower in seen_ecodes:
            continue
        seen_ecodes.add(ecode_lower)

        normalized = normalize_for_matching(ecode)
        if normalized in seen_normalized:
            continue
        seen_normalized.add(normalized)

        spans.append(
            CandidateSpan(
                raw_text=ecode,
                normalized_text=normalized,
                section_type=block.section_type,
                polarity="present",
                category_hint="additive",
                evidence=raw_text,
            )
        )

    return spans
