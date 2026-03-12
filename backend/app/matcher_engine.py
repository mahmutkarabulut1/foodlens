from __future__ import annotations

import logging

from .analysis.engine import FoodLensAnalysisEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FoodLens")


class FoodLensMatcher:
    def __init__(self):
        logger.info("Rule-based FoodLens matcher başlatılıyor")
        self.engine = FoodLensAnalysisEngine()
        self.database = self.engine.lexicon.records
        self.exact_map = self.engine.lexicon.alias_map
        self.search_aliases = list(self.engine.lexicon.alias_map.keys())

    def health(self):
        return self.engine.health()

    def analyze_structured(self, text: str):
        return self.engine.analyze_structured(text).to_debug_dict()

    def analyze_text(self, text: str):
        return self.engine.analyze_for_api(text)
