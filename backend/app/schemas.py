from pydantic import BaseModel, Field


class ImageRequest(BaseModel):
    ocr_text: str
    selected_allergens: list[str] = Field(default_factory=list)
