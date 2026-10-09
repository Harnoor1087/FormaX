import pytest
from pydantic import ValidationError
from app.schemas.request import TransformRequest, OutputType, Audience, Tone, Language, Objective, DetailLevel

def test_valid_request():
    req = TransformRequest(
        source_text="This is a verified test report detailing operational metrics.",
        output_types=[OutputType.ADVISORY, OutputType.LINKEDIN_POST],
        audience=Audience.LEADERSHIP,
        tone=Tone.FORMAL,
        language=Language.ENGLISH,
        objective=Objective.INFORM,
        detail_level=DetailLevel.DETAILED,
    )
    assert req.source_text == "This is a verified test report detailing operational metrics."
    assert len(req.output_types) == 2

def test_empty_source_text_fails():
    with pytest.raises(ValidationError):
        TransformRequest(
            source_text="   ",
            output_types=[OutputType.ADVISORY],
        )

def test_empty_output_types_fails():
    with pytest.raises(ValidationError):
        TransformRequest(
            source_text="Valid source content",
            output_types=[],
        )

def test_max_character_limit_exceeded():
    huge_text = "a" * 50001
    with pytest.raises(ValidationError):
        TransformRequest(
            source_text=huge_text,
            output_types=[OutputType.ADVISORY],
        )

def test_duplicate_output_types_deduplicated():
    req = TransformRequest(
        source_text="Testing duplicate output formats",
        output_types=[OutputType.ADVISORY, OutputType.ADVISORY, OutputType.LINKEDIN_POST],
    )
    assert len(req.output_types) == 2
    assert req.output_types == [OutputType.ADVISORY, OutputType.LINKEDIN_POST]
