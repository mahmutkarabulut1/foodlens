import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw" / "raw_data"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "foodlens_comprehensive_db.json"

RISK_MAP = {
    "E102": {"level": "High", "note": "Hiperaktivite riski (Tartrazin)."},
    "E202": {"level": "Low", "note": "Genellikle güvenli."},
}


def load_json(filename):
    path = RAW_DIR / filename
    print(f"📂 Okunuyor: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def clean_text(text):
    if not text:
        return ""
    return text.lower().strip()


def process_item(key, val, item_type):
    clean_id = key.replace("en:", "").replace("-", " ").strip()
    if item_type == "additive" and clean_id.startswith("e"):
        clean_id = clean_id.replace(" ", "").upper()

    names = val.get("name", {})
    name_tr = names.get("tr", "")
    name_en = names.get("en", "")

    display_name = name_tr if name_tr else name_en

    if not display_name:
        return None

    keywords = set()
    keywords.add(clean_id.lower())
    if name_tr:
        keywords.add(clean_text(name_tr))
    if name_en:
        keywords.add(clean_text(name_en))

    if item_type == "additive":
        keywords.add(clean_id.lower().replace("e", "e-"))
        keywords.add(clean_id.lower().replace("e", "e "))

    risk_data = {"level": "Unknown", "note": ""}
    if item_type == "additive":
        risk_data = RISK_MAP.get(clean_id, risk_data)

    return {
        "id": clean_id,
        "name": display_name,
        "type": item_type,
        "risk_level": risk_data["level"],
        "note": risk_data["note"],
        "keywords": sorted(list(keywords)),
    }


def main():
    try:
        raw_additives = load_json("additives.json")
        raw_allergens = load_json("allergens.json")
        raw_ingredients = load_json("ingredients.json")
    except FileNotFoundError as e:
        print(f"❌ HATA: Dosya bulunamadı -> {e}")
        return

    print("🚀 Veri işleme başladı (Kapsayıcı Mod)...")

    final_list = []

    print("...Katkı Maddeleri taranıyor")
    for k, v in raw_additives.items():
        if k.startswith("en:e"):
            item = process_item(k, v, "additive")
            if item:
                final_list.append(item)

    print("...Alerjenler taranıyor")
    for k, v in raw_allergens.items():
        item = process_item(k, v, "allergen")
        if item:
            final_list.append(item)

    print("...Genel İçerikler taranıyor")
    for k, v in raw_ingredients.items():
        item = process_item(k, v, "ingredient")
        if item and len(item["name"]) > 2:
            final_list.append(item)

    output_data = {
        "metadata": {"count": len(final_list), "strategy": "Multi-Language Fallback"},
        "data": final_list,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ İŞLEM TAMAM! Toplam {len(final_list)} madde veritabanına eklendi.")
    print(f"📂 Çıktı dosyası: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
