"""
Exclusion Rules — filter out candidates that are not real ingredients.

Filters:
  - Nutritional table terms (kcal, protein, etc.)
  - Functional role terms without specific substance (emülgatör, koruyucu, etc.)
  - Storage/packaging instructions
  - Manufacturer/address fragments
  - OCR noise fragments
  - Generic/structural words
"""
from __future__ import annotations

import re

IGNORE_TOKENS = {
    # Nutritional terms
    "enerji", "energy", "protein", "karbonhidrat", "carbohydrate", "carbohydrates",
    "fat", "yağ", "yag", "salt", "tuz", "lif", "fibre", "fiber",
    "kcal", "kj", "besin değerleri", "besin degerleri", "nutrition",
    "nutritional", "calories", "kalori",
    "doymuş yağ", "doymus yag", "saturates", "saturated",
    "şeker", "sugars", "of which sugars", "trans yağ", "trans yag",

    # Storage/packaging terms
    "muhafaza", "saklayınız", "saklayiniz", "saklanız", "saklaniniz",
    "son tüketim", "son tuketim", "parti no", "barcode", "barkod",
    "üretim tarihi", "uretim tarihi", "tett", "skt",
    "tavsiye edilen", "ambalaj", "paket", "kutu",
    "serin ve kuru", "buzdolabı", "buzdolabi",

    # Units and measures
    "adet", "gram", "g", "ml", "kg", "lt", "mg", "porsiyon", "serving",

    # Structural/generic terms
    "ürün", "urun", "bu ürün", "bu urun", "bu üründe", "bu urunde",
    "product", "this product", "ürünümüz", "urunumuz",

    # Claim-related stopwords (these are structural, not ingredient names)
    "eser miktarda", "iz miktarda", "traces of", "may contain", "contains",
    "içerir", "icerir", "içerebilir", "icerebilir", "içermez", "icermez",
    "yoktur", "bulunmaz", "does not contain", "free from",

    # Role terms (not ingredients themselves)
    "aroma verici", "aroma vericiler", "flavouring", "flavourings",
    "renklendirici", "renklendiriciler", "renk verici", "renk vericiler",
    "koruyucu", "koruyucular", "preservative", "preservatives",
    "emülgatör", "emülgatörler", "emulgator", "emulgatorler",
    "emulsifier", "emulsifiers",
    "stabilizör", "stabilizörler", "stabilizer", "stabilizers",
    "tatlandırıcı", "tatlandırıcılar", "sweetener", "sweeteners",
    "kabartıcı", "kabartıcılar", "raising agent", "raising agents",
    "kıvam arttırıcı", "kivam arttirici", "thickener", "thickeners",
    "antioksidan", "antioksidanlar", "antioxidant", "antioxidants",
    "asitlik düzenleyici", "asitlik duzenleyici",
    "acidity regulator", "acidity regulators",

    # Address/manufacturer fragments
    "tel", "fax", "adres", "address", "manufacturer",
    "üretici", "uretici", "dağıtıcı", "dagitici",
    "gıda işletmecisi", "gida isletmecisi",
    "ticaret", "sanayi", "ltd", "şti", "sti",
}

# Patterns that indicate non-ingredient content
NOISE_PATTERNS = [
    re.compile(r"^\d+[.,]?\d*\s*(?:g|mg|ml|kg|l|kcal|kj)$", re.IGNORECASE),  # Pure measurement
    re.compile(r"^(?:www\.|http|\.com|\.tr|\.net)", re.IGNORECASE),             # URLs
    re.compile(r"^\+?\d[\d\s\-]{6,}$"),                                         # Phone numbers
    re.compile(r"^\d{4,}$"),                                                     # Long number sequences
    re.compile(r"^(?:ref|lot|batch|no|seri)\s*[:.]?\s*\d", re.IGNORECASE),      # Batch/lot numbers
]


def should_ignore_candidate(text: str) -> bool:
    """Check if a candidate text should be filtered out."""
    lowered = text.lower().strip(" ,;:.)(")

    if not lowered:
        return True

    if lowered in IGNORE_TOKENS:
        return True

    if lowered.isdigit():
        return True

    if len(lowered) <= 1:
        return True

    # Check noise patterns
    for pattern in NOISE_PATTERNS:
        if pattern.match(lowered):
            return True

    # Very long text without separators is probably a sentence, not an ingredient
    if len(lowered) > 80 and "," not in lowered and ";" not in lowered:
        return True

    return False
