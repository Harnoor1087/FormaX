import re
from typing import Tuple, List, Dict

# Patterns for sensitive information detection and redaction
PII_PATTERNS: List[Tuple[str, str, str]] = [
    # API Keys / Bearer tokens
    (
        r"(?i)\b(?:bearer\s+[a-zA-Z0-9_\-\.]{20,}|(?:sk|ghp|xoxb|xoxp|ai-za|key)-[a-zA-Z0-9_\-]{16,})\b",
        "[SECRET_KEY_REDACTED]",
        "SECRET_TOKEN"
    ),
    # Email addresses
    (
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "[EMAIL_REDACTED]",
        "EMAIL_ADDRESS"
    ),
    # Phone numbers (international, US, Indian standards)
    (
        r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "[PHONE_REDACTED]",
        "PHONE_NUMBER"
    ),
    # Indian Aadhaar / 12-digit Government IDs
    (
        r"\b\d{4}[\s-]\d{4}[\s-]\d{4}\b",
        "[GOVT_ID_REDACTED]",
        "GOVERNMENT_ID"
    ),
    # US Social Security Number (SSN)
    (
        r"\b\d{3}-\d{2}-\d{4}\b",
        "[SSN_REDACTED]",
        "NATIONAL_ID"
    ),
    # Credit Card Numbers
    (
        r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "[PAYMENT_CARD_REDACTED]",
        "PAYMENT_CARD"
    ),
]

class SensitiveDataFilter:
    """
    Screens source content and generated outputs for sensitive data leakage
    and personally identifiable information (PII) - OWASP LLM06.
    """

    def __init__(self, patterns=None):
        self.patterns = patterns or PII_PATTERNS

    def scan(self, text: str) -> List[str]:
        """Scans and returns list of detected sensitive data category tags."""
        if not text:
            return []
        
        detected = []
        for pattern, _, label in self.patterns:
            if re.search(pattern, text):
                detected.append(label)
        return list(dict.fromkeys(detected))

    def redact(self, text: str) -> Tuple[str, List[str]]:
        """
        Redacts detected sensitive strings in the text.
        Returns:
            Tuple of (redacted_text: str, detected_types: List[str])
        """
        if not text:
            return "", []

        redacted = text
        detected = []

        for pattern, replacement, label in self.patterns:
            if re.search(pattern, redacted):
                detected.append(label)
                redacted = re.sub(pattern, replacement, redacted)

        return redacted, list(dict.fromkeys(detected))

sensitive_filter = SensitiveDataFilter()
