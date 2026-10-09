from enum import Enum
from typing import List
from pydantic import BaseModel, Field

class SecurityDecision(str, Enum):
    ALLOW = "allow"
    REVIEW = "review"
    BLOCK = "block"

class SecurityAssessmentResult(BaseModel):
    """
    Contract matching Section 6.3 of Member 2 document.
    """
    decision: SecurityDecision = Field(
        ...,
        description="Security outcome decision: allow, review, or block"
    )
    risk_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Calculated risk score from 0.0 (safe) to 1.0 (malicious)"
    )
    detected_signals: List[str] = Field(
        default_factory=list,
        description="Identified security signals or pattern flags"
    )
    reason_code: str = Field(
        default="SEC_OK",
        description="Machine-readable security code (e.g. SEC_INJECTION_DETECTED)"
    )
    explanation: str = Field(
        default="Input cleared all security validation checks.",
        description="Safe, non-leaking explanation of the security assessment"
    )

    @property
    def is_blocked(self) -> bool:
        return self.decision == SecurityDecision.BLOCK
