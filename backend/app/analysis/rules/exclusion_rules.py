from __future__ import annotations

IGNORE_TOKENS = {
    "enerji", "energy", "protein", "karbonhidrat", "carbohydrate", "fat", "yağ", "yag", "salt", "tuz",
    "kcal", "kj", "besin değerleri", "besin degerleri", "nutrition", "muhafaza", "saklayınız",
    "saklayiniz", "son tüketim", "son tuketim", "parti no", "barcode", "barkod",
    "üretim tarihi", "uretim tarihi", "tett", "adet", "gram", "g", "ml",
    "ürün", "urun", "bu ürün", "bu urun", "bu üründe", "bu urunde",
    "katkıları", "katkilari", "atkıları", "atkilari",
    "eser miktarda", "iz miktarda", "traces of", "may contain", "contains",
    "içerir", "icerir", "içerebilir", "icerebilir", "içermez", "icermez",
    "yoktur", "bulunmaz",
    "aroma verici", "aroma vericiler",
    "renklendirici", "renklendiriciler", "renk verici", "renk vericiler",
    "koruyucu", "koruyucular",
    "emülgatör", "emülgatörler", "emulgator", "emulgatorler",
    "stabilizör", "stabilizörler", "stabilizer", "stabilizers",
}


def should_ignore_candidate(text: str) -> bool:
    lowered = text.lower().strip(" ,;:.)(")
    if not lowered:
        return True
    if lowered in IGNORE_TOKENS:
        return True
    if lowered.isdigit():
        return True
    if len(lowered) <= 1:
        return True
    return False
