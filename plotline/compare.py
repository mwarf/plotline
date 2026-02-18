"""
plotline.compare - Cross-interview best-take comparison.

Provides cross-interview normalization of delivery scores and comparison
grouping for the best-take comparison report.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from plotline.analyze.scoring import compute_composite_score, normalize_metrics
from plotline.project import read_json


def collect_all_segments(
    project_path: Path,
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Collect all enriched segments from all interviews.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict

    Returns:
        Tuple of (all_segments_list, segments_by_id dict)
    """
    segments_dir = project_path / "data" / "segments"
    all_segments = []
    segments_by_id = {}

    for interview in manifest.get("interviews", []):
        interview_id = interview.get("id", "")
        segments_path = segments_dir / f"{interview_id}.json"

        if not segments_path.exists():
            continue

        segments_data = read_json(segments_path)
        for segment in segments_data.get("segments", []):
            seg_id = segment.get("segment_id", "")
            segment["_interview_id"] = interview_id
            all_segments.append(segment)
            segments_by_id[seg_id] = segment

    return all_segments, segments_by_id


def normalize_scores_cross_interview(
    all_segments: list[dict[str, Any]],
    weights: dict[str, float],
) -> dict[str, float]:
    """Normalize delivery scores across all interviews.

    Computes globally comparable scores by normalizing raw metrics
    across the entire segment pool (not per-interview).

    Args:
        all_segments: All segments from all interviews
        weights: Delivery weights from config

    Returns:
        Dict mapping segment_id to cross_interview_score
    """
    if not all_segments:
        return {}

    raw_metrics = []
    for seg in all_segments:
        delivery = seg.get("delivery", {})
        raw = delivery.get("raw", {})
        if not raw:
            raw = {
                "rms_energy": 0.5,
                "pitch_std_hz": 0.5,
                "speech_rate_wpm": 150,
                "pause_before_sec": 0,
                "pause_after_sec": 0,
                "spectral_centroid_mean": 0.5,
                "zero_crossing_rate": 0.5,
            }
        raw_metrics.append(raw)

    normalized = normalize_metrics(raw_metrics)

    cross_scores = {}
    for i, seg in enumerate(all_segments):
        if i < len(normalized):
            score = compute_composite_score(normalized[i], weights)
            seg_id = seg.get("segment_id", "")
            cross_scores[seg_id] = score

    return cross_scores


def get_delivery_class(score: float) -> str:
    """Get CSS class for delivery score."""
    if score >= 0.7:
        return "filled"
    elif score >= 0.4:
        return "medium"
    return "low"


def build_comparison_groups(
    synthesis: dict[str, Any],
    segments_by_id: dict[str, dict[str, Any]],
    cross_scores: dict[str, float],
    interviews_map: dict[str, dict[str, Any]],
    brief: dict[str, Any] | None = None,
    message_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Build comparison groups from synthesis data.

    Args:
        synthesis: Synthesis data with best_takes and unified_themes
        segments_by_id: All segments indexed by segment_id
        cross_scores: Cross-interview normalized scores
        interviews_map: Interview metadata indexed by interview_id
        brief: Optional creative brief with key_messages
        message_filter: Optional filter to match specific key message

    Returns:
        List of comparison groups, each with topic and candidates
    """
    groups = []
    best_takes = synthesis.get("best_takes", [])
    unified_themes = synthesis.get("unified_themes", [])

    themes_by_topic = {}
    for theme in unified_themes:
        topic_name = theme.get("name", "")
        themes_by_topic[topic_name] = theme

    key_messages = []
    if brief:
        key_messages = brief.get("key_messages", [])

    for take in best_takes:
        topic = take.get("topic", "")
        candidates = take.get("candidates", [])

        if not candidates:
            continue

        theme_data = themes_by_topic.get(topic, {})
        brief_message = None

        for msg in key_messages:
            if topic.lower() in msg.lower() or msg.lower() in topic.lower():
                brief_message = msg
                break

        if message_filter:
            if brief_message and message_filter.lower() not in brief_message.lower():
                continue
            if message_filter.lower() not in topic.lower():
                continue

        enriched_candidates = []
        for candidate in candidates:
            seg_id = candidate.get("segment_id", "")
            segment = segments_by_id.get(seg_id)

            if not segment:
                continue

            interview_id = segment.get("_interview_id", candidate.get("interview_id", ""))
            interview = interviews_map.get(interview_id, {})

            raw_cross_score = cross_scores.get(seg_id)
            fallback_score = candidate.get("composite_score")
            cross_score: float = (
                raw_cross_score
                if raw_cross_score is not None
                else (fallback_score if fallback_score is not None else 0.5)
            )

            start = segment.get("start", 0)
            end = segment.get("end", 0)

            audio_path = None
            if interview.get("audio_full_path"):
                audio_path = f"../{interview['audio_full_path']}#t={max(0, start - 2)}"

            enriched_candidates.append(
                {
                    "segment_id": seg_id,
                    "interview_id": interview_id,
                    "text": segment.get("text", candidate.get("text", "")),
                    "start": start,
                    "end": end,
                    "duration": end - start,
                    "rank": candidate.get("rank", 0),
                    "composite_score": candidate.get("composite_score", 0.5),
                    "cross_score": round(cross_score, 3),
                    "content_alignment": candidate.get("content_alignment"),
                    "conciseness_score": candidate.get("conciseness_score"),
                    "reasoning": candidate.get("reasoning", ""),
                    "delivery_label": segment.get("delivery", {}).get("delivery_label", ""),
                    "delivery_class": get_delivery_class(cross_score),
                    "audio_path": audio_path,
                    "frame_rate": interview.get("frame_rate", 24),
                }
            )

        if enriched_candidates:
            enriched_candidates.sort(key=lambda c: c.get("rank", 999))

            groups.append(
                {
                    "topic": topic,
                    "brief_message": brief_message,
                    "perspectives": theme_data.get("perspectives", ""),
                    "source_theme_count": len(theme_data.get("source_themes", [])),
                    "candidates": enriched_candidates,
                }
            )

    return groups


def run_compare(
    project_path: Path,
    manifest: dict[str, Any],
    config: Any,
    message_filter: str | None = None,
) -> dict[str, Any]:
    """Run comparison analysis and return data for report.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        config: Resolved PlotlineConfig
        message_filter: Optional filter for specific key message

    Returns:
        Dict with comparison groups and metadata
    """
    synthesis_path = project_path / "data" / "synthesis.json"
    if not synthesis_path.exists():
        raise FileNotFoundError("No synthesis found. Run 'plotline synthesize' first.")

    synthesis = read_json(synthesis_path)

    all_segments, segments_by_id = collect_all_segments(project_path, manifest)

    weights = {
        "energy": config.delivery_weights.energy,
        "pitch_variation": config.delivery_weights.pitch_variation,
        "speech_rate": config.delivery_weights.speech_rate,
        "pause_weight": config.delivery_weights.pause_weight,
        "spectral_brightness": config.delivery_weights.spectral_brightness,
        "voice_texture": config.delivery_weights.voice_texture,
    }

    cross_scores = normalize_scores_cross_interview(all_segments, weights)

    interviews_map = {}
    for interview in manifest.get("interviews", []):
        interviews_map[interview["id"]] = interview

    brief = None
    brief_path = project_path / "brief.json"
    if brief_path.exists():
        brief = read_json(brief_path)

    groups = build_comparison_groups(
        synthesis=synthesis,
        segments_by_id=segments_by_id,
        cross_scores=cross_scores,
        interviews_map=interviews_map,
        brief=brief,
        message_filter=message_filter,
    )

    return {
        "project_name": manifest.get("project_name", "Plotline Project"),
        "groups": groups,
        "total_groups": len(groups),
        "total_candidates": sum(len(g["candidates"]) for g in groups),
        "interview_count": len(interviews_map),
        "has_brief": brief is not None,
        "message_filter": message_filter,
    }
