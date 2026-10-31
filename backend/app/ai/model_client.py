import json
import logging
import re
from typing import Optional, Dict, Any
from ..config import settings

logger = logging.getLogger(__name__)

class ModelClient:
    """
    LLM API client with offline/mock fallback for unit tests and local development.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = settings.GEMINI_API_KEY if api_key is None else api_key
        self.model_name = model_name or settings.DEFAULT_MODEL
        self._mock_response: Optional[Dict[str, Any]] = None

    def set_mock_response(self, response: Optional[Dict[str, Any]]):
        """Allows test suites to inject deterministic mock outputs."""
        self._mock_response = response

    def generate_json(
        self,
        prompt: str,
        source_text_hint: str = "",
        *,
        allow_heuristic_fallback: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes model completion or returns deterministic fallback structure.
        """
        if self._mock_response is not None:
            return self._mock_response

        # If API key is available, attempt real call
        if self.api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
                text = (response.text or "").strip()
                if not text:
                    raise ValueError("The model returned an empty response.")
                # Clean code fences if present
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\n?", "", text)
                    text = re.sub(r"\n?```$", "", text)
                result = json.loads(text.strip())
                if not isinstance(result, dict):
                    raise ValueError("The model response must be a JSON object.")
                return result
            except Exception as exc:
                logger.error("Gemini JSON generation failed (%s).", type(exc).__name__)
                if not allow_heuristic_fallback:
                    status_code = getattr(exc, "code", None)
                    if status_code == 503:
                        message = "Gemini is temporarily busy (HTTP 503). Retry shortly."
                    elif status_code == 429:
                        message = "Gemini request quota is temporarily exhausted (HTTP 429). Using a labeled template draft."
                    elif status_code == 404:
                        message = "The configured Gemini model is unavailable (HTTP 404). Check MODEL_NAME."
                    elif isinstance(exc, (json.JSONDecodeError, ValueError)):
                        message = "The configured AI model failed to generate valid JSON."
                    else:
                        message = "Gemini could not generate this draft. Check the backend logs and API access."
                    raise RuntimeError(message) from exc

        # Offline / Mock Fallback Extraction: extracts source-grounded facts
        if not allow_heuristic_fallback:
            raise RuntimeError("AI generation requires GEMINI_API_KEY to be configured.")
        return self._heuristic_extraction(source_text_hint)

    def _heuristic_extraction(self, text: str) -> Dict[str, Any]:
        """
        Source-grounded heuristic extractor ensuring zero external dependencies.
        Extracts real sentences, identifies entities, and assesses urgency.
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        first_line = lines[0] if lines else "General Announcement"
        
        # Split sentences
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 15]
        key_facts = sentences[:4]
        
        # Entity detection (Capitalized words/phrases)
        entity_matches = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
        filtered_entities = list(dict.fromkeys([e for e in entity_matches if len(e) > 3]))[:5]

        # Urgency detection
        lower_text = text.lower()
        if any(w in lower_text for w in ["critical", "emergency", "immediate", "fatal", "outage"]):
            urgency = "critical"
        elif any(w in lower_text for w in ["urgent", "warning", "severe", "alert", "danger"]):
            urgency = "high"
        elif any(w in lower_text for w in ["important", "advisory", "notice", "update"]):
            urgency = "medium"
        else:
            urgency = "low"

        # Domain detection
        if any(w in lower_text for w in ["cyber", "vulnerability", "malware", "phishing", "breach"]):
            domain = "Cybersecurity"
        elif any(w in lower_text for w in ["health", "virus", "hospital", "medical", "disease"]):
            domain = "Public Health"
        elif any(w in lower_text for w in ["flood", "cyclone", "weather", "storm", "earthquake"]):
            domain = "Disaster Management"
        elif any(w in lower_text for w in ["policy", "government", "ministry", "official", "directive"]):
            domain = "Governance"
        else:
            domain = "Operations"

        return {
            "topic": first_line[:120],
            "domain": domain,
            "key_facts": key_facts,
            "entities": filtered_entities,
            "urgency": urgency,
            "constraints": ["Preserve original source facts strictly"],
            "missing_information": [],
        }
