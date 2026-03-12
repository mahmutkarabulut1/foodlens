from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TextBlock:
    section_type: str
    raw_text: str
    normalized_text: str
    source_lines: List[str] = field(default_factory=list)
    anchor: str = ""


@dataclass
class CandidateSpan:
    raw_text: str
    normalized_text: str
    section_type: str
    polarity: str
    category_hint: str
    evidence: str = ""


@dataclass
class MatchedEntity:
    item_id: str
    name: str
    item_type: str
    risk_level: str
    description: str
    matched_key: str
    raw_query: str
    match_type: str = "exact"
    match_score: int = 100
    polarity: str = "present"
    source_section: str = "ingredient_section"
    source_text: str = ""

    def to_api_dict(self) -> Dict[str, Any]:
        return {
            "id": self.item_id,
            "name": self.name,
            "item_type": self.item_type,
            "risk_level": self.risk_level,
            "description": self.description,
            "raw_query": self.raw_query,
            "matched_key": self.matched_key,
            "match_type": self.match_type,
            "match_score": self.match_score,
            "needs_validation": False,
            "validation_reason": [],
            "polarity": self.polarity,
            "source_section": self.source_section,
            "source_text": self.source_text,
            "verifier_payload": {
                "ocr_fragment": self.raw_query,
                "matched_key": self.matched_key,
                "candidate_id": self.item_id,
                "candidate_name": self.name,
                "candidate_type": self.item_type,
                "context": self.source_text,
                "query_coverage": 1.0,
                "alias_precision": 1.0,
                "polarity": self.polarity,
                "source_section": self.source_section,
            },
        }


@dataclass
class StructuredAnalysis:
    present: List[MatchedEntity] = field(default_factory=list)
    may_contain: List[MatchedEntity] = field(default_factory=list)
    free_from: List[MatchedEntity] = field(default_factory=list)
    unmatched_spans: List[CandidateSpan] = field(default_factory=list)
    ignored_blocks: List[TextBlock] = field(default_factory=list)
    blocks: List[TextBlock] = field(default_factory=list)

    def to_debug_dict(self) -> Dict[str, Any]:
        return {
            "present": [item.to_api_dict() for item in self.present],
            "may_contain": [item.to_api_dict() for item in self.may_contain],
            "free_from": [item.to_api_dict() for item in self.free_from],
            "unmatched_spans": [
                {
                    "raw_text": span.raw_text,
                    "normalized_text": span.normalized_text,
                    "section_type": span.section_type,
                    "polarity": span.polarity,
                    "category_hint": span.category_hint,
                    "evidence": span.evidence,
                }
                for span in self.unmatched_spans
            ],
            "ignored_blocks": [
                {
                    "section_type": block.section_type,
                    "raw_text": block.raw_text,
                    "anchor": block.anchor,
                }
                for block in self.ignored_blocks
            ],
            "blocks": [
                {
                    "section_type": block.section_type,
                    "raw_text": block.raw_text,
                    "anchor": block.anchor,
                }
                for block in self.blocks
            ],
        }
