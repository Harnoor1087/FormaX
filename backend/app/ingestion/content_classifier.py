import re
from typing import List, Dict, Any
from pydantic import BaseModel
from ..schemas.request import OutputType, Audience, Tone, Objective

class ContentTypeResult(BaseModel):
    content_type: str
    confidence: float
    domain: str
    recommended_tone: str
    recommended_objective: str
    recommended_audience: str
    suggested_outputs: List[str]
    features_detected: List[str]

# Pattern banks for content classification
CLASSIFIER_PROFILES = [
    {
        "type": "incident_report",
        "domain": "Emergency & Threat Management",
        "keywords": [
            r"\b(?:incident|breach|vulnerability|outage|exploit|malware|alert|advisory|warning|evacuation|fatal|casualt(?:y|ies))\b",
            r"\b(?:cve-\d{4}-\d+|threat\s+actor|dos\s+attack|emergency\s+services?|critical\s+severity)\b"
        ],
        "rec_tone": "urgent",
        "rec_objective": "alert",
        "rec_audience": "government officials",
        "suggested_outputs": ["advisory", "twitter_thread", "executive_summary"]
    },
    {
        "type": "policy_document",
        "domain": "Governance & Legal",
        "keywords": [
            r"\b(?:regulation|statutory|compliance|pursuant\s+to|clause|sub-section|ordinance|amendment|mandatory\s+requirement)\b",
            r"\b(?:terms\s+and\s+conditions|governing\s+law|legal\s+framework|regulatory\s+body)\b"
        ],
        "rec_tone": "formal",
        "rec_objective": "inform",
        "rec_audience": "government officials",
        "suggested_outputs": ["advisory", "executive_summary"]
    },
    {
        "type": "press_release",
        "domain": "Media & Public Relations",
        "keywords": [
            r"\b(?:for\s+immediate\s+release|press\s+release|media\s+contact|spokesperson\s+stated|pleased\s+to\s+announce|unveils?|launches?)\b"
        ],
        "rec_tone": "persuasive",
        "rec_objective": "inform",
        "rec_audience": "media",
        "suggested_outputs": ["linkedin_post", "twitter_thread"]
    },
    {
        "type": "executive_brief",
        "domain": "Strategic Leadership",
        "keywords": [
            r"\b(?:quarterly\s+results?|fiscal\s+year|revenue|ebitda|strategic\s+priorities|kpi|roi|board\s+of\s+directors|market\s+share)\b"
        ],
        "rec_tone": "formal",
        "rec_objective": "summarise",
        "rec_audience": "leadership",
        "suggested_outputs": ["executive_summary", "presentation"]
    },
]

def classify_content_type(text: str, is_transcript_hint: bool = False) -> ContentTypeResult:
    """
    Lightweight, deterministic content classifier and format recommendation engine (Synopsis Section 4).
    """
    if is_transcript_hint or ("\nSpeaker" in text and ":" in text):
        return ContentTypeResult(
            content_type="meeting_transcript",
            confidence=0.90,
            domain="Operations & Discussion",
            recommended_tone="neutral",
            recommended_objective="summarise",
            recommended_audience="leadership",
            suggested_outputs=["executive_summary", "presentation"],
            features_detected=["dialogue_turns_found", "multiple_speakers"]
        )

    lower_text = text.lower()
    best_match = None
    highest_score = 0
    matched_features: List[str] = []

    for profile in CLASSIFIER_PROFILES:
        score = 0
        current_features = []
        for kw_pattern in profile["keywords"]:
            matches = re.findall(kw_pattern, lower_text)
            if matches:
                score += len(matches)
                current_features.append(f"{profile['type']}_matches({len(matches)})")

        if score > highest_score:
            highest_score = score
            best_match = profile
            matched_features = current_features

    if best_match and highest_score >= 2:
        confidence = min(0.60 + (highest_score * 0.05), 0.95)
        return ContentTypeResult(
            content_type=best_match["type"],
            confidence=round(confidence, 2),
            domain=best_match["domain"],
            recommended_tone=best_match["rec_tone"],
            recommended_objective=best_match["rec_objective"],
            recommended_audience=best_match["rec_audience"],
            suggested_outputs=best_match["suggested_outputs"],
            features_detected=matched_features,
        )

    # General default fallback
    return ContentTypeResult(
        content_type="general_report",
        confidence=0.50,
        domain="General Operations",
        recommended_tone="formal",
        recommended_objective="inform",
        recommended_audience="general public",
        suggested_outputs=["advisory", "executive_summary"],
        features_detected=["baseline_prose"],
    )
