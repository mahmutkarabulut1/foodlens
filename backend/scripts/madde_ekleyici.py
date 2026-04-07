import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path
import re

URL = "https://www.gursahakman.com/e-kodu-listesi/"

BASE_DIR = Path(__file__).resolve().parents[2]
JSON_FILE = BASE_DIR / "data" / "processed" / "foodlens_ai_completed.json"


def clean_text(text):
    return text.strip()


def load_database():
    if not JSON_FILE.exists():
        return []

    try:
        with JSON_FILE.open("r", encoding="utf-8") as f:
            content = json.load(f)
            if isinstance(content, dict) and "data" in content:
                return content["data"]
            return content
    except Exception:
        return []


def main():
    print("🚀 Gürşah Akman listesi taranıyor ve formatlanıyor...")

    database = load_database()
    existing_ids = set()

    for item in database:
        if "id" in item:
            existing_ids.add(item["id"])

    print(f"📂 Mevcut kayıt sayısı: {len(database)}")
    print(f"📂 Hedef dosya: {JSON_FILE}")

    try:
        response = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        content_div = soup.find("div", class_="entry-content")
        if not content_div:
            print("❌ İçerik bulunamadı!")
            return

        lines = content_div.get_text(separator="\n").split("\n")

        added_count = 0
        pattern = re.compile(r"^(E\s?[\d]+[a-z]?)\s+(.*)")

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if " - " in line and "Renklendiriciler" in line:
                continue

            match = pattern.match(line)
            if not match:
                continue

            raw_code = match.group(1).replace(" ", "")
            name = match.group(2).strip()

            if raw_code in existing_ids:
                continue

            new_item = {
                "id": raw_code,
                "name_tr": name,
                "name_en": "",
                "type": "additive",
                "wikidata_ref": "",
                "risk_level": "Unknown",
                "source_category": "additives",
                "keywords": [
                    raw_code,
                    raw_code.lower(),
                    raw_code.replace("E", "E-").lower(),
                    name.lower(),
                ],
                "dietary_status": "Unknown",
                "description_tr": "Gıda katkı maddesi.",
                "ai_processed": False,
                "source": "gursahakman.com",
            }

            database.append(new_item)
            existing_ids.add(raw_code)
            added_count += 1
            print(f"✅ Eklendi: {raw_code} - {name}")

        if added_count > 0:
            output_data = {"data": database}
            JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
            with JSON_FILE.open("w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=4)
            print(f"\n🎉 İşlem tamam! {added_count} yeni madde eklendi.")
        else:
            print("\n✅ Veritabanı zaten güncel.")

    except Exception as e:
        print(f"❌ Hata: {e}")


if __name__ == "__main__":
    main()
