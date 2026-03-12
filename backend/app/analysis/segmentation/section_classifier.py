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

INGREDIENT_CUES = [
    "şeker", "seker", "su", "süt", "sut", "milk", "water", "flour", "unu", "un",
    "yağ", "yag", "oil", "palm", "citric", "asit", "acid", "aroma", "flavour",
    "kakao", "cocoa", "lesitin", "lecithin", "sorbat", "benzoat", "nişasta", "nisasta",
    "syrup", "şurup", "surup", "glucose", "glikoz", "meyve", "fruit", "emülgatör",
    "emulgator", "renklendirici", "koruyucu",
]


def ingredient_cue_count(line: str) -> int:
    lowered = line.lower()
    return sum(1 for cue in INGREDIENT_CUES if cue in lowered)


def classify_line(line: str) -> tuple[str, str]:
    lowered = line.lower()
    cue_count = ingredient_cue_count(lowered)
    comma_count = line.count(",") + line.count(";")
    has_ecode = bool(ECODE_RE.search(line))

    if contains_any(lowered, INGREDIENT_ANCHORS):
        return "ingredient_section", "ingredient"

    if contains_any(lowered, FREE_FROM_ANCHORS):
        return "free_from_section", "free_from"

    if contains_any(lowered, MAY_CONTAIN_ANCHORS):
        return "may_contain_section", "may_contain"

    if contains_any(lowered, ALLERGEN_ANCHORS):
        return "allergen_section", "allergen"

    if contains_any(lowered, NUTRITION_ANCHORS):
        if cue_count >= 3 and comma_count >= 2:
            return "ingredient_section", "nutrition_mixed_with_ingredients"
        return "nutrition_section", "nutrition"

    if contains_any(lowered, STORAGE_ANCHORS):
        return "storage_section", "storage"

    if contains_any(lowered, MANUFACTURER_ANCHORS):
        return "manufacturer_section", "manufacturer"

    if has_ecode and comma_count >= 1:
        return "ingredient_section", "ecode_dense"

    if comma_count >= 2 and cue_count >= 2:
        return "ingredient_section", "comma_dense"

    return "misc_section", ""
