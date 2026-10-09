import re
from typing import List, Dict, Any, Tuple

TIMESTAMP_PATTERN = re.compile(
    r"(?:\[?\b\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?\b(?:\s*-->\s*\b\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?\b)?\]?)"
)
SPEAKER_PATTERN = re.compile(
    r"(?i)(?:^|\n)\s*([A-Za-z0-9_\-\s]{2,25})\s*:\s*"
)
FILLER_WORDS_PATTERN = re.compile(
    r"(?i)\b(?:uh|um|er|ah|you know)\b[\s,]*"
)

def clean_transcript(text: str, remove_timestamps: bool = True, strip_fillers: bool = True) -> str:
    """
    Normalizes automated speech-to-text transcripts (Whisper outputs):
    - Strips or standardizes timestamp markers
    - Cleans disfluencies (uh, um, etc.)
    - Unifies broken line-breaks within speech segments
    """
    if not text:
        return ""

    cleaned = text
    if remove_timestamps:
        cleaned = TIMESTAMP_PATTERN.sub("", cleaned)

    if strip_fillers:
        cleaned = FILLER_WORDS_PATTERN.sub("", cleaned)

    # Normalize whitespace
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()

def parse_speaker_segments(text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extracts speaker dialogue turns and summarizes transcript dialogue structure.
    Returns:
        Tuple of (formatted_dialogue_text: str, transcript_metadata: Dict[str, Any])
    """
    cleaned = clean_transcript(text, remove_timestamps=True, strip_fillers=True)
    
    # Split by speaker tags
    lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
    speaker_turns: List[Dict[str, str]] = []
    current_speaker = "Speaker"
    current_utterance: List[str] = []
    unique_speakers = set()

    for line in lines:
        match = re.match(r"^([A-Za-z0-9_\-\s]{2,25}):\s*(.*)$", line)
        if match:
            if current_utterance:
                speaker_turns.append({
                    "speaker": current_speaker,
                    "text": " ".join(current_utterance)
                })
                current_utterance = []
            current_speaker = match.group(1).strip()
            unique_speakers.add(current_speaker)
            if match.group(2):
                current_utterance.append(match.group(2).strip())
        else:
            current_utterance.append(line)

    if current_utterance:
        speaker_turns.append({
            "speaker": current_speaker,
            "text": " ".join(current_utterance)
        })
        unique_speakers.add(current_speaker)

    # Reconstruct clean speaker-annotated dialogue
    formatted_dialogue = "\n\n".join(
        [f"{turn['speaker']}: {turn['text']}" for turn in speaker_turns]
    )

    metadata = {
        "is_transcript": len(speaker_turns) > 1 or len(unique_speakers) > 1,
        "speakers_identified": list(unique_speakers),
        "total_dialogue_turns": len(speaker_turns),
    }

    return formatted_dialogue if formatted_dialogue else cleaned, metadata
