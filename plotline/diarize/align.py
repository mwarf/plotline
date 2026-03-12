"""
plotline.diarize.align - Align diarization results with transcript words.

Maps pyannote speaker segments to Whisper word-level timestamps.
"""

from __future__ import annotations

from typing import Any

# Words in a gap larger than this (seconds) from any speaker segment are left
# unassigned rather than speculatively attributed to the nearest speaker.
MAX_GAP_SECONDS = 3.0


def find_speaker_for_time(
    time: float,
    diarization_segments: list[dict[str, Any]],
) -> str | None:
    """Find the speaker for a given timestamp.

    When multiple speaker segments contain the timestamp (overlapping speech),
    picks the speaker whose segment encloses the point most deeply — i.e. the
    segment for which the point is furthest from either edge.  Ties are broken
    by preferring the longer segment, which is more likely to be the primary
    speaker at that moment.

    Args:
        time: Timestamp in seconds
        diarization_segments: List of diarization segments with start, end, speaker

    Returns:
        Speaker ID or None if no segment contains the time
    """
    best_speaker = None
    best_depth = -1.0  # distance from point to nearest segment edge
    best_duration = -1.0  # tiebreaker: longer segment wins

    for seg in diarization_segments:
        start = seg["start"]
        end = seg["end"]

        if start <= time <= end:
            # How deeply inside the segment is the point?
            depth = min(time - start, end - time)
            duration = end - start

            if depth > best_depth or (depth == best_depth and duration > best_duration):
                best_depth = depth
                best_duration = duration
                best_speaker = seg["speaker"]

    return best_speaker


def find_speaker_for_interval(
    word_start: float,
    word_end: float,
    diarization_segments: list[dict[str, Any]],
) -> str | None:
    """Find the dominant speaker for a word interval.

    Computes the actual overlap duration between the word's time interval and
    each speaker segment, then returns the speaker with the greatest overlap.
    This handles words that span a speaker transition more accurately than a
    single midpoint lookup.

    When overlaps are equal (e.g. perfectly symmetric transitions or identical
    overlapping-speech segments), the longer diarization segment wins as a
    tiebreaker.

    Args:
        word_start: Word start time in seconds
        word_end: Word end time in seconds
        diarization_segments: List of diarization segments with start, end, speaker

    Returns:
        Speaker ID or None if no segment overlaps the word interval
    """
    best_speaker = None
    best_overlap = 0.0
    best_duration = -1.0

    for seg in diarization_segments:
        seg_start = seg["start"]
        seg_end = seg["end"]

        # Overlap of [word_start, word_end] with [seg_start, seg_end]
        overlap = max(0.0, min(word_end, seg_end) - max(word_start, seg_start))
        if overlap <= 0.0:
            continue

        duration = seg_end - seg_start
        if overlap > best_overlap or (overlap == best_overlap and duration > best_duration):
            best_overlap = overlap
            best_duration = duration
            best_speaker = seg["speaker"]

    return best_speaker


def assign_speakers_to_words(
    words: list[dict[str, Any]],
    diarization_segments: list[dict[str, Any]],
    max_gap_seconds: float = MAX_GAP_SECONDS,
) -> list[dict[str, Any]]:
    """Assign speaker labels to words based on diarization.

    For each word, computes the actual overlap between the word's time interval
    and every diarization segment, assigning the speaker with the greatest
    overlap.  This is more accurate than a midpoint-only lookup for words that
    span a speaker boundary.

    Words that fall entirely outside any diarization segment (gaps) are assigned
    to the nearest speaker only if the gap is smaller than *max_gap_seconds*.
    Words in longer gaps are left with speaker=None so that downstream code can
    treat them appropriately rather than making a speculative attribution.

    Args:
        words: List of word dicts with start, end timestamps
        diarization_segments: List of diarization segments
        max_gap_seconds: Maximum distance (seconds) to nearest segment for gap
            fallback.  Words further than this receive speaker=None.

    Returns:
        Words with speaker field added (may be None for words in long gaps)
    """
    if not diarization_segments:
        return words

    updated_words = []
    for word in words:
        word_copy = word.copy()
        word_start = word.get("start", 0)
        word_end = word.get("end", 0)

        # Fix 4: use full interval overlap instead of midpoint-only lookup
        speaker = find_speaker_for_interval(word_start, word_end, diarization_segments)

        if speaker is None:
            # Fix 2: gap fallback with max-distance guard
            mid_time = (word_start + word_end) / 2
            min_dist = float("inf")
            nearest_speaker = None
            for seg in diarization_segments:
                dist_to_start = abs(mid_time - seg["start"])
                dist_to_end = abs(mid_time - seg["end"])
                dist = min(dist_to_start, dist_to_end)
                if dist < min_dist:
                    min_dist = dist
                    nearest_speaker = seg["speaker"]

            # Only use the fallback if the word is close enough to a segment
            if min_dist <= max_gap_seconds:
                speaker = nearest_speaker
            # else: speaker stays None — word is in a long gap

        word_copy["speaker"] = speaker
        updated_words.append(word_copy)

    return updated_words


def compute_segment_speaker(
    words: list[dict[str, Any]],
) -> str | None:
    """Compute the primary speaker for a segment.

    Uses duration-weighted voting: each word contributes its spoken duration
    (end - start) rather than a flat count of 1.  This prevents short
    back-channel words ("yeah", "uh-huh") from unfairly swinging the result
    when the segment is dominated by a different speaker's longer utterances.

    Args:
        words: List of words with speaker and start/end fields

    Returns:
        Speaker with the most total spoken time, or None if no words have speakers
    """
    if not words:
        return None

    # Fix 1: accumulate spoken duration per speaker instead of word count
    speaker_durations: dict[str, float] = {}
    for word in words:
        speaker = word.get("speaker")
        if speaker:
            duration = word.get("end", 0) - word.get("start", 0)
            speaker_durations[speaker] = speaker_durations.get(speaker, 0.0) + max(duration, 0.0)

    if not speaker_durations:
        return None

    best, _ = max(speaker_durations.items(), key=lambda kv: kv[1])
    return best


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
