from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

# Legacy env support:
# - FOODLENS_MASTER_FILE is the new preferred env var
# - FOODLENS_DB_FILE is accepted only if it points to a CSV
_master_env = os.getenv("FOODLENS_MASTER_FILE", "").strip()
_legacy_db_env = os.getenv("FOODLENS_DB_FILE", "").strip()

if _master_env:
    _selected_master = _master_env
elif _legacy_db_env.lower().endswith(".csv"):
    _selected_master = _legacy_db_env
else:
    _selected_master = "foodlens_master_final.csv"

MASTER_CSV_FILE = Path(_selected_master) if Path(_selected_master).is_absolute() else (PROCESSED_DIR / _selected_master)

REFERENCE_ADDITIVES_CSV = PROCESSED_DIR / os.getenv("FOODLENS_REFERENCE_ADDITIVES_FILE", "reference_additives.csv")
REFERENCE_ALLERGENS_CSV = PROCESSED_DIR / os.getenv("FOODLENS_REFERENCE_ALLERGENS_FILE", "reference_allergens.csv")
REFERENCE_INGREDIENTS_CSV = PROCESSED_DIR / os.getenv("FOODLENS_REFERENCE_INGREDIENTS_FILE", "reference_ingredients.csv")

# Backward compatibility for existing imports in matcher_engine.py
DB_FILE = MASTER_CSV_FILE

STOP_ALIASES_RAW = {
    "", "unknown", "bilinmiyor", "belirsiz", "none", "n/a", "na", "null", "yok"
}

ROLE_TERMS_RAW = {
    "içindekiler", "icindekiler", "ingredients", "bileşenler",
    "koruyucu", "koruyucular", "asitlik düzenleyici", "asitlik düzenleyiciler",
    "renklendirici", "renklendiriciler", "renk verici", "renk vericiler",
    "emülgatör", "emülgatörler", "emulgator", "emulgators",
    "stabilizör", "stabilizörler", "stabilizer", "stabilizers",
    "tatlandırıcı", "tatlandırıcılar", "sweetener", "sweeteners",
    "kabartıcı", "kabartıcılar", "raising agent", "raising agents",
    "kıvam arttırıcı", "kıvam arttırıcılar", "thickener", "thickeners",
    "aroma verici", "aroma vericiler", "flavouring", "flavourings",
    "flavoring", "flavorings", "antioksidan", "antioksidanlar",
    "acidifier", "acidifiers", "acidity regulator", "acidity regulators"
}

ROLE_PREFIXES_RAW = [
    "asitlik düzenleyiciler", "asitlik düzenleyici",
    "koruyucular", "koruyucu",
    "renklendiriciler", "renklendirici",
    "renk vericiler", "renk verici",
    "emülgatörler", "emülgatör",
    "emulgators", "emulgator",
    "stabilizörler", "stabilizör",
    "stabilizers", "stabilizer",
    "tatlandırıcılar", "tatlandırıcı",
    "sweeteners", "sweetener",
    "kabartıcılar", "kabartıcı",
    "raising agents", "raising agent",
    "kıvam arttırıcılar", "kıvam arttırıcı",
    "thickeners", "thickener",
    "aroma vericiler", "aroma verici",
    "flavourings", "flavouring",
    "flavorings", "flavoring",
    "antioksidanlar", "antioksidan",
    "acidifiers", "acidifier",
    "acidity regulators", "acidity regulator",
]

TYPE_PRIORITY = {
    "allergen": 3,
    "additive": 2,
    "ingredient": 1,
}

QUERY_SYNONYMS = {
    "cafein": ["kafein", "caffeine"],
    "kafein": ["cafein", "caffeine"],
    "caffeine": ["kafein", "cafein"],
}

START_KEYWORDS = ["içindekiler", "ingredients", "icindekiler", "bileşenler"]

FUZZY_MIN_FOR_SEMANTIC = float(os.getenv("FOODLENS_FUZZY_MIN_FOR_SEMANTIC", "72"))

def thresholds_for_type(item_type: str):
    if item_type == "ingredient":
        return {"fuzzy_strong": 96, "fuzzy_fallback": 92, "semantic": 0.90}
    if item_type == "allergen":
        return {"fuzzy_strong": 91, "fuzzy_fallback": 84, "semantic": 0.82}
    return {"fuzzy_strong": 91, "fuzzy_fallback": 82, "semantic": 0.80}
