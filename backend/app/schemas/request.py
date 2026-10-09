from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class OutputType(str, Enum):
    ADVISORY = "advisory"
    LINKEDIN_POST = "linkedin_post"
    TWITTER_THREAD = "twitter_thread"
    EXECUTIVE_SUMMARY = "executive_summary"
    PRESENTATION = "presentation"
    INFOGRAPHIC = "infographic"
    VIDEO_PACKAGE = "video_package"

class Audience(str, Enum):
    GENERAL_PUBLIC = "general public"
    GOVERNMENT_OFFICIALS = "government officials"
    LEADERSHIP = "leadership"
    FIELD_STAFF = "field staff"
    TECHNICAL_EXPERTS = "technical experts"
    MEDIA = "media"

class Tone(str, Enum):
    FORMAL = "formal"
    NEUTRAL = "neutral"
    URGENT = "urgent"
    FRIENDLY = "friendly"
    PERSUASIVE = "persuasive"

class Language(str, Enum):
    ENGLISH = "English"
    HINDI = "Hindi"
    PUNJABI = "Punjabi"

class Objective(str, Enum):
    INFORM = "inform"
    ALERT = "alert"
    EDUCATE = "educate"
    PERSUADE = "persuade"
    SUMMARISE = "summarise"

class DetailLevel(str, Enum):
    BRIEF = "brief"
    MEDIUM = "medium"
    DETAILED = "detailed"

class TransformRequest(BaseModel):
    """
    Contract matching Member 1 frontend and Section 6.1 of Member 2 document.
    """
    source_text: str = Field(
        ...,
        description="Raw or extracted document text content",
        min_length=1,
        max_length=50000,
    )
    output_types: List[OutputType] = Field(
        ...,
        description="List of requested output artifact types",
        min_length=1,
    )
    audience: Audience = Field(
        default=Audience.GOVERNMENT_OFFICIALS,
        description="Target audience for generated outputs",
    )
    tone: Tone = Field(
        default=Tone.FORMAL,
        description="Communication tone",
    )
    language: Language = Field(
        default=Language.ENGLISH,
        description="Language of generated output",
    )
    objective: Objective = Field(
        default=Objective.INFORM,
        description="Primary communication objective",
    )
    detail_level: DetailLevel = Field(
        default=DetailLevel.MEDIUM,
        description="Depth of detail required",
    )
    source_type: Optional[str] = Field(
        default="text",
        description="Source format descriptor: text, file, pdf, docx",
    )
    source_filename: Optional[str] = Field(
        default=None,
        description="Original name of the uploaded document if applicable",
    )

    @field_validator("source_text")
    @classmethod
    def validate_source_text(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("source_text cannot be empty or only whitespace")
        if len(trimmed) > 50000:
            raise ValueError("source_text exceeds maximum limit of 50,000 characters")
        return trimmed

    @field_validator("output_types")
    @classmethod
    def validate_output_types(cls, v: List[OutputType]) -> List[OutputType]:
        if not v:
            raise ValueError("At least one output_type must be selected")
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for item in v:
            if item not in seen:
                seen.add(item)
                deduped.append(item)
        return deduped

    model_config = {
        "json_schema_extra": {
            "example": {
                "source_text": "Severe cyclone alert issued for northern coastal districts. Evacuations underway.",
                "output_types": ["advisory", "linkedin_post"],
                "audience": "government officials",
                "tone": "formal",
                "language": "English",
                "objective": "inform",
                "detail_level": "medium",
                "source_type": "text",
                "source_filename": "cyclone_report.txt"
            }
        }
    }
