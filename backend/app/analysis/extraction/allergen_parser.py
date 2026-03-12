from __future__ import annotations

from typing import List

from ..schemas import CandidateSpan, TextBlock
from .claim_parser import extract_claim_spans


def extract_from_allergen_related_block(block: TextBlock) -> List[CandidateSpan]:
    return extract_claim_spans(block)
