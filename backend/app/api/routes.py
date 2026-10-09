import uuid
from fastapi import APIRouter, HTTPException, status
from ..schemas.request import TransformRequest
from ..schemas.response import ProcessResponse, GenerateResponse, GenerateOutputItem
from ..schemas.context import StructuredContext, GenerationParameters
from ..schemas.security import SecurityDecision
from ..security.input_validator import normalize_text, validate_source_input
from ..security.injection_detector import InjectionDetector
from ..security.security_policy import evaluate_security_policy
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

@router.post("/v1/process", response_model=ProcessResponse, tags=["AI Pipeline"])
def process_pipeline(request: TransformRequest):
    """
    Core AI Pipeline & Security processing endpoint (Section 3.6).
    1. Validates incoming request.
    2. Performs input normalization and prompt-injection security checks.
    3. Analyzes source context and intent (topic, facts, entities, urgency).
    4. Constructs the structured AI context.
    5. Routes the request to appropriate generators.
    6. Returns structured, traceable response.
    """
    request_id = f"req_{uuid.uuid4().hex[:10]}"
    
    # 1. Normalize and validate input bounds
    clean_text = normalize_text(request.source_text)
    is_valid, error_msg = validate_source_input(clean_text)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_msg)

    # 2. Security Assessment
    risk_score, signals = detector.scan(clean_text)
    security_result = evaluate_security_policy(risk_score, signals)

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

    # 3. Context & Intent Analysis
    extracted = analyzer.analyze(clean_text)

    # 4. Construct Structured Context
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

    # 5. Route to generators
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

@router.post("/generate", response_model=GenerateResponse, tags=["Member 1 Compatibility"])
def generate_compat(request: TransformRequest):
    """
    Compatibility bridge matching Member 1's frontend contract: POST /api/generate.
    """
    clean_text = normalize_text(request.source_text)
    is_valid, error_msg = validate_source_input(clean_text)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    # Security check
    risk_score, signals = detector.scan(clean_text)
    security_result = evaluate_security_policy(risk_score, signals)
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
        request_id=f"req_{uuid.uuid4().hex[:10]}",
        security=security_result,
    )
