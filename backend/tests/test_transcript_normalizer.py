from app.ingestion.transcript_normalizer import clean_transcript, parse_speaker_segments

def test_clean_transcript_strips_timestamps_and_fillers():
    raw_whisper = (
        "[00:00:05.100 --> 00:00:08.500] Speaker 1: We uh observed significant packet loss.\n"
        "[00:00:09.000 --> 00:00:12.300] Speaker 2: Yes, um, the core router restarted."
    )
    cleaned = clean_transcript(raw_whisper)
    assert "[00:00:05.100" not in cleaned
    assert "-->" not in cleaned
    assert " uh " not in cleaned
    assert " um " not in cleaned
    assert "packet loss" in cleaned
    assert "core router restarted" in cleaned

def test_parse_speaker_segments_extracts_turns():
    transcript = (
        "Alice: We are ready to begin the briefing.\n"
        "Bob: Systems in region east are stable.\n"
        "Alice: Excellent, let us prepare the advisory."
    )
    formatted, meta = parse_speaker_segments(transcript)
    assert meta["is_transcript"] is True
    assert "Alice" in meta["speakers_identified"]
    assert "Bob" in meta["speakers_identified"]
    assert meta["total_dialogue_turns"] == 3
    assert "Alice: We are ready to begin the briefing." in formatted
