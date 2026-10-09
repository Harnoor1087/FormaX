# FormaX AI – Member 2: AI Pipeline & Security Backend

This backend module fulfills the **Member 2 Responsibilities** defined in the project synopsis and architecture specification for **FormaX AI** (GenAI Platform for Automated Content Transformation).

---

## 1. Role and Boundaries

- **Input Ingestion & Validation**: Validates requests received from Member 1's frontend dashboard (`TransformRequest`).
- **Input Sanitization & Security**: Normalizes text and defends against prompt injection / instruction overrides (OWASP Top 10 for LLM Applications: LLM01). Outputs structured decisions (`allow`, `review`, `block`).
- **Context & Intent Analysis**: Analyzes source content using structured LLM prompting to extract topics, verified key facts, domain, entities, and urgency into `StructuredContext`.
- **Format Router**: Validates requested output formats against an explicit allowlist and dispatches the validated context to registered generator modules.
- **Handoff to Member 3**: Member 3 registers content generation functions (`advisory`, `linkedin_post`, etc.) directly into the `FormatRouter`.

---

## 2. API Endpoints

### `GET /health`
Returns service health and operational metadata.

### `POST /api/v1/process`
Primary Member 2 pipeline endpoint.

**Request (`TransformRequest`):**
```json
{
  "source_text": "Severe cyclone alert issued for coastal regions. Disaster relief teams deployed.",
  "output_types": ["advisory", "linkedin_post"],
  "audience": "government officials",
  "tone": "formal",
  "language": "English",
  "objective": "inform",
  "detail_level": "medium",
  "source_type": "text",
  "source_filename": "incident_report.txt"
}
```

**Response (`ProcessResponse`):**
```json
{
  "status": "success",
  "request_id": "req_8a3f91d2",
  "security": {
    "decision": "allow",
    "risk_score": 0.05,
    "detected_signals": [],
    "reason_code": "SEC_CLEAN",
    "explanation": "Input cleared all security validation checks."
  },
  "context": {
    "source_text": "Severe cyclone alert issued for coastal regions. Disaster relief teams deployed.",
    "topic": "Severe Cyclone Warning",
    "domain": "Disaster Management",
    "key_facts": [
      "Severe cyclone alert issued for coastal regions",
      "Disaster relief teams deployed"
    ],
    "entities": ["Coastal Regions", "Disaster Relief Teams"],
    "urgency": "high",
    "constraints": ["Preserve original source facts strictly"],
    "missing_information": [],
    "parameters": {
      "audience": "government officials",
      "tone": "formal",
      "language": "English",
      "objective": "inform",
      "detail_level": "medium"
    }
  },
  "outputs": [...],
  "errors": []
}
```

### `POST /api/v1/ingestion/classify`
Analyzes raw source text to auto-detect content type (`incident_report`, `policy_document`, `press_release`, `executive_brief`, `meeting_transcript`), domain, recommended tone, objective, audience, and recommended formats.

### `GET /api/v1/security/audit-trail`
Operator endpoint to view recent security audit events and detected flags without exposing confidential details or credentials.

### `POST /api/generate` (Member 1 Compatibility Bridge)
Directly consumes Member 1's frontend requests and returns `{ "outputs": [ ... ] }`.

---

## 3. Security Hardening (Phase 2 - Pillar 1)

- **Rate Limiting & Denial-of-Wallet Gatekeeper**: Sliding-window rate limiting on API endpoints (defaults to 30 req/min per IP) returning `HTTP 429 Too Many Requests`.
- **Sensitive Data & PII Masking**: Automatic detection and redaction of emails, international phone numbers, Aadhaar/Government IDs, and secret API keys/tokens before context analysis.
- **Forensic Audit Logger**: Maintains an access-controlled audit trail storing request IDs, timestamps, security decisions, risk scores, and sensitive flags without storing raw credentials or secret tokens.

---

## 4. Enhanced Ingestion & Pre-Processing (Phase 2 - Pillar 2)

- **Layout-Aware Document Normalization (`layout_normalizer.py`)**: Strips running headers, footers, standalone page numbers, resolves hyphenated line-breaks across boundaries, and preserves markdown heading structures and tabular rows.
- **Audio/Video Speech-to-Text Normalizer (`transcript_normalizer.py`)**: Cleans Whisper-family automated transcripts by removing timestamp ranges (`[00:01:23]`), stripping disfluencies (`uh`, `um`), and structuring speaker turns (`Alice: ...`, `Bob: ...`).
- **Content Classification & Domain Auto-Tagging (`content_classifier.py`)**: Classifies text into defined operational archetypes and outputs recommended communication parameters (`tone`, `objective`, `audience`) and suggested output formats.

---

## 5. Generator Architecture & Member 3 Plug-in Interface (Phase 2 - Pillar 3)

The platform comes pre-configured with reference implementations for all **7 format generators** specified in the synopsis:
1. **`advisory`**: Formal governmental/institutional advisory with classifications, findings, entity scope, mitigation directives, and grounding notice.
2. **`linkedin_post`**: Executive thought-leadership narrative with hook, structured takeaways, and domain hashtags.
3. **`twitter_thread`**: Numbered sequence (`1/N` ... `N/N`) with bulleted key claims and call to action.
4. **`executive_summary`**: High-level strategic briefing with situation scope, evidence, risk rating, and decision points.
5. **`presentation`**: 4-slide structured deck (Agenda, Situational Context, Key Data/Findings, Action Items).
6. **`infographic`**: Visual storytelling blueprint (Headline Banner, Callout Cards, 3-step Timeline Flow, Attribution).
7. **`video_package`**: Complete multimedia package including 4-scene storyboard, voiceover narration, and SRT subtitles.

### Fault-Tolerant Fan-Out
The router provides **error isolation**: If a generator encounters an unhandled exception or third-party renderer timeout, it is caught safely and isolated to that specific output item, allowing all other requested format generators to complete successfully without failing the pipeline.

### Member 3 Plug-in Override Example

Member 3 can override any generator or register new ones with zero changes to Member 2's core code:

```python
from app.routing.format_router import default_router
from app.schemas.context import StructuredContext
from app.schemas.response import GenerateOutputItem

def custom_advisory_generator(ctx: StructuredContext) -> GenerateOutputItem:
    # Access verified source facts and operator parameters
    facts = ctx.key_facts
    target_audience = ctx.parameters.audience
    return GenerateOutputItem(
        output_type="advisory",
        title=f"Custom Advisory: {ctx.topic}",
        summary=f"Issued for {target_audience}",
        key_points=facts[:4],
        body="...",
    )

# Register into the format router
default_router.register("advisory", custom_advisory_generator)
```

---

## 6. Acceptance Criteria & Final Handoff Checklist

| No. | Acceptance Criterion | Status |
|---|---|---|
| 1 | Request validation works for valid and invalid inputs | **Passed** (`test_request_validation.py`) |
| 2 | Security assessment returns a structured decision (`allow`/`review`/`block`) | **Passed** (`test_security.py`) |
| 3 | Source content is treated as untrusted input with strict delimiters | **Passed** (`app/ai/prompt_builder.py`) |
| 4 | Context analysis returns the agreed Pydantic schema | **Passed** (`test_context_analysis.py`) |
| 5 | Important source facts are preserved without unsupported additions | **Passed** (`app/ai/context_analyzer.py`) |
| 6 | Router handles all 7 supported output formats | **Passed** (`test_member3_integration.py`) |
| 7 | Member 3 can register interfaces without modifying internal code | **Passed** (`FormatRouter.register`) |
| 8 | API errors follow agreed response contract | **Passed** (`test_api_endpoints.py`) |
| 9 | Automated test suite passes (41/41 tests) | **Passed** (`pytest backend/tests/ -v`) |
| 10 | Documentation and integration examples complete | **Passed** (`backend/README.md`) |

---

## 7. Running the Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Run all 41 unit and integration tests
pytest tests/ -v
```
