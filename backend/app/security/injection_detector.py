import re
from typing import List, Tuple

# Compiled weighted patterns for prompt injection detection
INJECTION_RULES = [
    # Direct instruction overrides (High severity: weight 0.85)
    (
        r"(?i)\b(?:ignore|disregard|forget|override|bypass|cancel)\s+(?:all\s+)?(?:previous|prior|above|former|earlier)\s+(?:instructions?|directives?|prompts?|rules?|guidelines?)\b",
        0.85,
        "OVERRIDE_INSTRUCTION_DIRECTIVE"
    ),
    (
        r"(?i)\b(?:do\s+not\s+follow|stop\s+following)\s+(?:any\s+)?(?:instructions?|directives?|rules?)\b",
        0.80,
        "DISREGARD_RULES_DIRECTIVE"
    ),
    # System role impersonation / delimiter spoofing (High severity: weight 0.80)
    (
        r"(?i)(?:^|\n)\s*(?:system|assistant|admin|root|developer)\s*:\s*(?:you\s+are|new\s+instructions|override|act\s+as)",
        0.80,
        "ROLE_IMPERSONATION"
    ),
    (
        r"(?i)(?:<\|im_start\|>|<\|im_end\|>|\[INST\]|\[\/INST\]|<<SYS>>|<\/s>)",
        0.90,
        "SPECIAL_TOKEN_INJECTION"
    ),
    # Jailbreak / Alternate persona commands (Medium-High severity: weight 0.75)
    (
        r"(?i)\b(?:you\s+are\s+now\s+in\s+developer\s+mode|dan\s+mode|jailbreak|unfiltered\s+mode|god\s+mode)\b",
        0.75,
        "JAILBREAK_PERSONA_TRIGGER"
    ),
    (
        r"(?i)\b(?:pretend\s+you\s+have\s+no\s+(?:rules|restrictions|filters|guidelines))\b",
        0.75,
        "SAFETY_FILTER_BYPASS"
    ),
    # System prompt extraction / leakage attempts (Medium severity: weight 0.65)
    (
        r"(?i)\b(?:repeat|print|reveal|output|display|show|leak)\s+(?:the\s+)?(?:system\s+prompt|initial\s+instructions?|developer\s+prompt|hidden\s+prompt)\b",
        0.65,
        "SYSTEM_PROMPT_LEAK_ATTEMPT"
    ),
    # Untrusted delimiter escape attempts (Medium severity: weight 0.60)
    (
        r"(?i)<\/?(?:untrusted_source_content|system_instruction|guardrail|operator_input)>",
        0.70,
        "INTERNAL_DELIMITER_ESCAPE"
    ),
]

class InjectionDetector:
    """
    Heuristic and pattern-based prompt-injection scanner.
    Enforces OWASP Top 10 for LLM Applications (LLM01: Prompt Injection).
    """

    def __init__(self, rules=None):
        self.rules = rules or INJECTION_RULES

    def scan(self, text: str) -> Tuple[float, List[str]]:
        """
        Scans normalized text for prompt injection signals.
        Returns:
            Tuple of (cumulative_risk_score: float [0.0 - 1.0], detected_signals: List[str])
        """
        if not text:
            return 0.0, []

        detected_signals = []
        max_score = 0.0
        additive_score = 0.0

        for pattern, weight, signal_id in self.rules:
            matches = re.findall(pattern, text)
            if matches:
                detected_signals.append(f"{signal_id} (count={len(matches)})")
                if weight > max_score:
                    max_score = weight
                additive_score += weight * 0.1 * min(len(matches), 3)

        # Total score combines highest single threat + small additive factor, capped at 1.0
        final_score = min(round(max_score + additive_score, 2), 1.0)
        return final_score, detected_signals
