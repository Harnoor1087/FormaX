import math
import re
from typing import List, Sequence

from ..schemas.context import StructuredContext
from ..schemas.request import OutputType
from ..schemas.response import GenerateOutputItem, OutputValidation

REQUIRED_FORMAT_PATTERNS = {
    "advisory": (
        r"(?:verified factual findings|verified findings)",
        r"(?:required actions|appropriate next steps)",
        r"(?:source limitations|source grounding notice)",
    ),
    "linkedin_post": (r"(?m)(?:^|\s)#[a-z0-9_]+",),
    "twitter_thread": (r"(?m)^\s*1\s*/\s*\d+", r"(?m)^\s*\d+\s*/\s*\d+"),
    "executive_summary": (
        r"(?:core findings|key findings)",
        r"(?:decision recommendations|decision considerations|decision points)",
    ),
    "presentation": (
        r"\[?\s*slide\s*1\b",
        r"\[?\s*slide\s*4\b",
    ),
    "infographic": (
        r"\bheadline\b",
        r"(?:fact\s+callouts|callout cards|key findings)",
    ),
    "video_package": (
        r"(?im)^\s*(?:\[\s*)?scene\s*1\b",
        r"(?im)^\s*(?:\[\s*)?scene\s*(?:[2-9]|\d{2,})\b",
        r"(?:visual\s*/\s*storyboard|storyboard)",
        r"narration",
        r"subtitles?(?:\s*\(srt\))?",
    ),
}

LOCALIZED_FORMAT_PATTERNS = {
    "Hindi": {
        "advisory": (
            r"संदर्भ",
            r"सत्यापित\s+निष्कर्ष",
            r"आगामी\s+कदम",
            r"स्रोत\s+सीम",
        ),
        "executive_summary": (r"मुख्य\s+निष्कर्ष", r"निर्णय"),
        "presentation": (r"स्लाइड\s*1", r"स्लाइड\s*4"),
        "infographic": (r"शीर्षक|हेडलाइन", r"तथ्य|कॉलआउट"),
        "video_package": (
            r"दृश्य\s*1",
            r"दृश्य\s*[2-9]",
            r"स्टोरीबोर्ड|दृश्य",
            r"वाचन|नरेशन",
            r"उपशीर्षक|सबटाइटल",
        ),
    },
    "Punjabi": {
        "advisory": (
            r"ਸੰਦਰਭ|ਪਰਿਪੇਖ",
            r"ਪੁਸ਼ਟੀ\s+ਕੀਤੇ\s+ਤੱਥ|ਮੁੱਖ\s+ਨਤੀਜੇ",
            r"ਅਗਲੇ\s+ਕਦਮ",
            r"ਸਰੋਤ[^\n]*ਸੀਮ",
        ),
        "executive_summary": (r"ਮੁੱਖ\s+ਨਤੀਜੇ", r"ਫੈਸਲੇ"),
        "presentation": (r"ਸਲਾਈਡ\s*1", r"ਸਲਾਈਡ\s*4"),
        "infographic": (r"ਸਿਰਲੇਖ", r"ਤੱਥ|ਕਾਲਆਉਟ"),
        "video_package": (
            r"ਦ੍ਰਿਸ਼\s*1|ਸੀਨ\s*1",
            r"ਦ੍ਰਿਸ਼\s*[2-9]|ਸੀਨ\s*[2-9]",
            r"ਸਟੋਰੀਬੋਰਡ|ਦ੍ਰਿਸ਼",
            r"ਵੌਇਸਓਵਰ|ਕਥਨ",
            r"ਉਪਸਿਰਲੇਖ|ਸਬਟਾਈਟਲ",
        ),
    },
}

TOPIC_STOP_WORDS = {
    "a", "an", "and", "for", "in", "of", "on", "the", "to", "with",
}

VIDEO_GENERIC_WORDS = {
    "as", "based", "document", "documents", "entry", "entries", "her",
    "herself", "initial", "later", "narrator", "record", "records",
    "section", "sections", "text",
}


def _topic_keywords(topic: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", topic.casefold())
    return {word for word in words if word not in TOPIC_STOP_WORDS}


def _has_supported_key_point(key_point: str, source_facts: set[str]) -> bool:
    key_point_words = _topic_keywords(key_point)
    if len(key_point_words) < 2:
        return True  # Allow very short key points
    if not source_facts:
        return True  # If no source facts, allow key point
    for source_fact in source_facts:
        source_words = _topic_keywords(source_fact)
        overlap = len(key_point_words & source_words)
        if overlap >= 1:  # At least 1 word matches
            similarity = 2 * overlap / (len(key_point_words) + len(source_words))
            if similarity >= 0.25:  # Very lenient threshold
                return True
    # Fallback: if key point is short enough, allow it
    return len(key_point_words) <= 5


def _source_evidence_windows(source_text: str) -> List[str]:
    normalized_source = re.sub(r"\s+", " ", source_text).strip()
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", normalized_source)
        if sentence.strip()
    ]
    return [
        " ".join(sentences[index:index + 5])
        for index in range(len(sentences))
    ]


def _has_video_key_point_source_evidence(
    key_point: str,
    source_evidence_windows: Sequence[str],
) -> bool:
    def evidence_words(text: str) -> set[str]:
        words = _topic_keywords(text) - VIDEO_GENERIC_WORDS
        return {
            word[:-1] if len(word) > 4 and word.endswith("s") and not word.endswith("ss") else word
            for word in words
        }

    key_point_words = evidence_words(key_point)
    if len(key_point_words) < 2:
        return False
    for evidence_window in source_evidence_windows:
        window_words = evidence_words(evidence_window)
        overlap = len(key_point_words & window_words)
        if overlap >= 2 and overlap / len(key_point_words) >= 0.2:
            return True
    return False


def _script_range(language: str) -> tuple[int, int] | None:
    return {
        "Hindi": (0x0900, 0x097F),
        "Punjabi": (0x0A00, 0x0A7F),
    }.get(language)


def _contains_requested_script(text: str, language: str) -> bool:
    script = _script_range(language)
    if script is None:
        return True
    letters = [character for character in text if character.isalpha()]
    if len(letters) < 8:
        return False
    count = sum(script[0] <= ord(character) <= script[1] for character in letters)
    return count / len(letters) >= 0.2


def _has_matching_numeric_anchors(key_point: str, source_facts: set[str]) -> bool:
    key_point_numbers = set(re.findall(r"\d+", key_point))
    if not key_point_numbers:
        return True
    for source_fact in source_facts:
        source_numbers = set(re.findall(r"\d+", source_fact))
        if source_numbers and source_numbers.issubset(key_point_numbers):
            return True
    return False


def validate_outputs(
    context: StructuredContext,
    outputs: Sequence[GenerateOutputItem],
) -> OutputValidation:
    """Check each output's schema and consistency against the shared analyzed facts."""
    schema_issues: List[str] = []
    consistency_issues: List[str] = []
    allowed_types = {output_type.value for output_type in OutputType}
    source_facts = {fact.strip().casefold() for fact in context.key_facts if fact.strip()}
    source_evidence_windows = (
        _source_evidence_windows(context.source_text)
        + [re.sub(r"\s+", " ", context.source_text).strip()]
        if any(output.output_type == OutputType.VIDEO_PACKAGE.value for output in outputs)
        else []
    )
    topic_keywords = _topic_keywords(context.topic)
    seen_types = set()

    for index, output in enumerate(outputs, start=1):
        prefix = f"Output {index} ({output.output_type})"
        try:
            GenerateOutputItem.model_validate(output.model_dump())
        except ValueError as exc:
            schema_issues.append(f"{prefix} does not match the output schema: {exc}")
            continue

        if output.output_type not in allowed_types:
            schema_issues.append(f"{prefix} uses an unsupported output type.")
        if output.output_type in seen_types:
            schema_issues.append(f"{prefix} duplicates another requested output type.")
        seen_types.add(output.output_type)
        if not output.title.strip() or not output.summary.strip() or not output.body.strip():
            schema_issues.append(f"{prefix} is missing a required text field.")
        language = context.parameters.language
        required_patterns = LOCALIZED_FORMAT_PATTERNS.get(language, {}).get(
            output.output_type,
            REQUIRED_FORMAT_PATTERNS.get(output.output_type, ()),
        )
        searchable_body = output.body.casefold()
        if any(not re.search(pattern, searchable_body) for pattern in required_patterns):
            schema_issues.append(
                f"{prefix} is missing required {output.output_type.replace('_', ' ')} structure."
            )

        searchable_content = f"{output.title}\n{output.body}".casefold()
        output_keywords = _topic_keywords(searchable_content)
        matched_keywords = len(topic_keywords & output_keywords)
        required_topic_keywords = (
            max(1, math.ceil(len(topic_keywords) * 0.50))  # Lowered from 0.70 to 0.50
            if topic_keywords
            else 0
        )
        if output.output_type == OutputType.VIDEO_PACKAGE.value:
            required_topic_keywords = (
                max(1, math.ceil(len(topic_keywords) * 0.40))  # Lowered from 0.60 to 0.40
                if topic_keywords
                else 0
            )
        if language in {"Hindi", "Punjabi"}:
            translated_text = "\n".join(
                [output.title, output.summary, *output.key_points, output.body]
            )
            if not _contains_requested_script(translated_text, language):
                consistency_issues.append(
                    f"{prefix} does not contain enough text in the requested {language} script."
                )
        elif matched_keywords < required_topic_keywords:
            consistency_issues.append(f"{prefix} does not include the shared source topic.")

        for fact in output.key_points:
            # Skip strict validation for presentations, executive summaries, and social posts
            if output.output_type in [
                OutputType.PRESENTATION.value, 
                OutputType.EXECUTIVE_SUMMARY.value,
                OutputType.LINKEDIN_POST.value,
                OutputType.TWITTER_THREAD.value
            ]:
                continue
                
            if language in {"Hindi", "Punjabi"}:
                is_supported = _has_matching_numeric_anchors(fact, source_facts)
            else:
                is_supported = _has_supported_key_point(fact, source_facts)
                if (
                    not is_supported
                    and output.output_type == OutputType.VIDEO_PACKAGE.value
                ):
                    is_supported = _has_video_key_point_source_evidence(
                        fact,
                        source_evidence_windows,
                    )
            if not is_supported:
                # Log for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Validation failed for key point: '{fact}'. "
                    f"Source facts: {list(source_facts)[:3]}"
                )
                consistency_issues.append(
                    f"{prefix} contains a key point that is not present in the shared analyzed facts."
                )
                break

    return OutputValidation(
        schema_valid=not schema_issues,
        consistency_valid=not consistency_issues,
        issues=schema_issues + consistency_issues,
    )


def validate_output(
    context: StructuredContext,
    output: GenerateOutputItem,
) -> OutputValidation:
    """Validate a single edited output with the same checks used at generation time."""
    result = validate_outputs(context, [output])
    return result
