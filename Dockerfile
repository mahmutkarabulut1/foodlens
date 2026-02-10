# 1. Python 3.9'un hafif sürümünü baz al (Resmi Google önerisi)
FROM python:3.9-slim

# 2. Çalışma klasörünü ayarla
WORKDIR /app

# 3. Önce gereksinim dosyasını kopyala ve kütüphaneleri kur
# (Bunu ayrı yapmak, önbellekleme sayesinde sonraki yüklemeleri hızlandırır)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Kalan tüm dosyaları (main.py, veritabanı json vb.) kopyala
COPY . .

# 5. Cloud Run'ın bize vereceği PORT numarasını dinle
# Google Cloud Run, $PORT değişkenini otomatik atar (Genelde 8080)
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
