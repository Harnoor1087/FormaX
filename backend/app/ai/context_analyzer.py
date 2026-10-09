from typing import Optional
from .prompt_builder import build_context_analysis_prompt
from .model_client import ModelClient
from ..schemas.context import ExtractedContext

class ContextAnalyzer:
    """
    Analyzes normalized source content to extract grounded topic, domain,
    facts, entities, and urgency (Section 3.3).
    """

    def __init__(self, model_client: Optional[ModelClient] = None):
        self.model_client = model_client or ModelClient()

    def analyze(self, normalized_text: str) -> ExtractedContext:
        """
        Executes intent & context analysis and validates output into Pydantic schema.
        """
        prompt = build_context_analysis_prompt(normalized_text)
        raw_data = self.model_client.generate_json(prompt, source_text_hint=normalized_text)
        
        # Validate against ExtractedContext Pydantic schema
        try:
            return ExtractedContext(
                topic=raw_data.get("topic", "General Analysis"),
                domain=raw_data.get("domain", "General"),
                key_facts=raw_data.get("key_facts", []),
                entities=raw_data.get("entities", []),
                urgency=raw_data.get("urgency", "medium"),
                constraints=raw_data.get("constraints", []),
                missing_information=raw_data.get("missing_information", []),
            )
        except Exception as e:
            # Fallback if raw_data was malformed
            return ExtractedContext(
                topic=normalized_text[:100],
                domain="General",
                key_facts=[normalized_text[:200]],
                entities=[],
                urgency="medium",
                constraints=["Preserve source claims"],
                missing_information=["Model response required formatting normalization"],
            )
