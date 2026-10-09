import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Request, Depends
from ..config import settings
from ..schemas.request import TransformRequest
from ..schemas.response import ProcessResponse, GenerateResponse, GenerateOutputItem
from ..schemas.context import StructuredContext, GenerationParameters
from ..schemas.security import SecurityDecision
from ..security.input_validator import normalize_text, validate_source_input
from ..security.injection_detector import InjectionDetector
from ..security.security_policy import evaluate_security_policy
from ..security.rate_limiter import rate_limit_dependency
from ..security.sensitive_data_filter import sensitive_filter
from ..security.audit_logger import audit_logger
from ..ingestion.layout_normalizer import clean_layout_artifacts, structure_document_text
from ..ingestion.transcript_normalizer import clean_transcript, parse_speaker_segments
from ..ingestion.content_classifier import classify_content_type, ContentTypeResult
from ..ai.context_analyzer import ContextAnalyzer
from ..routing.format_router import default_router

router = APIRouter()
detector = InjectionDetector()
analyzer = ContextAnalyzer()

@router.get("/health", tags=["System"])
def health_check():
    """Health status and diagnostic endpoint."""
    return {
        "status": "healthy",
        "service": "FormaX AI Backend",
        "role": "Member 2: AI Pipeline & Security",
        "version": "1.0.0"
    }

@router.get("/v1/security/audit-trail", tags=["Security Governance"])
def get_audit_trail(limit: int = 50):
    """
    Operator access to immutable security audit trail (Synopsis Section 5).
    Exposes security decisions and flags without leaking credentials.
    """
    events = audit_logger.get_recent_events(limit=limit)
    return {
        "total_records": len(events),
        "events": events
    }

@router.post("/v1/ingestion/classify", response_model=ContentTypeResult, tags=["Ingestion & Pre-processing"])
def classify_source_content(request: dict):
    """
    Lightweight content classifier and format recommendation endpoint (Synopsis Section 4).
    Auto-detects whether source is an incident report, policy document, press release, or transcript.
    """
    text = request.get("source_text", "").strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source_text cannot be empty")
    
    clean_text = clean_layout_artifacts(normalize_text(text))
    return classify_content_type(clean_text)

@router.post("/v1/process", response_model=ProcessResponse, tags=["AI Pipeline"], dependencies=[Depends(rate_limit_dependency)])
def process_pipeline(request: TransformRequest, raw_req: Request):
    """
    Core AI Pipeline & Security processing endpoint (Section 3.6).
    1. Enforces rate limiting per client IP.
    2. Validates incoming request.
    3. Normalizes layout artifacts & screens for PII.
    4. Auto-classifies content type and structure.
    5. Performs prompt-injection security assessment.
    6. Records event in security audit logger.
    7. Analyzes source context and intent.
    8. Constructs structured AI context with ingestion metadata.
    9. Routes to appropriate generators.
    """
    request_id = f"req_{uuid.uuid4().hex[:10]}"
    client_ip = raw_req.client.host if raw_req.client else "unknown"
    
    # 1. Normalize and clean layout artifacts
    normalized_raw = normalize_text(request.source_text)
    clean_text, layout_meta = structure_document_text(normalized_raw)
    
    is_valid, error_msg = validate_source_input(clean_text)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_msg)

    # 2. Content classification & domain detection
    classification = classify_content_type(clean_text)

    # 3. PII / Sensitive data screening & redaction
    sensitive_flags = []
    if settings.ENABLE_PII_REDACTION:
        clean_text, sensitive_flags = sensitive_filter.redact(clean_text)

    # 4. Security Assessment
    risk_score, signals = detector.scan(clean_text)
    security_result = evaluate_security_policy(risk_score, signals)

    # 5. Audit Logging (records event without raw secrets or credentials)
    output_type_names = [t.value for t in request.output_types]
    audit_logger.log_event(
        request_id=request_id,
        client_ip=client_ip,
        decision=security_result.decision.value,
        risk_score=security_result.risk_score,
        detected_signals=security_result.detected_signals,
        reason_code=security_result.reason_code,
        output_types=output_type_names,
        source_length=len(clean_text),
        sensitive_flags=sensitive_flags,
    )

    # If blocked by security policy, return blocked outcome safely
    if security_result.is_blocked:
        return ProcessResponse(
            status="blocked",
            request_id=request_id,
            security=security_result,
            context=None,
            outputs=[],
            errors=[security_result.explanation]
        )

    # 6. Context & Intent Analysis
    extracted = analyzer.analyze(clean_text)

    # 7. Construct Structured Context with Ingestion Metadata
    params = GenerationParameters(
        audience=request.audience.value,
        tone=request.tone.value,
        language=request.language.value,
        objective=request.objective.value,
        detail_level=request.detail_level.value,
    )
    structured_context = StructuredContext(
        source_text=clean_text,
        topic=extracted.topic,
        domain=classification.domain if classification.domain != "General Operations" else extracted.domain,
        key_facts=extracted.key_facts,
        entities=extracted.entities,
        urgency=extracted.urgency,
        constraints=extracted.constraints,
        missing_information=extracted.missing_information,
        parameters=params,
        ingestion_metadata={
            "content_type": classification.content_type,
            "confidence": classification.confidence,
            "suggested_outputs": classification.suggested_outputs,
            "layout": layout_meta,
        }
    )

    # 8. Route to generators
    outputs = default_router.route(structured_context, request.output_types)
    serialized_outputs = [item.model_dump() for item in outputs]

    return ProcessResponse(
        status="success",
        request_id=request_id,
        security=security_result,
        context=structured_context,
        outputs=serialized_outputs,
        errors=[]
    )

@router.post("/generate", response_model=GenerateResponse, tags=["Member 1 Compatibility"], dependencies=[Depends(rate_limit_dependency)])
def generate_compat(request: TransformRequest, raw_req: Request):
    """
    Compatibility bridge matching Member 1's frontend contract: POST /api/generate.
    """
    request_id = f"req_{uuid.uuid4().hex[:10]}"
    client_ip = raw_req.client.host if raw_req.client else "unknown"

    clean_text = normalize_text(request.source_text)
    is_valid, error_msg = validate_source_input(clean_text)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    sensitive_flags = []
    if settings.ENABLE_PII_REDACTION:
        clean_text, sensitive_flags = sensitive_filter.redact(clean_text)

    # Security check
    risk_score, signals = detector.scan(clean_text)
    security_result = evaluate_security_policy(risk_score, signals)

    # Audit Logging
    output_type_names = [t.value for t in request.output_types]
    audit_logger.log_event(
        request_id=request_id,
        client_ip=client_ip,
        decision=security_result.decision.value,
        risk_score=security_result.risk_score,
        detected_signals=security_result.detected_signals,
        reason_code=security_result.reason_code,
        output_types=output_type_names,
        source_length=len(clean_text),
        sensitive_flags=sensitive_flags,
    )

    if security_result.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security alert: {security_result.explanation}"
        )

    # Analyze & Structure
    extracted = analyzer.analyze(clean_text)
    params = GenerationParameters(
        audience=request.audience.value,
        tone=request.tone.value,
        language=request.language.value,
        objective=request.objective.value,
        detail_level=request.detail_level.value,
    )
    structured_context = StructuredContext(
        source_text=clean_text,
        topic=extracted.topic,
        domain=extracted.domain,
        key_facts=extracted.key_facts,
        entities=extracted.entities,
        urgency=extracted.urgency,
        constraints=extracted.constraints,
        missing_information=extracted.missing_information,
        parameters=params,
    )

    outputs = default_router.route(structured_context, request.output_types)
    return GenerateResponse(
        outputs=outputs,
        request_id=request_id,
        security=security_result,
    )
