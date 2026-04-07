from __future__ import annotations

ALLERGEN_CATALOG: dict[str, list[str]] = {
    "Süt ve Süt Ürünleri": [
        "süt", "sut", "süt tozu", "sut tozu", "laktoz", "lactose",
        "kazein", "casein", "whey", "peynir", "yoğurt", "yogurt",
        "tereyağı", "tereyagi", "krema", "milk", "milk powder",
        "milk protein", "butter", "buttermilk"
    ],
    "Gluten (Buğday, Arpa, vb.)": [
        "gluten", "buğday", "bugday", "buğday unu", "bugday unu",
        "arpa", "çavdar", "cavdar", "yulaf", "irmik", "semolina",
        "malt", "wheat", "wheat flour", "barley", "rye", "oat"
    ],
    "Yer Fıstığı": [
        "yer fıstığı", "yer fistigi", "yer fıstık", "yer fistik",
        "yer fıstığı ezmesi", "yer fistigi ezmesi",
        "fıstık ezmesi", "fistik ezmesi",
        "peanut", "peanuts", "peanut butter",
        "groundnut", "groundnuts", "arachis"
    ],
    "Sert Kabuklu Yemişler (Fındık, Antep Fıstığı vb.)": [
        "fındık", "findik", "badem", "ceviz", "kaju",
        "antep fıstığı", "antep fistigi", "antep fıstık", "antep fistik",
        "hazelnut", "almond", "walnut", "cashew",
        "pistachio", "pecan", "macadamia", "nut paste",
        "antep fistigi ezmesi"
    ],
    "Soya Fasulyesi": [
        "soya", "soy", "soya proteini", "soy protein",
        "soya unu", "soy flour", "soya lesitini", "soy lecithin",
        "tofu", "edamame"
    ],
    "Yumurta": [
        "yumurta", "egg", "albumin", "albumen", "ovalbumin",
        "egg white", "egg yolk", "lysozyme"
    ],
    "Balık": [
        "balık", "balik", "fish", "fish oil", "fish gelatin",
        "somon", "salmon", "ton balığı", "ton baligi", "tuna",
        "hamsi", "anchovy"
    ],
    "Deniz Kabukluları": [
        "karides", "shrimp", "prawn", "midye", "mussel",
        "yengeç", "yengec", "crab", "istakoz", "lobster",
        "clam", "oyster", "kalamar", "squid"
    ],
    "Susam": [
        "susam", "sesame", "tahin", "tahini", "susam ezmesi"
    ],
    "Kereviz": [
        "kereviz", "celery", "celeriac", "celery root"
    ],
    "Hardal": [
        "hardal", "mustard", "mustard seed", "mustard flour"
    ],
    "Kükürt Dioksit ve Sülfitler": [
        "sülfit", "sulfit", "sulfite", "sulphite",
        "kükürt dioksit", "kukurt dioksit", "sulfur dioxide",
        "potassium metabisulfite", "sodium metabisulfite"
    ],
    "Acı Bakla (Lüpen)": [
        "lüpen", "lupen", "lupin", "lupine", "lupin flour"
    ],
}


def get_aliases_for_allergen(allergen_name: str) -> list[str]:
    aliases = ALLERGEN_CATALOG.get(allergen_name)
    if aliases:
        return aliases
    return [allergen_name]
