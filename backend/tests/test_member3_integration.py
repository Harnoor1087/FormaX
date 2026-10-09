import pytest
from app.routing.format_router import default_router, FormatRouter
from app.schemas.request import OutputType
from app.schemas.context import StructuredContext, GenerationParameters
from app.schemas.response import GenerateOutputItem

@pytest.fixture
def sample_context():
    return StructuredContext(
        source_text="Critical security vulnerability CVE-2026-9011 detected in perimeter routers.",
        topic="Critical Perimeter Router Vulnerability",
        domain="Cybersecurity",
        key_facts=[
            "Zero-day vulnerability CVE-2026-9011 actively exploited in the wild.",
            "Emergency patch released by hardware vendor.",
            "All perimeter firewalls require immediate configuration update."
        ],
        entities=["CERT", "Perimeter Network Ops", "Hardware Vendor"],
        urgency="critical",
        constraints=["Preserve verified CVE identifiers"],
        parameters=GenerationParameters(
            audience="government officials",
            tone="urgent",
            language="English",
            objective="alert",
            detail_level="detailed",
        ),
        ingestion_metadata={
            "content_type": "incident_report",
            "confidence": 0.85
        }
    )

def test_all_seven_formats_generate_successfully(sample_context):
    all_formats = [
        OutputType.ADVISORY,
        OutputType.LINKEDIN_POST,
        OutputType.TWITTER_THREAD,
        OutputType.EXECUTIVE_SUMMARY,
        OutputType.PRESENTATION,
        OutputType.INFOGRAPHIC,
        OutputType.VIDEO_PACKAGE,
    ]
    outputs = default_router.route(sample_context, all_formats)
    assert len(outputs) == 7

    types_generated = [o.output_type for o in outputs]
    for fmt in all_formats:
        assert fmt.value in types_generated

def test_video_package_contains_storyboard_script_subtitles(sample_context):
    outputs = default_router.route(sample_context, [OutputType.VIDEO_PACKAGE])
    assert len(outputs) == 1
    pkg = outputs[0]
    assert pkg.output_type == "video_package"
    assert "SCENE 1" in pkg.body
    assert "Storyboard" in pkg.body
    assert "Narration" in pkg.body
    assert "Subtitles (SRT)" in pkg.body

def test_twitter_thread_structure(sample_context):
    outputs = default_router.route(sample_context, [OutputType.TWITTER_THREAD])
    assert len(outputs) == 1
    tweet = outputs[0]
    assert "1/" in tweet.body
    assert "🧵" in tweet.body

def test_cross_output_factual_consistency(sample_context):
    outputs = default_router.route(sample_context, [
        OutputType.ADVISORY,
        OutputType.EXECUTIVE_SUMMARY,
        OutputType.LINKEDIN_POST
    ])
    # All outputs must share the exact same core topic
    for o in outputs:
        assert "Router Vulnerability" in o.title or "Router Vulnerability" in o.body

def test_fault_tolerant_error_isolation(sample_context):
    router = FormatRouter()
    
    # Faulty generator simulates runtime exception from third-party tool
    def broken_generator(ctx: StructuredContext) -> GenerateOutputItem:
        raise RuntimeError("External format renderer connection timeout")

    # Working generator
    def working_generator(ctx: StructuredContext) -> GenerateOutputItem:
        return GenerateOutputItem(
            output_type="linkedin_post",
            title="Working Post",
            summary="Clean summary",
            key_points=["Fact 1"],
            body="Clean body",
        )

    router.register("advisory", broken_generator)
    router.register("linkedin_post", working_generator)

    results = router.route(sample_context, [OutputType.ADVISORY, OutputType.LINKEDIN_POST])
    assert len(results) == 2
    # The broken generator returned an isolated error item
    assert "Error Generating" in results[0].title
    # The working generator completed successfully!
    assert results[1].title == "Working Post"
