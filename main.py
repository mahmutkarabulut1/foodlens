from fastapi import FastAPI
from pydantic import BaseModel
import json
import os
import re
import logging
# C++ tabanlı hızlı arama kütüphanesi
from rapidfuzz import process, fuzz 

# --- LOGLAMA AYARLARI ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FoodLens")

app = FastAPI()

# --- AYARLAR ---
DB_FILE = "foodlens_ai_completed.json"
MATCH_THRESHOLD = 85.0  # RapidFuzz 0-100 arası puan verir
database = []

# Hızlı Arama İndeksleri (RAM'de tutulacak)
SEARCH_KEYS = []      # C++'ın tarayacağı saf metin listesi
KEY_TO_ITEM_MAP = {}  # Metinden nesneye giden harita

def clean_text(text):
    if text is None: return ""
    text = str(text)
    
    # 1. Önce Türkçe Karakter Sorununu Çöz (Elle Dönüştürme)
    # Python standart lower() 'I' yı 'i' yapar, biz 'ı' istiyoruz.
    text = text.replace('İ', 'i').replace('I', 'ı').replace('Ğ', 'ğ').replace('Ü', 'ü').replace('Ş', 'ş').replace('Ö', 'ö').replace('Ç', 'ç')
    
    # 2. Standart Küçük Harfe Çevir
    text = text.lower()
    
    # 3. Temizlik (Noktalama işaretlerini sil)
    text = text.replace('\n', ' ').replace(':', '').replace('.', '').replace(',', '')
    
    return text.strip()

def load_database():
    global database, SEARCH_KEYS, KEY_TO_ITEM_MAP
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, DB_FILE)
        
        if not os.path.exists(file_path):
            logger.error(f"DOSYA BULUNAMADI: {DB_FILE}")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
            if isinstance(content, dict) and "data" in content:
                database = content["data"]
            elif isinstance(content, list):
                database = content
            else:
                database = []
        
        # C++ İÇİN İNDEKSLEME (SPEED BOOST)
        SEARCH_KEYS = []
        KEY_TO_ITEM_MAP = {}
        
        logger.info("Veritabanı indeksleniyor... Lütfen bekleyin.")
        
        for item in database:
            # Aday kelimeleri topla: ID, TR İsim, EN İsim, Keywordler
            candidates = set()
            
            if item.get("id"): candidates.add(item["id"])
            if item.get("name_tr"): candidates.add(item["name_tr"])
            if item.get("name_en"): candidates.add(item["name_en"])
            
            if item.get("keywords"):
                for kw in item["keywords"]:
                    if kw: candidates.add(kw)
            
            # Her bir adayı indekse ekle
            for candidate in candidates:
                clean_key = clean_text(candidate)
                if len(clean_key) < 2: continue 
                
                SEARCH_KEYS.append(clean_key)
                KEY_TO_ITEM_MAP[clean_key] = item
                
        logger.info(f"✅ VERİTABANI YÜKLENDİ: {len(database)} madde.")
        logger.info(f"🚀 HIZLI ARAMA İNDEKSİ: {len(SEARCH_KEYS)} anahtar kelime hazır.")
            
    except Exception as e:
        logger.error(f"❌ Veritabanı Hatası: {e}")
        database = []

# Uygulama başlarken yükle
load_database()

class ImageRequest(BaseModel):
    ocr_text: str

def extract_relevant_section(text):
    """
    GÜNCELLENMİŞ ALGORİTMA:
    'İçindekiler'den başla, 4. noktaya (.) kadar al.
    Eğer 4 nokta yoksa, metnin sonuna kadar git.
    """
    text_lower = text.lower()
    start_keywords = ["içindekiler", "ingredients", "icindekiler", "bileşenler"]
    
    start_index = -1
    for kw in start_keywords:
        idx = text_lower.find(kw)
        if idx != -1:
            start_index = idx
            break
    
    # Başlık bulunamazsa hepsini gönder
    if start_index == -1:
        return text 

    # Başlangıçtan sonrasını al
    relevant_part = text[start_index:]
    
    # --- 4. NOKTAYI BULMA ALGORİTMASI ---
    target_dot_count = 4   # Kaçıncı noktada duracak?
    current_pos = 0        # Aramaya nereden başlayacağız?
    found_index = -1       # Kesme noktamız
    
    for _ in range(target_dot_count):
        # current_pos'tan itibaren bir nokta ara
        dot_idx = relevant_part.find('.', current_pos)
        
        if dot_idx != -1:
            # Nokta bulundu, konumunu kaydet
            found_index = dot_idx
            # Bir sonraki aramayı bu noktadan 1 karakter sonra yap
            current_pos = dot_idx + 1
        else:
            # Aradığımız kadar nokta yokmuş (metin bitti), döngüyü kır
            break
            
    if found_index != -1:
        # Bulunan son noktaya (4. veya metnin son noktasına) kadar kes
        return relevant_part[:found_index]
    else:
        # Hiç nokta yoksa sonuna kadar al
        return relevant_part

@app.post("/analyze")
def analyze_image(request: ImageRequest):
    original_text = request.ocr_text
    
    # 1. İlgili Bölümü Kes
    targeted_text = extract_relevant_section(original_text)
    
    # 2. Metni Parçala
    clean_ocr = targeted_text.replace('\n', ',').replace(':', ',').replace(';', ',').replace('•', ',')

    # YENİ EKLEME: Parantezleri virgüle çeviriyoruz
    clean_ocr = clean_ocr.replace('(', ',').replace(')', ',').replace('[', ',').replace(']', ',').replace('{', ',').replace('}', ',')
    raw_items = [x.strip() for x in clean_ocr.split(',')]
    
    results = []
    seen_ids = set()
    
    # 3. C++ TABANLI HIZLI ARAMA (RapidFuzz)
    for item_text in raw_items:
        if len(item_text) < 3 or len(item_text) > 50: continue 
        
        cleaned_query = clean_text(item_text)
        
        # RapidFuzz tüm listeyi C++ hızında tarar
        match = process.extractOne(
            cleaned_query, 
            SEARCH_KEYS, 
            scorer=fuzz.token_sort_ratio,
            score_cutoff=MATCH_THRESHOLD
        )
        
        if match:
            found_key = match[0]
            score = match[1]
            
            db_item = KEY_TO_ITEM_MAP.get(found_key)
            
            if db_item and db_item["id"] not in seen_ids:
                results.append({
                    "id": db_item["id"],
                    "name": db_item["name_tr"] if db_item.get("name_tr") else db_item.get("name_en"),
                    "risk_level": db_item.get("risk_level", "Unknown"),
                    "description": db_item.get("description_tr", ""),
                    "dietary_status": db_item.get("dietary_status", "Unknown"),
                    "match_score": int(score)
                })
                seen_ids.add(db_item["id"])
                logger.info(f"BULUNDU: '{item_text}' -> {db_item['name_tr']} (%{score:.1f})")

    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
