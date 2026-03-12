from __future__ import annotations

from typing import List

from ..schemas import TextBlock
from ..preprocessing.normalize import normalize_for_matching
from .section_classifier import classify_line


JOINABLE_SECTIONS = {
    "ingredient_section",
    "allergen_section",
    "may_contain_section",
    "free_from_section",
}


def split_into_blocks(lines: List[str]) -> List[TextBlock]:
    blocks: List[TextBlock] = []
    current: TextBlock | None = None

    for line in lines:
        section_type, anchor = classify_line(line)
        normalized_line = normalize_for_matching(line)

        if current and section_type == current.section_type and section_type in JOINABLE_SECTIONS:
            current.source_lines.append(line)
            current.raw_text = f"{current.raw_text} {line}".strip()
            current.normalized_text = f"{current.normalized_text} {normalized_line}".strip()
            continue

        if current:
            blocks.append(current)

        current = TextBlock(
            section_type=section_type,
            raw_text=line,
            normalized_text=normalized_line,
            source_lines=[line],
            anchor=anchor,
        )

    if current:
        blocks.append(current)

    return blocks
