from __future__ import annotations

import csv
from pathlib import Path

import pytesseract
from PIL import Image
from pillow_heif import register_heif_opener, open_heif

register_heif_opener()

BASE_DIR = Path(__file__).resolve().parent
PHOTO_DIR = BASE_DIR / "fotolar"
OUTPUT_DIR = BASE_DIR / "output"

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}


def clean_text(text: str) -> str:
    if text is None:
        return ""
    text = text.replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def load_image_as_rgb(image_path: Path) -> Image.Image:
    ext = image_path.suffix.lower()

    if ext in {".heic", ".heif"}:
        heif_file = open_heif(str(image_path))
        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
        )
    else:
        image = Image.open(image_path)

    if image.mode != "RGB":
        image = image.convert("RGB")

    return image


def run_ocr_on_image(image_path: Path) -> str:
    image = load_image_as_rgb(image_path)
    text = pytesseract.image_to_string(image, lang="tur+eng")
    return clean_text(text)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    image_files = sorted(
        [p for p in PHOTO_DIR.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
    )

    if not image_files:
        print(f"Görsel bulunamadı: {PHOTO_DIR}")
        return

    csv_path = OUTPUT_DIR / "ocr_sonuclari.csv"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "file_name",
                "file_path",
                "ocr_text",
                "line_count",
                "char_count",
                "has_error",
                "error_message",
            ],
        )
        writer.writeheader()

        for image_path in image_files:
            print(f"OCR işleniyor: {image_path.name}")
            record_id = image_path.stem

            try:
                text = run_ocr_on_image(image_path)

                line_count = len([line for line in text.splitlines() if line.strip()])
                char_count = len(text)

                writer.writerow({
                    "id": record_id,
                    "file_name": image_path.name,
                    "file_path": str(image_path),
                    "ocr_text": text,
                    "line_count": line_count,
                    "char_count": char_count,
                    "has_error": 0,
                    "error_message": "",
                })

                print(f"  -> CSV satırı yazıldı: {record_id}")

            except Exception as e:
                error_message = str(e)

                writer.writerow({
                    "id": record_id,
                    "file_name": image_path.name,
                    "file_path": str(image_path),
                    "ocr_text": "",
                    "line_count": 0,
                    "char_count": 0,
                    "has_error": 1,
                    "error_message": error_message,
                })

                print(f"  -> HATA yazıldı: {record_id} | {error_message}")

    print(f"\nToplu CSV kaydedildi: {csv_path}")
    print("Tamamlandı.")


if __name__ == "__main__":
    main()
