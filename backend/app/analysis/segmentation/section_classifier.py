"""
Section Classifier — determines what type of content each OCR line represents.

Key improvement: detects ingredient content even when OCR destroyed the
'İçindekiler' keyword, by using a scoring system based on:
  - Comma/separator density
  - Known ingredient word presence
  - E-code patterns
  - Percentage patterns (ingredient ratios)
  - Parenthetical sub-ingredients
  - Absence of nutritional-table-only patterns
"""
from __future__ import annotations

import re

from .anchors import (
    ALLERGEN_ANCHORS,
    FREE_FROM_ANCHORS,
    INGREDIENT_ANCHORS,
    MANUFACTURER_ANCHORS,
    MAY_CONTAIN_ANCHORS,
    NUTRITION_ANCHORS,
    STORAGE_ANCHORS,
    contains_any,
)

ECODE_RE = re.compile(r"\be[\s\-]?\d{3,4}[a-z]?\b", re.IGNORECASE)

# ── Ingredient cue words (Turkish + English) ────────────────────────────────
# These are words that commonly appear in ingredient lists but rarely in
# nutritional tables, storage instructions, or manufacturer info.

INGREDIENT_CUES = [
    # Turkish common ingredients
    "şeker", "seker", "süt", "sut", "un ", " unu", "buğday", "bugday",
    "yağ", "yag", "palm", "bitkisel", "kakao", "cocoa",
    "tuz", "aroma", "nişasta", "nisasta", "mısır", "misir",
    "lesitin", "lecithin", "peyniraltı", "peynir", "yoğurt", "yogurt",
    "fındık", "findik", "badem", "ceviz", "susam",
    "yumurta", "egg", "soya", "gluten",
    "fruktoz", "glikoz", "glucose", "maltodekstrin",
    "konsantre", "konsantresi", "extract",
    # Turkish functional terms (these appear inside ingredient lists)
    "emülgatör", "emulgator", "stabilizör", "stabilizer",
    "koruyucu", "kabartıcı", "kabartici",
    "renklendirici", "tatlandırıcı", "tatlandirici",
    "antioksidan", "kıvam", "kivam", "jelatin", "gelatin",
    "asitlik düzenleyici", "asitlik duzenleyici",
    # English common ingredients
    "sugar", "milk", "flour", "oil", "water", "salt",
    "starch", "syrup", "butter", "cream", "powder",
    "citric", "acid", "flavour", "flavor", "colour", "color",
    "preservative", "emulsifier", "stabiliser",
    "sorbat", "benzoat", "nitrit", "nitrat", "fosfat",
    # E-code related chemical names
    "sodyum", "potasyum", "kalsiyum", "amonyum",
    "karbonat", "bikarbonat", "hidrojen", "sülfit",
    "askorbik", "tartarik", "malik", "laktik",
    "sodium", "potassium", "calcium",
]

# Words that strongly indicate nutritional table content (not ingredients)
NUTRITION_ONLY_CUES = [
    "kcal", " kj", "besin değer", "besin deger", "nutritional",
    "nutrition facts", "beslenme", "günlük", "gunluk",
    "referans", "reference intake", "daily value",
    "porsiyon", "serving size", "portion",
]

# Patterns that indicate a line is from a nutritional value table
NUTRITION_VALUE_RE = re.compile(
    r"(?:"
    r"\b\d+[.,]?\d*\s*(?:kcal|kj|mg|µg|mcg|g)\b"
    r"|\b(?:enerji|energy)\s*/?\s*(?:energy|enerji)?\s*\d"
    r"|\byağ\s*/\s*fat\b"
    r"|\bprotein\s*/?\s*protein\b"
    r"|\bkarbonhidrat\s*/?\s*carbohydrate"
    r"|\btuz\s*/\s*salt\b"
    r"|\blif\s*/\s*fib(?:re|er)\b"
    r")",
    re.IGNORECASE,
)

# Percentage patterns common in ingredient lists: (%42), %65, (% 12)
INGREDIENT_PERCENT_RE = re.compile(r"[(%]\s*\d+[.,]?\d*\s*%?\s*[)]?")

# Sub-ingredient parentheticals: (buğday unu, şeker, tuz)
SUB_INGREDIENT_PAREN_RE = re.compile(r"\([^)]{5,}(?:,|;)[^)]{3,}\)")


def ingredient_cue_count(line: str) -> int:
    lowered = line.lower()
    return sum(1 for cue in INGREDIENT_CUES if cue in lowered)


def _nutrition_only_score(line: str) -> int:
    """Score how much a line looks like pure nutritional table data."""
    lowered = line.lower()
    score = 0
    score += sum(2 for cue in NUTRITION_ONLY_CUES if cue in lowered)
    if NUTRITION_VALUE_RE.search(line):
        score += 3
    # Lines with "X / Y" bilingual nutritional headers
    if re.search(r"\b\w+\s*/\s*\w+\s+\d", line):
        score += 1
    return score


def _ingredient_content_score(line: str) -> float:
    """
    Score how likely a line is to contain ingredient content.
    Returns a float score; higher = more likely ingredients.
    This is the key function for detecting ingredients without anchor keywords.
    """
    lowered = line.lower()
    score = 0.0

    # Ingredient keyword hits
    cue_hits = ingredient_cue_count(lowered)
    score += cue_hits * 1.5

    # Comma/semicolon density (ingredient lists are comma-heavy)
    separator_count = line.count(",") + line.count(";")
    score += min(separator_count * 0.8, 6.0)

    # E-code presence (strong signal)
    ecode_matches = ECODE_RE.findall(line)
    score += len(ecode_matches) * 2.0

    # Percentage patterns (ingredient ratios)
    pct_matches = INGREDIENT_PERCENT_RE.findall(line)
    score += len(pct_matches) * 1.0

    # Sub-ingredient parentheticals
    sub_matches = SUB_INGREDIENT_PAREN_RE.findall(line)
    score += len(sub_matches) * 2.0

    # Parentheses density (ingredient lists have lots of parens)
    paren_count = line.count("(") + line.count(")")
    score += min(paren_count * 0.3, 2.0)

    # Penalty for nutritional-table-only content
    nutrition_score = _nutrition_only_score(line)
    score -= nutrition_score * 1.5

    # Penalty for very short lines (less likely to be ingredient lists)
    words = line.split()
    if len(words) < 3:
        score -= 2.0

    return score


def classify_line(line: str) -> tuple[str, str]:
    """
    Classify a single line into a section type.
    Returns (section_type, anchor_reason).
    """
    lowered = line.lower()
    cue_count = ingredient_cue_count(lowered)
    comma_count = line.count(",") + line.count(";")
    has_ecode = bool(ECODE_RE.search(line))

    # ── Priority 1: Explicit anchor keywords ──
    if contains_any(lowered, INGREDIENT_ANCHORS):
        return "ingredient_section", "ingredient"

    if contains_any(lowered, FREE_FROM_ANCHORS):
        return "free_from_section", "free_from"

    if contains_any(lowered, MAY_CONTAIN_ANCHORS):
        return "may_contain_section", "may_contain"

    if contains_any(lowered, ALLERGEN_ANCHORS):
        return "allergen_section", "allergen"

    # ── Priority 2: Nutritional table detection ──
    if contains_any(lowered, NUTRITION_ANCHORS):
        # But check if ingredients are mixed in
        if cue_count >= 3 and comma_count >= 2:
            return "ingredient_section", "nutrition_mixed_with_ingredients"
        # Pure nutrition with values
        if _nutrition_only_score(line) >= 3:
            return "nutrition_section", "nutrition"
        # Nutrition header but could still be ingredients
        if cue_count >= 2 and comma_count >= 1:
            return "ingredient_section", "nutrition_mixed_with_ingredients"
        return "nutrition_section", "nutrition"

    if contains_any(lowered, STORAGE_ANCHORS):
        return "storage_section", "storage"

    if contains_any(lowered, MANUFACTURER_ANCHORS):
        return "manufacturer_section", "manufacturer"

    # ── Priority 3: Content-based detection (no anchor keyword needed) ──

    # E-code with separators = almost certainly ingredients
    if has_ecode and comma_count >= 1:
        return "ingredient_section", "ecode_dense"

    # High comma density + ingredient keywords = ingredients
    if comma_count >= 2 and cue_count >= 2:
        return "ingredient_section", "comma_dense"

    # Use the scoring system for ambiguous lines
    content_score = _ingredient_content_score(line)

    # Strong ingredient signal even without explicit anchors
    if content_score >= 6.0:
        return "ingredient_section", "content_score_high"

    # Moderate signal: comma-heavy with some ingredient words
    if content_score >= 4.0 and comma_count >= 3:
        return "ingredient_section", "content_score_moderate"

    # Single E-code with ingredient words
    if has_ecode and cue_count >= 1:
        return "ingredient_section", "ecode_with_cues"

    # Lines with many commas and parentheses (sub-ingredient patterns)
    if comma_count >= 4 and line.count("(") >= 1:
        return "ingredient_section", "structure_dense"

    # Lines with percentage patterns and ingredient words
    if INGREDIENT_PERCENT_RE.search(line) and cue_count >= 2:
        return "ingredient_section", "percent_with_cues"

    return "misc_section", ""
