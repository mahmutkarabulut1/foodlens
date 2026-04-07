"""
Block Splitter — groups OCR lines into coherent section blocks.

Key improvements:
  - Joins consecutive ingredient lines even when section anchors are missing
  - Treats misc_section lines following an ingredient block as continuation
    when they have ingredient-like content (commas, ingredient words)
  - Better handling of interleaved noise lines within ingredient blocks
"""
from __future__ import annotations

from typing import List

from ..schemas import TextBlock
from ..preprocessing.normalize import normalize_for_matching
from .section_classifier import classify_line, ingredient_cue_count

JOINABLE_SECTIONS = {
    "ingredient_section",
    "allergen_section",
    "may_contain_section",
    "free_from_section",
}

# Sections that definitively END an ingredient block
SECTION_BREAKERS = {
    "nutrition_section",
    "storage_section",
    "manufacturer_section",
}


def _is_ingredient_continuation(line: str, prev_section: str) -> bool:
    """
    Check if a misc_section line is actually a continuation of an ingredient block.
    This handles cases where OCR destroyed the separator or the line is a fragment.
    """
    if prev_section != "ingredient_section":
        return False

    lowered = line.lower()

    # Has commas/semicolons -> likely ingredient list continuation
    sep_count = line.count(",") + line.count(";")
    if sep_count >= 1:
        return True

    # Has ingredient cue words
    if ingredient_cue_count(lowered) >= 1:
        return True

    # Starts with lowercase (continuation of previous line)
    stripped = line.strip()
    if stripped and stripped[0].islower():
        return True

    # Has parentheses (sub-ingredients)
    if "(" in line and ")" in line:
        return True

    # Short line after ingredient block -> likely a tail fragment
    if len(stripped.split()) <= 4:
        return True

    return False


def split_into_blocks(lines: List[str]) -> List[TextBlock]:
    """
    Split lines into typed blocks, with smart joining of ingredient continuations.
    """
    blocks: List[TextBlock] = []
    current: TextBlock | None = None

    for line in lines:
        section_type, anchor = classify_line(line)
        normalized_line = normalize_for_matching(line)

        # Check if this misc line is actually a continuation of ingredients
        if (section_type == "misc_section"
                and current is not None
                and _is_ingredient_continuation(line, current.section_type)):
            section_type = "ingredient_section"
            anchor = "continuation"

        # Join consecutive lines of the same joinable section type
        if (current is not None
                and section_type == current.section_type
                and section_type in JOINABLE_SECTIONS):
            current.source_lines.append(line)
            current.raw_text = f"{current.raw_text} {line}".strip()
            current.normalized_text = f"{current.normalized_text} {normalized_line}".strip()
            continue

        # A section breaker always starts a new block
        if current is not None:
            blocks.append(current)

        current = TextBlock(
            section_type=section_type,
            raw_text=line,
            normalized_text=normalized_line,
            source_lines=[line],
            anchor=anchor,
        )

    if current is not None:
        blocks.append(current)

    return blocks
