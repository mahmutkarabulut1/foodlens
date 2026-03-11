from pydantic import BaseModel

class ImageRequest(BaseModel):
    ocr_text: str
