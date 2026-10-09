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

## 4. Integration Guide for Member 3

Member 3 owns the generation logic for specific formats (Advisory, LinkedIn, Executive Summary, etc.). To connect a generator:

```python
from app.routing.format_router import default_router
from app.schemas.context import StructuredContext
from app.schemas.response import GenerateOutputItem

def generate_advisory(ctx: StructuredContext) -> GenerateOutputItem:
    # Use ctx.topic, ctx.key_facts, ctx.parameters to construct output
    return GenerateOutputItem(
        output_type="advisory",
        title=f"Official Advisory: {ctx.topic}",
        summary=f"Prepared for {ctx.parameters.audience}",
        key_points=ctx.key_facts,
        body="...",
    )

# Register into the router
default_router.register("advisory", generate_advisory)
```

---

## 4. Running the Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
pytest tests/ -v
```
