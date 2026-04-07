from __future__ import annotations

from ..schemas import CandidateSpan, MatchedEntity
from .lexicon import MasterLexicon


class ExactRuleMatcher:
    def __init__(self, lexicon: MasterLexicon):
        self.lexicon = lexicon

    def match_span(self, span: CandidateSpan) -> MatchedEntity | None:
        record = self.lexicon.exact_lookup(span.normalized_text or span.raw_text, span.section_type)
        if not record:
            return None

        return MatchedEntity(
            item_id=record["id"],
            name=record["name"],
            item_type=record["item_type"],
            risk_level=record["risk_level"],
            description=record["description"],
            matched_key=span.normalized_text or span.raw_text,
            raw_query=span.raw_text,
            match_type="exact",
            match_score=100,
            polarity=span.polarity,
            source_section=span.section_type,
            source_text=span.evidence,
        )
