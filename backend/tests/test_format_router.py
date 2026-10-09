import pytest
from app.routing.format_router import FormatRouter
from app.schemas.request import OutputType
from app.schemas.context import StructuredContext, GenerationParameters
from app.schemas.response import GenerateOutputItem

def test_format_router_routes_multi_outputs():
    router = FormatRouter()
    ctx = StructuredContext(
        source_text="Test source text content",
        topic="Cloud Migration Roadmap",
        domain="Information Technology",
        key_facts=["Phase 1 begins next month", "Servers being provisioned"],
        entities=["CloudOps Team"],
        urgency="medium",
        constraints=["Maintain zero downtime"],
        parameters=GenerationParameters(
            audience="leadership",
            tone="formal",
            language="English",
            objective="inform",
            detail_level="detailed",
        )
    )

    outputs = router.route(ctx, [OutputType.ADVISORY, OutputType.LINKEDIN_POST])
    assert len(outputs) == 2
    assert outputs[0].output_type == "advisory"
    assert outputs[1].output_type == "linkedin_post"
    assert "Cloud Migration Roadmap" in outputs[0].title

def test_member_3_custom_generator_registration():
    router = FormatRouter()
    
    # Simulate Member 3 registering a custom generator
    def custom_advisory_generator(ctx: StructuredContext) -> GenerateOutputItem:
        return GenerateOutputItem(
            output_type="advisory",
            title="Custom Member 3 Advisory Format",
            summary=f"Tailored for {ctx.parameters.audience}",
            key_points=ctx.key_facts,
            body="Custom formatted advisory body.",
        )

    router.register("advisory", custom_advisory_generator)
    
    ctx = StructuredContext(
        source_text="Source data",
        topic="Incident Response",
        domain="Security",
        key_facts=["Fact A"],
        entities=[],
        urgency="high",
        constraints=[],
        parameters=GenerationParameters(
            audience="field staff",
            tone="urgent",
            language="English",
            objective="alert",
            detail_level="brief",
        )
    )

    outputs = router.route(ctx, [OutputType.ADVISORY])
    assert len(outputs) == 1
    assert outputs[0].title == "Custom Member 3 Advisory Format"
    assert outputs[0].body == "Custom formatted advisory body."
