"""
Anchor Patterns — keyword lists used to identify section types in food labels.

Includes OCR-corrupted variants of common Turkish/English food label keywords.
"""
from __future__ import annotations

import re

INGREDIENT_ANCHORS = [
    "içindekiler", "icindekiler", "ingredients", "ingredient list",
    "bileşenler", "bilesenler", "içerik", "icerik",
    # OCR-corrupted variants found in real data
    "İçindekiler", "iÇiNDEKiLER", "İÇİNDEKİLER",
]

ALLERGEN_ANCHORS = [
    "alerjen", "alerjenler", "allergen", "allergens",
    "alerjen uyarısı", "alerjen uyarisi", "allergen warning",
    "alerjen bilgisi", "alerjen bilgileri",
]

MAY_CONTAIN_ANCHORS = [
    "eser miktarda", "iz miktarda", "iz içerebilir", "iz icerebilir",
    "içerebilir", "icerebilir", "may contain", "may also contain",
    "trace", "traces of", "traces",
    "bulunabilir", "ihtiva edebilir",
]

FREE_FROM_ANCHORS = [
    "içermez", "icermez", "yoktur", "bulunmaz",
    "contains no", "does not contain",
    "free from", "without", "none of",
    "helal", "domuz kaynaklı hiçbir", "domuz kaynakli hicbir",
    "domuz içermez", "domuz icermez",
    "gdo'suz", "gdosuz", "gdo içermez", "gdo icermez",
]

NUTRITION_ANCHORS = [
    "besin değerleri", "besin degerleri", "besin öğeleri", "besin ogeleri",
    "nutrition information", "nutritional information", "nutrition facts",
    "nutritional values", "beslenme bilgileri",
    "energy", "enerji",
    "karbonhidrat", "carbohydrate",
    "protein",
]

STORAGE_ANCHORS = [
    "muhafaza", "saklayınız", "saklayiniz", "saklama", "saklanız",
    "serin ve kuru", "güneş ışığından", "gunes isigindan",
    "son tüketim", "son tuketim", "tett",
    "tavsiye edilen tüketim", "tavsiye edilen tuketim",
    "parti no", "lot number", "batch",
    "üretim tarihi", "uretim tarihi",
    "raf ömrü", "raf omru",
    "açıldıktan sonra", "acildiktan sonra",
]

MANUFACTURER_ANCHORS = [
    "gıda işletmecisi", "gida isletmecisi", "işletmeci", "isletmeci",
    "manufacturer", "importer", "produced by", "made by",
    "üretici", "uretici", "ithalatçı", "ithalatci",
    "dağıtıcı", "dagitici", "distributor",
    "adres", "address",
    "tel", "telefon", "fax",
    "www.", "http",
    "barcode", "barkod",
    "ticaret a.ş", "ticaret a.s",
    "sanayi", "ltd",
]


def contains_any(text: str, anchors: list[str]) -> bool:
    lowered = text.lower()
    return any(anchor in lowered for anchor in anchors)
