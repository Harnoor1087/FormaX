from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from .context import StructuredContext
from .security import SecurityAssessmentResult

class OutputValidation(BaseModel):
    schema_valid: bool
    consistency_valid: bool
    issues: List[str] = Field(default_factory=list)

class GenerateOutputItem(BaseModel):
    """
    Contract for Member 1 frontend output card.
    """
    output_type: str
    title: str
    summary: str
    key_points: List[str]
    body: str
    output_id: Optional[str] = None
    review_status: str = "draft"
    generation_mode: Optional[Literal["gemini", "template", "template_fallback"]] = None
    validation: Optional[OutputValidation] = None

class GenerateResponse(BaseModel):
    """
    Direct response contract consumed by Member 1's POST /api/generate.
    """
    outputs: List[GenerateOutputItem]
    request_id: Optional[str] = None
    generation_id: Optional[str] = None
    generation_mode: str = "template"
    security: Optional[SecurityAssessmentResult] = None
    validation: Optional[OutputValidation] = None

class ProcessResponse(BaseModel):
    """
    Agreed API Response Contract for Member 2 & Member 3 integration (Section 6.5).
    """
    status: str = Field(..., description="'success', 'blocked', or 'error'")
    request_id: str = Field(..., description="Unique traceability identifier")
    security: SecurityAssessmentResult = Field(..., description="Security assessment details")
    context: Optional[StructuredContext] = Field(None, description="Structured AI context for generators")
    generation_id: Optional[str] = None
    generation_mode: str = "template"
    validation: Optional[OutputValidation] = None
    outputs: List[GenerateOutputItem] = Field(default_factory=list, description="Populated by Member 3 generators")
    errors: List[str] = Field(default_factory=list, description="Any warnings or error details")

class GenerateOutputUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    summary: str = Field(..., min_length=1, max_length=5000)
    key_points: List[str] = Field(default_factory=list, max_length=100)
    body: str = Field(..., min_length=1, max_length=50000)
