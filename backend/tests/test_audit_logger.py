from app.security.audit_logger import SecurityAuditLogger

def test_audit_logger_records_and_retrieves():
    logger = SecurityAuditLogger(log_file="logs/test_audit.jsonl", max_memory_entries=10)
    logger.clear()

    event = logger.log_event(
        request_id="req_test_99",
        client_ip="192.168.1.100",
        decision="allow",
        risk_score=0.15,
        detected_signals=[],
        reason_code="SEC_CLEAN",
        output_types=["advisory"],
        source_length=350,
        sensitive_flags=["EMAIL_ADDRESS"],
    )

    assert event["request_id"] == "req_test_99"
    assert event["decision"] == "allow"
    assert event["risk_score"] == 0.15

    recent = logger.get_recent_events(limit=5)
    assert len(recent) == 1
    assert recent[0]["request_id"] == "req_test_99"
    assert recent[0]["client_ip"] == "192.168.1.100"

    logger.clear()
