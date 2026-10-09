from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .context import StructuredContext
from .security import SecurityAssessmentResult

class GenerateOutputItem(BaseModel):
    """
    Contract for Member 1 frontend output card.
    """
    output_type: str
    title: str
    summary: str
    key_points: List[str]
    body: str

class GenerateResponse(BaseModel):
    """
    Direct response contract consumed by Member 1's POST /api/generate.
    """
    outputs: List[GenerateOutputItem]
    request_id: Optional[str] = None
    security: Optional[SecurityAssessmentResult] = None

class ProcessResponse(BaseModel):
    """
    Agreed API Response Contract for Member 2 & Member 3 integration (Section 6.5).
    """
    status: str = Field(..., description="'success', 'blocked', or 'error'")
    request_id: str = Field(..., description="Unique traceability identifier")
    security: SecurityAssessmentResult = Field(..., description="Security assessment details")
    context: Optional[StructuredContext] = Field(None, description="Structured AI context for generators")
    outputs: List[Dict[str, Any]] = Field(default_factory=list, description="Populated by Member 3 generators")
    errors: List[str] = Field(default_factory=list, description="Any warnings or error details")
