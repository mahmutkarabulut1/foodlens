from __future__ import annotations

import re

INGREDIENT_ANCHORS = [
    "içindekiler", "icindekiler", "ingredients", "ingredient list",
    "bileşenler", "bilesenler", "içerik", "icerik",
]
ALLERGEN_ANCHORS = [
    "alerjen", "alerjenler", "allergen", "allergens",
]
MAY_CONTAIN_ANCHORS = [
    "eser miktarda", "iz miktarda", "iz içerebilir", "iz icerebilir",
    "içerebilir", "icerebilir", "may contain", "may also contain", "trace",
]
FREE_FROM_ANCHORS = [
    "içermez", "icermez", "yoktur", "bulunmaz", "contains no", "does not contain",
    "free from", "without", "none of", "helal", "domuz kaynaklı hiçbir",
]
NUTRITION_ANCHORS = [
    "besin değerleri", "besin degerleri", "nutrition information", "nutritional information",
    "energy", "enerji", "karbonhidrat", "protein", "yağ", "yag", "salt", "tuz",
]
STORAGE_ANCHORS = [
    "muhafaza", "saklayınız", "saklama", "serin ve kuru", "güneş ışığından", "gunes isigindan",
    "son tüketim", "tett", "tavsiye edilen tüketim", "parti no", "lot number",
]
MANUFACTURER_ANCHORS = [
    "gıda işletmecisi", "gida isletmecisi", "işletmeci", "manufacturer", "importer",
    "adres", "istanbul", "ankara", "tel", "www.", "barcode", "barkod",
]


def contains_any(text: str, anchors: list[str]) -> bool:
    lowered = text.lower()
    return any(anchor in lowered for anchor in anchors)
