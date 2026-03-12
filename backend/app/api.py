from fastapi import FastAPI

from .matcher_engine import FoodLensMatcher
from .schemas import ImageRequest

app = FastAPI(title="FoodLens API")

_matcher = None


def get_matcher():
    global _matcher
    if _matcher is None:
        _matcher = FoodLensMatcher()
    return _matcher


@app.get("/health")
def health():
    return get_matcher().health()


@app.post("/analyze")
def analyze_image(request: ImageRequest):
    matcher = get_matcher()
    return {"results": matcher.analyze_text(request.ocr_text)}


@app.post("/analyze-structured")
def analyze_image_structured(request: ImageRequest):
    matcher = get_matcher()
    return matcher.analyze_structured(request.ocr_text)
