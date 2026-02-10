import requests
import os
import time

# İndirilecek Dosyalar ve Kaynak Linkleri (Open Food Facts Resmi Taksonomileri)
DATA_SOURCES = {
    "additives.json": "https://static.openfoodfacts.org/data/taxonomies/additives.json",
    "allergens.json": "https://static.openfoodfacts.org/data/taxonomies/allergens.json",
    "ingredients.json": "https://static.openfoodfacts.org/data/taxonomies/ingredients.json"
}

# Kayıt Klasörü
DOWNLOAD_DIR = "raw_data"

def download_file(url, filename):
    """Dosyayı stream (akış) modunda indirir, RAM şişirmez."""
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    print(f"⬇️  İndiriliyor: {filename}...")
    
    try:
        # Open Food Facts nazik kullanım için User-Agent ister
        headers = {'User-Agent': 'FoodLens-Thesis-Project/1.0 (mahmut.karabulut@ogrenci.ege.edu.tr)'}
        
        with requests.get(url, headers=headers, stream=True) as r:
            r.raise_for_status()
            total_size = 0
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
                    total_size += len(chunk)
        
        size_mb = total_size / (1024 * 1024)
        print(f"✅ Tamamlandı: {filename} ({size_mb:.2f} MB)")
        return True
        
    except Exception as e:
        print(f"❌ Hata oluştu ({filename}): {e}")
        return False

def main():
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        print(f"📂 '{DOWNLOAD_DIR}' klasörü oluşturuldu.")

    print("Ham veri indirme işlemi başlıyor...\n")
    
    start_time = time.time()
    success_count = 0
    
    for name, url in DATA_SOURCES.items():
        if download_file(url, name):
            success_count += 1
            
    print(f"\n🏁 İŞLEM BİTTİ.")
    print(f"toplam {success_count}/{len(DATA_SOURCES)} dosya '{DOWNLOAD_DIR}' klasörüne indi.")
    print(f"⏱️  Geçen Süre: {round(time.time() - start_time, 2)} saniye")

if __name__ == "__main__":
    main()

