import requests
from pathlib import Path
import time

DATA_SOURCES = {
    "additives.json": "https://static.openfoodfacts.org/data/taxonomies/additives.json",
    "allergens.json": "https://static.openfoodfacts.org/data/taxonomies/allergens.json",
    "ingredients.json": "https://static.openfoodfacts.org/data/taxonomies/ingredients.json",
}

BASE_DIR = Path(__file__).resolve().parents[2]
DOWNLOAD_DIR = BASE_DIR / "data" / "raw" / "raw_data"


def download_file(url, filename):
    file_path = DOWNLOAD_DIR / filename
    print(f"⬇️  İndiriliyor: {filename} -> {file_path}")

    try:
        headers = {
            "User-Agent": "FoodLens-Thesis-Project/1.0 (mahmut.karabulut@ogrenci.ege.edu.tr)"
        }

        with requests.get(url, headers=headers, stream=True, timeout=120) as r:
            r.raise_for_status()
            total_size = 0
            with file_path.open("wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    f.write(chunk)
                    total_size += len(chunk)

        size_mb = total_size / (1024 * 1024)
        print(f"✅ Tamamlandı: {filename} ({size_mb:.2f} MB)")
        return True

    except Exception as e:
        print(f"❌ Hata oluştu ({filename}): {e}")
        return False


def main():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    print("Ham veri indirme işlemi başlıyor...\n")

    start_time = time.time()
    success_count = 0

    for name, url in DATA_SOURCES.items():
        if download_file(url, name):
            success_count += 1

    print("\n🏁 İŞLEM BİTTİ.")
    print(f"Toplam {success_count}/{len(DATA_SOURCES)} dosya '{DOWNLOAD_DIR}' klasörüne indi.")
    print(f"⏱️  Geçen Süre: {round(time.time() - start_time, 2)} saniye")


if __name__ == "__main__":
    main()
