from app.ingestion.content_classifier import classify_content_type

def test_classify_incident_report():
    text = (
        "Severe vulnerability alert CVE-2026-1192 identified in boundary firewalls. "
        "Threat actor exploit detected. Immediate emergency patching and evacuation of compromised subnet required."
    )
    result = classify_content_type(text)
    assert result.content_type == "incident_report"
    assert result.domain == "Emergency & Threat Management"
    assert result.recommended_tone == "urgent"
    assert result.recommended_objective == "alert"
    assert "advisory" in result.suggested_outputs

def test_classify_policy_document():
    text = (
        "Pursuant to statutory compliance guidelines and circular 44, "
        "all subordinate bodies must adopt this regulatory framework clause."
    )
    result = classify_content_type(text)
    assert result.content_type == "policy_document"
    assert result.recommended_tone == "formal"
    assert result.recommended_objective == "inform"

def test_classify_press_release():
    text = (
        "For immediate release: The department spokesperson announced a new public digital initiative. "
        "Media contact information is provided below."
    )
    result = classify_content_type(text)
    assert result.content_type == "press_release"
    assert "media" in result.recommended_audience
    assert "linkedin_post" in result.suggested_outputs

def test_classify_transcript_hint():
    text = (
        "Speaker 1: Hello team.\n"
        "Speaker 2: Good morning. Let's start the status check."
    )
    result = classify_content_type(text, is_transcript_hint=True)
    assert result.content_type == "meeting_transcript"
    assert result.recommended_objective == "summarise"
