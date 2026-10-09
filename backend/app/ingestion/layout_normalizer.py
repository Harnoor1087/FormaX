import re
from typing import Tuple, Dict, Any, List

# Common document header/footer patterns
PAGE_NUMBER_PATTERN = re.compile(
    r"(?i)(?:page\s+\d+(?:\s+of\s+\d+)?|^\s*\d+\s*$|^-\s*\d+\s*-$)",
    re.MULTILINE
)
RUNNING_HEADER_PATTERN = re.compile(
    r"(?i)^\s*(?:confidential|draft|internal use only|restricted|official use only)\s*$",
    re.MULTILINE
)
HYPHENATED_LINEBREAK = re.compile(r"(\b[a-zA-Z]+)-\n([a-zA-Z]+\b)")

def clean_layout_artifacts(raw_text: str) -> str:
    """
    Removes layout noise from PDF/DOCX extractions:
    - Re-joins hyphenated words across line boundaries
    - Strips running headers, footers, and standalone page numbers
    - Normalizes paragraph spacing
    """
    if not raw_text:
        return ""

    # Re-join hyphenated words across line breaks
    text = HYPHENATED_LINEBREAK.sub(r"\1\2", raw_text)

    # Strip page numbers and headers
    text = PAGE_NUMBER_PATTERN.sub("", text)
    text = RUNNING_HEADER_PATTERN.sub("", text)

    # Strip consecutive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def structure_document_text(text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Analyzes document structural elements (headings, bullet points, key-value tables).
    Returns:
        Tuple of (structured_text: str, layout_metadata: Dict[str, Any])
    """
    cleaned = clean_layout_artifacts(text)
    lines = cleaned.split("\n")

    detected_headings: List[str] = []
    bullet_count = 0
    table_rows = 0

    structured_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            structured_lines.append("")
            continue

        # Bullet point detection
        if re.match(r"^[-*•]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
            bullet_count += 1
            structured_lines.append(stripped)
        # Table/columnar line detection
        elif "|" in stripped or "\t" in stripped:
            table_rows += 1
            normalized_row = " | ".join([cell.strip() for cell in re.split(r"[|\t]+", stripped) if cell.strip()])
            structured_lines.append(f"| {normalized_row} |")
        # Heading detection: Uppercase or numbered section title
        elif (
            (stripped.isupper() and len(stripped.split()) <= 8 and len(stripped) > 4)
            or re.match(r"^(?:Section|Chapter|Part|Annexure)\s+[\dA-Z]+[:\-\s]", stripped, re.IGNORECASE)
        ):
            detected_headings.append(stripped)
            structured_lines.append(f"## {stripped}")
        else:
            structured_lines.append(stripped)

    metadata = {
        "headings_found": len(detected_headings),
        "headings_list": detected_headings[:5],
        "bullet_points_count": bullet_count,
        "table_rows_count": table_rows,
        "estimated_paragraphs": len([p for p in "\n".join(structured_lines).split("\n\n") if p.strip()]),
    }

    return "\n".join(structured_lines).strip(), metadata
