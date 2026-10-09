from app.ingestion.layout_normalizer import clean_layout_artifacts, structure_document_text

def test_clean_layout_artifacts_removes_headers_and_page_numbers():
    raw_pdf_text = (
        "CONFIDENTIAL\n"
        "Page 1 of 5\n"
        "The national cyber defense council identified multiple target infra-\n"
        "structures under reconnaissance.\n"
        "- 1 -\n"
        "RESTRICTED\n"
    )
    cleaned = clean_layout_artifacts(raw_pdf_text)
    assert "CONFIDENTIAL" not in cleaned
    assert "Page 1 of 5" not in cleaned
    assert "- 1 -" not in cleaned
    assert "infrastructures" in cleaned  # de-hyphenated

def test_structure_document_text_identifies_headings_and_tables():
    raw_doc = (
        "INCIDENT OVERVIEW\n"
        "A distributed denial of service attack affected central gateways.\n\n"
        "Annexure A: System Outages\n"
        "Node | Latency | Status\n"
        "Alpha | 450ms | Degraded\n"
        "Beta | 32ms | Operational\n"
    )
    structured, meta = structure_document_text(raw_doc)
    assert meta["headings_found"] >= 1
    assert meta["table_rows_count"] >= 2
    assert "## INCIDENT OVERVIEW" in structured
    assert "| Node | Latency | Status |" in structured
