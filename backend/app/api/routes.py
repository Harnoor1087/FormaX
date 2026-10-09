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

@router.post("/v1/process", response_model=ProcessResponse, tags=["AI Pipeline"], dependencies=[Depends(rate_limit_dependency)])
def process_pipeline(request: TransformRequest, raw_req: Request):
    """
    Core AI Pipeline & Security processing endpoint (Section 3.6).
    1. Enforces rate limiting per client IP.
    2. Validates incoming request.
    3. Normalizes text and screens for PII / sensitive data.
    4. Performs prompt-injection security assessment.
    5. Records event in security audit logger.
    6. Analyzes source context and intent.
    7. Constructs structured AI context.
    8. Routes to appropriate generators.
    """
    request_id = f"req_{uuid.uuid4().hex[:10]}"
    client_ip = raw_req.client.host if raw_req.client else "unknown"
    
    # 1. Normalize and validate input bounds
    clean_text = normalize_text(request.source_text)
    is_valid, error_msg = validate_source_input(clean_text)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_msg)

    # 2. PII / Sensitive data screening & redaction
    sensitive_flags = []
    if settings.ENABLE_PII_REDACTION:
        clean_text, sensitive_flags = sensitive_filter.redact(clean_text)

    # 3. Security Assessment
    risk_score, signals = detector.scan(clean_text)
    security_result = evaluate_security_policy(risk_score, signals)

    # 4. Audit Logging (records event without raw secrets or credentials)
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

    # 5. Context & Intent Analysis
    extracted = analyzer.analyze(clean_text)

    # 6. Construct Structured Context
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

    # 7. Route to generators
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
