from typing import List, Optional
from pydantic import BaseModel, Field

class GenerationParameters(BaseModel):
    """
    Operator parameters passed through to downstream generators.
    """
    audience: str
    tone: str
    language: str
    objective: str
    detail_level: str

class ExtractedContext(BaseModel):
    """
    Structured analytical information extracted from the source by the LLM.
    """
    topic: str = Field(
        ...,
        description="Identified core topic of the source content"
    )
    domain: str = Field(
        default="General",
        description="Domain or sector (e.g., Cybersecurity, Public Health, Infrastructure, Governance)"
    )
    key_facts: List[str] = Field(
        default_factory=list,
        description="Verified, source-grounded factual claims"
    )
    entities: List[str] = Field(
        default_factory=list,
        description="Named organizations, individuals, locations, or dates extracted from source"
    )
    urgency: str = Field(
        default="medium",
        description="Assessed urgency level: low, medium, high, critical"
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="Explicit constraints or qualifications that generators must adhere to"
    )
    missing_information: Optional[List[str]] = Field(
        default_factory=list,
        description="Ambiguities or unverified elements noted in the source"
    )

class StructuredContext(ExtractedContext):
    """
    Deliverable to Member 3: Combines normalized source text, extracted facts,
    and operator parameters (Section 6.2).
    """
    source_text: str = Field(
        ...,
        description="Clean, normalized original source text"
    )
    parameters: GenerationParameters = Field(
        ...,
        description="Structured operator generation parameters"
    )
