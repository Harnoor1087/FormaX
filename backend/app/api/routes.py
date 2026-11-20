import uuid
import logging
import sqlite3
import re
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Request, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from ..config import settings
from ..schemas.request import TransformRequest
from ..schemas.response import (
    ProcessResponse,
    GenerateResponse,
    GenerateOutputItem,
    GenerateOutputUpdate,
    OutputValidation,
)
from ..schemas.context import StructuredContext, GenerationParameters
from ..schemas.security import SecurityDecision
from ..security.input_validator import normalize_text, validate_source_input
from ..security.injection_detector import InjectionDetector
from ..security.security_policy import evaluate_security_policy
from ..security.rate_limiter import rate_limit_dependency
from ..security.sensitive_data_filter import sensitive_filter
from ..security.audit_logger import audit_logger
from ..security.api_auth import ApiRole, require_roles
from ..errors import LanguageGenerationUnavailable
from ..ingestion.layout_normalizer import clean_layout_artifacts, structure_document_text
from ..ingestion.transcript_normalizer import clean_transcript, parse_speaker_segments
from ..ingestion.content_classifier import classify_content_type, ContentTypeResult
from ..ai.context_analyzer import ContextAnalyzer
from ..ai.content_generator import content_generator
from ..ai.veo_video import build_video_prompt, veo_video_generator
from ..routing.format_router import default_router
from ..generators.validation import validate_output, validate_outputs
from ..storage.generation_store import generation_store

router = APIRouter()
detector = InjectionDetector()
analyzer = ContextAnalyzer()
logger = logging.getLogger(__name__)


def _save_generated_outputs(
    request_id: str,
    context: StructuredContext,
    outputs: List[GenerateOutputItem],
) -> tuple[str, OutputValidation, List[GenerateOutputItem]]:
    validation = validate_outputs(context, outputs)
    validated_outputs = [
        output.model_copy(update={"validation": validate_output(context, output)})
        for output in outputs
    ]
    generation_id, saved_outputs = generation_store.create_generation(
        request_id=request_id,
        context=context,
        validation=validation,
        outputs=validated_outputs,
        generation_mode=_generation_mode_for(validated_outputs),
    )
    return generation_id, validation, saved_outputs


def _generation_mode_for(outputs: List[GenerateOutputItem]) -> str:
    modes = {output.generation_mode for output in outputs if output.generation_mode}
    if "template_fallback" in modes:
        return "template_fallback"
    if modes == {"template"}:
        return "template"
    if modes == {"gemini", "template"}:
        return "mixed"
    return content_generator.generation_mode


def _route_outputs(
    context: StructuredContext,
    output_types: List[OutputType],
) -> List[GenerateOutputItem]:
    try:
        return default_router.route(context, output_types)
    except LanguageGenerationUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error


def _public_video_job(job: Dict[str, Any]) -> Dict[str, Any]:
    video_job_id = job["video_job_id"]
    return {
        "video_job_id": video_job_id,
        "output_id": job["output_id"],
        "status": job["status"],
        "error": job["error"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
        "download_url": (
            f"/api/v1/video-jobs/{video_job_id}/download"
            if job["status"] == "completed"
            else None
        ),
    }


def _video_file_path(video_job_id: str) -> Path:
    return Path(settings.VIDEO_OUTPUT_DIR).resolve() / f"{video_job_id}.mp4"


def _presentation_sections(body: str) -> List[tuple[str, str]]:
    body = re.sub(
        r"=+\s*(?=\[?\s*(?:slide|स्लाइड|ਸਲਾਈਡ)\s*\d+)",
        "",
        body,
        flags=re.IGNORECASE,
    )
    heading_pattern = re.compile(
        r"(?im)^\s*\[?\s*(?:slide|स्लाइड|ਸਲਾਈਡ)\s*\d+\s*[:：\-]?\s*(.*?)\]?\s*$"
    )
    headings = list(heading_pattern.finditer(body))
    if not headings:
        sections = [
            section.strip()
            for section in re.split(r"\n\s*\n", body)
            if section.strip()
        ]
        return [(f"Slide {index}", section) for index, section in enumerate(sections, 1)]

    sections = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        content = body[heading.end():end].strip(" \n=[]")
        title = heading.group(1).strip(" []") or f"Slide {index + 1}"
        sections.append((title, content))
    return sections


def _build_presentation(output: Dict[str, Any]) -> BytesIO:
    from pptx.dml.color import RGBColor
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    
    deck = Presentation()
    deck.slide_width = Inches(10)
    deck.slide_height = Inches(5.625)  # 16:9 aspect ratio
    sections = _presentation_sections(output["body"])
    if not sections:
        sections = [("Key Information", output["body"])]

    # Gamma-inspired color palette
    PRIMARY = RGBColor(99, 102, 241)  # Indigo
    ACCENT = RGBColor(236, 72, 153)  # Pink
    TEXT_DARK = RGBColor(15, 23, 42)  # Slate 900
    TEXT_LIGHT = RGBColor(255, 255, 255)
    BG_WHITE = RGBColor(255, 255, 255)
    CARD_BG = RGBColor(241, 245, 249)  # Slate 100
    
    for slide_index, (title, content) in enumerate(sections, 1):
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        
        # Clean white background
        background = slide.background.fill
        background.solid()
        background.fore_color.rgb = BG_WHITE

        # Decorative gradient header shape
        header_shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(0.4), Inches(0.4), Inches(9.2), Inches(1.2)
        )
        header_shape.fill.solid()
        header_shape.fill.fore_color.rgb = PRIMARY
        header_shape.line.fill.background()
        header_shape.shadow.inherit = False
        
        # Title with modern typography
        title_box = slide.shapes.add_textbox(
            Inches(0.6), Inches(0.55), Inches(7.5), Inches(0.9)
        )
        title_frame = title_box.text_frame
        title_frame.word_wrap = True
        title_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        title_paragraph = title_frame.paragraphs[0]
        title_paragraph.text = title if slide_index > 1 else output["title"]
        title_paragraph.font.name = "Calibri"
        title_paragraph.font.size = Pt(32)
        title_paragraph.font.bold = True
        title_paragraph.font.color.rgb = TEXT_LIGHT
        
        # Slide number - modern circular badge
        badge_size = Inches(0.5)
        badge = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(8.6), Inches(0.7), badge_size, badge_size
        )
        badge.fill.solid()
        badge.fill.fore_color.rgb = ACCENT
        badge.line.fill.background()
        badge.shadow.inherit = False
        
        badge_text = badge.text_frame
        badge_text.vertical_anchor = MSO_ANCHOR.MIDDLE
        badge_para = badge_text.paragraphs[0]
        badge_para.text = str(slide_index)
        badge_para.font.size = Pt(20)
        badge_para.font.bold = True
        badge_para.font.color.rgb = TEXT_LIGHT
        badge_para.alignment = PP_ALIGN.CENTER

        # Content card with subtle background
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(0.5), Inches(2.0), Inches(9.0), Inches(3.0)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = CARD_BG
        card.line.color.rgb = RGBColor(226, 232, 240)  # Slate 200
        card.line.width = Pt(1)
        card.shadow.inherit = False

        # Content text with modern styling
        content_box = slide.shapes.add_textbox(
            Inches(0.8), Inches(2.2), Inches(8.4), Inches(2.6)
        )
        content_frame = content_box.text_frame
        content_frame.word_wrap = True
        content_frame.margin_left = Inches(0.3)
        content_frame.margin_right = Inches(0.3)
        content_frame.margin_top = Inches(0.2)
        
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            lines = [output["summary"]]
            
        for line_index, line in enumerate(lines):
            paragraph = content_frame.paragraphs[0] if line_index == 0 else content_frame.add_paragraph()
            
            if line.startswith(("•", "-", "*")):
                clean_line = line.lstrip("•-* ").strip()
                paragraph.text = f"● {clean_line}"
                paragraph.level = 0
            else:
                paragraph.text = line
                
            paragraph.font.name = "Calibri"
            paragraph.font.size = Pt(16 if len(lines) < 8 else 14)
            paragraph.font.color.rgb = TEXT_DARK
            paragraph.space_after = Pt(12)
            paragraph.line_spacing = 1.4
            
        # Decorative accent line at bottom
        accent_line = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            Inches(0.5), Inches(5.3), Inches(3.0), Inches(0.08)
        )
        accent_line.fill.solid()
        accent_line.fill.fore_color.rgb = ACCENT
        accent_line.line.fill.background()

        # Modern footer
        footer_box = slide.shapes.add_textbox(
            Inches(3.8), Inches(5.15), Inches(5.7), Inches(0.3)
        )
        footer_para = footer_box.text_frame.paragraphs[0]
        footer_para.text = f"FormaX AI • {slide_index} of {len(sections)}"
        footer_para.alignment = PP_ALIGN.RIGHT
        footer_para.font.name = "Calibri"
        footer_para.font.size = Pt(10)
        footer_para.font.color.rgb = RGBColor(100, 116, 139)  # Slate 500
        footer_para.font.italic = True

    content = BytesIO()
    deck.save(content)
    content.seek(0)
    return content


@router.get("/health", tags=["System"])
def health_check():
    """Health status and diagnostic endpoint."""
    return {
        "status": "healthy",
        "service": "FormaX AI Backend",
        "role": "AI Pipeline, Generation & Review",
        "version": "1.0.0"
    }

@router.get("/v1/auth/me", tags=["Authentication"])
def get_current_user_role(auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("operator", "reviewer"))):
    role, token_id = auth
    return {"role": role, "token_id": token_id}

@router.get("/v1/security/audit-trail", tags=["Security Governance"])
def get_audit_trail(
    limit: int = 50,
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("operator", "reviewer")),
):
    """
    Operator access to immutable security audit trail (Synopsis Section 5).
    Exposes security decisions and flags without leaking credentials.
    """
    events = audit_logger.get_recent_events(limit=limit)
    return {
        "total_records": len(events),
        "events": events
    }

@router.get("/v1/generations", tags=["Generation Review"])
def list_generations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("operator", "reviewer")),
):
    return {"generations": generation_store.list_generations(limit=limit, offset=offset)}

@router.get("/v1/generations/{generation_id}", tags=["Generation Review"])
def get_generation(
    generation_id: str,
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("operator", "reviewer")),
):
    generation = generation_store.get_generation(generation_id)
    if generation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found.")
    return generation

@router.patch("/v1/outputs/{output_id}", tags=["Generation Review"])
def edit_generated_output(
    output_id: str,
    update: GenerateOutputUpdate,
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("reviewer")),
):
    existing = generation_store.get_output(output_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated output not found.")
    generation = generation_store.get_generation(existing["generation_id"])
    if generation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generation not found.")

    context = StructuredContext.model_validate(generation["context"])
    output = GenerateOutputItem(
        output_type=existing["output_type"],
        title=update.title,
        summary=update.summary,
        key_points=update.key_points,
        body=update.body,
    )
    validation = validate_output(context, output)
    updated = generation_store.update_output(output_id, output, validation)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated output not found.")
    return updated

@router.post("/v1/outputs/{output_id}/approve", tags=["Generation Review"])
def approve_generated_output(
    output_id: str,
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("reviewer")),
):
    output = generation_store.get_output(output_id)
    if output is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated output not found.")
    validation = OutputValidation.model_validate(output["validation"])
    if not validation.schema_valid or not validation.consistency_valid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Output must pass schema and consistency validation before approval.", "issues": validation.issues},
        )
    return generation_store.approve_output(output_id)

@router.post("/v1/outputs/{output_id}/export", tags=["Generation Review"])
def record_generated_output_export(
    output_id: str,
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("reviewer")),
):
    output = generation_store.record_export(output_id)
    if output is None:
        if generation_store.get_output(output_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated output not found.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Approve the output before exporting.")
    return output


@router.post(
    "/v1/outputs/{output_id}/presentation.pptx",
    tags=["Generation Review"],
)
def export_presentation_pptx(
    output_id: str,
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("reviewer")),
):
    output = generation_store.get_output(output_id)
    if output is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated output not found.")
    if output["output_type"] != "presentation":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only presentation outputs can be exported as PowerPoint files.",
        )
    if output["review_status"] != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approve the presentation before exporting it.",
        )

    content = _build_presentation(output)
    if generation_store.record_export(output_id) is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approve the presentation before exporting it.",
        )
    filename = re.sub(r"[^A-Za-z0-9_-]+", "-", output["title"]).strip("-")[:60]
    filename = filename or "formax-presentation"
    return StreamingResponse(
        content,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pptx"'},
    )


@router.post(
    "/v1/outputs/{output_id}/video",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Video Generation"],
)
def start_output_video(
    output_id: str,
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("reviewer")),
):
    if not settings.GEMINI_API_KEY.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Video generation is not configured. Set GEMINI_API_KEY in the backend .env and restart the server.",
        )

    output = generation_store.get_output(output_id)
    if output is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated output not found.")
    if output["output_type"] != "video_package":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an approved video package can be rendered as a video.",
        )
    if output["review_status"] != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approve the video package before rendering it.",
        )
    validation = OutputValidation.model_validate(output["validation"])
    if not validation.schema_valid or not validation.consistency_valid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The video package must pass validation before rendering.",
        )

    latest_job = generation_store.get_video_job_for_output(output_id)
    if latest_job and latest_job["status"] in {
        "starting",
        "processing",
        "downloading",
        "completed",
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A video render is already running or has completed for this approved draft.",
        )

    try:
        job = generation_store.create_video_job(output_id, output["updated_at"])
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A video render is already running or has completed for this approved draft.",
        ) from error

    generation_store.record_video_event(output_id, "video_generation_started")
    prompt = build_video_prompt(
        GenerateOutputItem(
            output_type=output["output_type"],
            title=output["title"],
            summary=output["summary"],
            key_points=output["key_points"],
            body=output["body"],
        )
    )
    try:
        operation_name = veo_video_generator.start(prompt)
        submitted_job = generation_store.submit_video_job(job["video_job_id"], operation_name)
        if submitted_job is None:
            raise RuntimeError("The video job could not be saved after provider submission.")
    except Exception as error:
        logger.exception("Veo failed to start video job %s", job["video_job_id"])
        provider_status = getattr(error, "code", None)
        if provider_status == 429:
            error_detail = (
                "Google Veo quota is exhausted (HTTP 429). Check Google AI billing "
                "and video-generation quota before retrying."
            )
            http_status = status.HTTP_429_TOO_MANY_REQUESTS
        elif provider_status == 503:
            error_detail = "Google Veo is temporarily unavailable (HTTP 503). Retry later."
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            error_detail = (
                "The video provider could not start this render. "
                "Check the backend logs and Gemini API access."
            )
            http_status = status.HTTP_502_BAD_GATEWAY
        generation_store.fail_video_job(
            job["video_job_id"],
            error_detail,
        )
        raise HTTPException(
            status_code=http_status,
            detail=error_detail,
        ) from error
    return _public_video_job(submitted_job)


@router.get("/v1/outputs/{output_id}/video", tags=["Video Generation"])
def get_output_video_job(
    output_id: str,
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("reviewer")),
):
    if generation_store.get_output(output_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generated output not found.")
    job = generation_store.get_video_job_for_output(output_id)
    return {"job": _public_video_job(job) if job else None}


@router.get("/v1/video-jobs/{video_job_id}", tags=["Video Generation"])
def get_video_job_status(
    video_job_id: str,
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("reviewer")),
):
    job = generation_store.get_video_job(video_job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video job not found.")

    if job["status"] == "processing":
        try:
            operation = veo_video_generator.get_operation(job["operation_name"])
        except Exception as error:
            logger.exception("Veo status check failed for video job %s", video_job_id)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not check video-render progress. Retry the status check.",
            ) from error

        if operation.done:
            if operation.error:
                logger.error("Veo returned a failed operation for video job %s", video_job_id)
                job = generation_store.fail_video_job(
                    video_job_id,
                    "Veo could not complete this clip. Check Google AI access and quota, then retry.",
                )
                return _public_video_job(job)

            generated_videos = (
                operation.response.generated_videos
                if operation.response and operation.response.generated_videos
                else []
            )
            if not generated_videos:
                job = generation_store.fail_video_job(
                    video_job_id,
                    "Veo completed without returning a video. Retry the render.",
                )
                return _public_video_job(job)

            if generation_store.claim_video_download(video_job_id):
                destination = _video_file_path(video_job_id)
                temporary_path = destination.with_name(f"{video_job_id}.partial")
                destination.parent.mkdir(parents=True, exist_ok=True)
                try:
                    veo_video_generator.download(generated_videos[0], temporary_path)
                    if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
                        raise RuntimeError("The video provider returned an empty download.")
                    temporary_path.replace(destination)
                    job = generation_store.complete_video_job(
                        video_job_id,
                        str(destination),
                    )
                    if job is None:
                        destination.unlink(missing_ok=True)
                        latest_job = generation_store.get_video_job(video_job_id)
                        return _public_video_job(latest_job)
                except Exception as error:
                    temporary_path.unlink(missing_ok=True)
                    logger.exception("Veo download failed for video job %s", video_job_id)
                    job = generation_store.fail_video_job(
                        video_job_id,
                        "Veo finished, but FormaX could not save the MP4. Check backend logs and retry.",
                    )
                    if destination.exists():
                        destination.unlink()
                    if job is None:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="The video brief changed while the render was finishing.",
                        ) from error
                    return _public_video_job(job)
            else:
                job = generation_store.get_video_job(video_job_id)

    return _public_video_job(job)


@router.get("/v1/video-jobs/{video_job_id}/download", tags=["Video Generation"])
def download_video_job(
    video_job_id: str,
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("reviewer")),
):
    job = generation_store.get_video_job(video_job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video job not found.")
    if job["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The MP4 is not ready for download.",
        )
    output = generation_store.get_output(job["output_id"])
    if (
        output is None
        or output["review_status"] != "approved"
        or output["updated_at"] != job["output_updated_at"]
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The approved video brief has changed. Approve the revised draft before downloading.",
        )

    path = _video_file_path(video_job_id)
    if job["file_path"] != str(path) or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="The generated MP4 is no longer available on this server.",
        )
    generation_store.record_video_event(job["output_id"], "video_downloaded")
    return FileResponse(path, media_type="video/mp4", filename=f"formax-{video_job_id[:8]}.mp4")


@router.post(
    "/v1/ingestion/classify",
    response_model=ContentTypeResult,
    tags=["Ingestion & Pre-processing"],
    dependencies=[Depends(require_roles("operator", "reviewer"))],
)
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

@router.post(
    "/v1/process",
    response_model=ProcessResponse,
    tags=["AI Pipeline"],
    dependencies=[
        Depends(rate_limit_dependency),
        Depends(require_roles("operator", "reviewer")),
    ],
)
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
    outputs = _route_outputs(structured_context, request.output_types)
    generation_id, validation, outputs = _save_generated_outputs(request_id, structured_context, outputs)

    return ProcessResponse(
        status="success",
        request_id=request_id,
        security=security_result,
        context=structured_context,
        generation_id=generation_id,
        generation_mode=_generation_mode_for(outputs),
        validation=validation,
        outputs=outputs,
        errors=validation.issues
    )

@router.post(
    "/generate",
    response_model=GenerateResponse,
    tags=["Member 1 Compatibility"],
    dependencies=[
        Depends(rate_limit_dependency),
        Depends(require_roles("operator", "reviewer")),
    ],
)
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

    outputs = _route_outputs(structured_context, request.output_types)
    generation_id, validation, outputs = _save_generated_outputs(request_id, structured_context, outputs)
    return GenerateResponse(
        outputs=outputs,
        request_id=request_id,
        generation_id=generation_id,
        generation_mode=_generation_mode_for(outputs),
        security=security_result,
        validation=validation,
    )
