from ..schemas.security import SecurityDecision, SecurityAssessmentResult
from ..config import settings

def evaluate_security_policy(
    risk_score: float,
    detected_signals: list[str],
    block_threshold: float = None,
    review_threshold: float = None,
) -> SecurityAssessmentResult:
    """
    Evaluates risk score and detected signals to produce a structured security decision.
    Outputs: ALLOW, REVIEW, or BLOCK.
    """
    block_th = block_threshold if block_threshold is not None else settings.PROMPT_INJECTION_BLOCK_THRESHOLD
    review_th = review_threshold if review_threshold is not None else settings.PROMPT_INJECTION_REVIEW_THRESHOLD

    if risk_score >= block_th:
        return SecurityAssessmentResult(
            decision=SecurityDecision.BLOCK,
            risk_score=risk_score,
            detected_signals=detected_signals,
            reason_code="SEC_PROMPT_INJECTION_BLOCKED",
            explanation="The submitted source content was blocked by the security policy because it contains instruction override or injection patterns."
        )
    elif risk_score >= review_th:
        return SecurityAssessmentResult(
            decision=SecurityDecision.REVIEW,
            risk_score=risk_score,
            detected_signals=detected_signals,
            reason_code="SEC_SUSPICIOUS_CONTENT_FLAGGED",
            explanation="The source content was flagged with suspicious patterns. It has been isolated with strict untrusted delimiters."
        )
    else:
        return SecurityAssessmentResult(
            decision=SecurityDecision.ALLOW,
            risk_score=risk_score,
            detected_signals=[],
            reason_code="SEC_CLEAN",
            explanation="Source content passed input security checks successfully."
        )
