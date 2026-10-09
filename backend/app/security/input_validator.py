import re
from typing import Tuple

# Zero-width spaces and invisible control characters used in evasion
INVISIBLE_CHARS_PATTERN = re.compile(r"[\u200B-\u200D\uFEFF\u00A0\u200E\u200F\u202A-\u202E]")

def normalize_text(raw_text: str) -> str:
    """
    Normalizes incoming source content:
    - Standardizes line breaks
    - Strips invisible unicode evasion characters
    - Normalizes consecutive spaces and tabs
    - Preserves logical paragraph breaks
    """
    if not raw_text:
        return ""
    
    # Remove null bytes immediately
    text = raw_text.replace("\x00", "")
    
    # Strip invisible zero-width and directional override characters
    text = INVISIBLE_CHARS_PATTERN.sub("", text)
    
    # Normalize line breaks
    text = re.sub(r"\r\n?", "\n", text)
    
    # Collapse horizontal spaces/tabs (preserving line breaks)
    text = re.sub(r"[ \t]+", " ", text)
    
    # Collapse 3+ consecutive newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    return text.strip()

def validate_source_input(text: str, max_length: int = 50000, min_length: int = 1) -> Tuple[bool, str]:
    """
    Validates source text constraints.
    Returns (is_valid, error_message).
    """
    if not text or not text.strip():
        return False, "Source content is empty or contains only whitespace."
    
    if len(text) < min_length:
        return False, f"Source content must be at least {min_length} characters."
        
    if len(text) > max_length:
        return False, f"Source content exceeds maximum allowed length of {max_length} characters."
        
    return True, ""
