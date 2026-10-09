from app.security.sensitive_data_filter import SensitiveDataFilter

def test_detect_and_redact_pii():
    filter_engine = SensitiveDataFilter()
    sample_text = (
        "Lead coordinator officer John Doe can be reached at john.doe@agency.gov.in "
        "or urgent mobile +91-9876543210. Aadhaar verification 1234 5678 9012 completed."
    )

    detected_tags = filter_engine.scan(sample_text)
    assert "EMAIL_ADDRESS" in detected_tags
    assert "PHONE_NUMBER" in detected_tags
    assert "GOVERNMENT_ID" in detected_tags

    redacted_text, tags = filter_engine.redact(sample_text)
    assert "john.doe@agency.gov.in" not in redacted_text
    assert "[EMAIL_REDACTED]" in redacted_text
    assert "[PHONE_REDACTED]" in redacted_text
    assert "[GOVT_ID_REDACTED]" in redacted_text

def test_detect_and_redact_api_token():
    filter_engine = SensitiveDataFilter()
    sample_text = "Deploying updates using sk-1234567890abcdef1234567890 securely."
    
    redacted_text, tags = filter_engine.redact(sample_text)
    assert "sk-1234567890abcdef1234567890" not in redacted_text
    assert "[SECRET_KEY_REDACTED]" in redacted_text
    assert "SECRET_TOKEN" in tags

def test_clean_text_no_redaction():
    filter_engine = SensitiveDataFilter()
    sample_text = "Heavy snowfall expected in high-altitude mountain passes over the weekend."
    redacted_text, tags = filter_engine.redact(sample_text)
    
    assert redacted_text == sample_text
    assert len(tags) == 0
