"""
plotline.diarize.align - Align diarization results with transcript words.

Maps pyannote speaker segments to Whisper word-level timestamps.
"""

from __future__ import annotations

from typing import Any


def find_speaker_for_time(
    time: float,
    diarization_segments: list[dict[str, Any]],
) -> str | None:
    """Find the speaker for a given timestamp.

    Uses longest overlap if multiple speakers overlap the time.

    Args:
        time: Timestamp in seconds
        diarization_segments: List of diarization segments with start, end, speaker

    Returns:
        Speaker ID or None if no segment contains the time
    """
    best_speaker = None
    best_overlap = 0.0

    for seg in diarization_segments:
        start = seg["start"]
        end = seg["end"]

        if start <= time <= end:
            overlap = min(time - start, end - time)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = seg["speaker"]

    return best_speaker


def assign_speakers_to_words(
    words: list[dict[str, Any]],
    diarization_segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Assign speaker labels to words based on diarization.

    For each word, finds the speaker at the word's midpoint.
    Handles edge cases:
    - Words in gaps between speaker segments: assigned to nearest speaker
    - Words spanning multiple speakers: assigned to speaker at midpoint

    Args:
        words: List of word dicts with start, end timestamps
        diarization_segments: List of diarization segments

    Returns:
        Words with speaker field added
    """
    if not diarization_segments:
        return words

    updated_words = []
    for word in words:
        word_copy = word.copy()
        start = word.get("start", 0)
        end = word.get("end", 0)

        mid_time = (start + end) / 2

        speaker = find_speaker_for_time(mid_time, diarization_segments)

        if speaker is None:
            min_dist = float("inf")
            nearest_speaker = None
            for seg in diarization_segments:
                dist_to_start = abs(mid_time - seg["start"])
                dist_to_end = abs(mid_time - seg["end"])
                dist = min(dist_to_start, dist_to_end)
                if dist < min_dist:
                    min_dist = dist
                    nearest_speaker = seg["speaker"]
            speaker = nearest_speaker

        word_copy["speaker"] = speaker
        updated_words.append(word_copy)

    return updated_words


def compute_segment_speaker(
    words: list[dict[str, Any]],
) -> str | None:
    """Compute the primary speaker for a segment.

    Uses majority vote based on word count per speaker.

    Args:
        words: List of words with speaker field

    Returns:
        Most common speaker, or None if no words have speakers
    """
    if not words:
        return None

    speaker_counts: dict[str, int] = {}
    for word in words:
        speaker = word.get("speaker")
        if speaker:
            speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1

    if not speaker_counts:
        return None

    return max(speaker_counts, key=speaker_counts.get)


def assign_speakers_to_transcript(
    transcript: dict[str, Any],
    diarization: dict[str, Any],
) -> dict[str, Any]:
    """Assign speakers to all segments and words in a transcript.

    Args:
        transcript: Transcript dict with segments
        diarization: Diarization result with segments

    Returns:
        Updated transcript with speaker fields on segments and words
    """
    diarization_segments = diarization.get("segments", [])

    updated_segments = []
    for segment in transcript.get("segments", []):
        segment_copy = segment.copy()

        words = segment.get("words", [])
        updated_words = assign_speakers_to_words(words, diarization_segments)
        segment_copy["words"] = updated_words

        segment_speaker = compute_segment_speaker(updated_words)
        segment_copy["speaker"] = segment_speaker

        updated_segments.append(segment_copy)

    result = transcript.copy()
    result["segments"] = updated_segments
    result["diarized_at"] = diarization.get("diarized_at")
    result["diarization_model"] = diarization.get("model")
    result["num_speakers"] = diarization.get("num_speakers_detected")

    return result
