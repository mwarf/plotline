"""
plotline.reports.coverage - Coverage matrix report.

Visualizes how creative brief key messages are covered across selected segments.
Identifies coverage gaps and provides per-message analysis.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from plotline.export.timecode import seconds_to_timecode
from plotline.project import read_json
from plotline.reports.generator import ReportGenerator
from plotline.utils import format_duration, get_delivery_class


def build_theme_alignment_map(
    synthesis_data: dict[str, Any] | None,
) -> dict[str, list[str]]:
    """Build mapping from message ID to unified theme IDs.

    Args:
        synthesis_data: Synthesis data with unified_themes

    Returns:
        Dict mapping message_id -> list of unified_theme_ids
    """
    if not synthesis_data:
        return {}

    alignment_map: dict[str, list[str]] = {}

    for theme in synthesis_data.get("unified_themes", []):
        brief_alignment = theme.get("brief_alignment")
        if brief_alignment:
            if brief_alignment not in alignment_map:
                alignment_map[brief_alignment] = []
            alignment_map[brief_alignment].append(theme.get("unified_theme_id", ""))

    return alignment_map


def build_theme_to_segments_map(
    synthesis_data: dict[str, Any] | None,
) -> dict[str, list[str]]:
    """Build mapping from unified theme ID to segment IDs.

    Args:
        synthesis_data: Synthesis data with unified_themes

    Returns:
        Dict mapping unified_theme_id -> list of segment_ids
    """
    if not synthesis_data:
        return {}

    theme_segments: dict[str, list[str]] = {}

    for theme in synthesis_data.get("unified_themes", []):
        theme_id = theme.get("unified_theme_id", "")
        segment_ids = theme.get("all_segment_ids", [])
        if theme_id and segment_ids:
            theme_segments[theme_id] = segment_ids

    return theme_segments


def analyze_coverage(
    brief_data: dict[str, Any],
    selections_data: dict[str, Any],
    synthesis_data: dict[str, Any] | None,
    arc_data: dict[str, Any] | None,
    interviews_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Analyze coverage of key messages across selections.

    Args:
        brief_data: Parsed brief with key_messages
        selections_data: Selections with segments
        synthesis_data: Optional synthesis for theme alignments
        arc_data: Optional arc for coverage_gaps
        interviews_map: Interview metadata by ID

    Returns:
        Dict with coverage analysis results
    """
    key_messages = brief_data.get("key_messages", [])
    segments = selections_data.get("segments", [])

    theme_alignment_map = build_theme_alignment_map(synthesis_data)
    theme_to_segments = build_theme_to_segments_map(synthesis_data)

    segment_by_id = {s.get("segment_id"): s for s in segments}

    messages_data = []
    matrix_columns = []

    for seg in segments:
        seg_id = seg.get("segment_id", "")
        interview_id = seg.get("interview_id", "")
        interview = interviews_map.get(interview_id, {})
        fps = interview.get("frame_rate", 24)

        start = seg.get("start", 0)
        end = seg.get("end", 0)

        matrix_columns.append(
            {
                "segment_id": seg_id,
                "position": seg.get("position", 0),
                "interview_id": interview_id,
                "timecode": seconds_to_timecode(start, fps),
                "duration": format_duration(end - start),
                "delivery_score": seg.get("composite_score", 0),
            }
        )

    for msg in key_messages:
        msg_id = msg.get("id", "")
        msg_text = msg.get("text", "")

        strong_segments = []
        weak_segments = []

        for seg in segments:
            seg_id = seg.get("segment_id", "")
            brief_message = seg.get("brief_message")

            if brief_message == msg_id:
                interview_id = seg.get("interview_id", "")
                interview = interviews_map.get(interview_id, {})
                fps = interview.get("frame_rate", 24)
                start = seg.get("start", 0)
                end = seg.get("end", 0)

                strong_segments.append(
                    {
                        "segment_id": seg_id,
                        "position": seg.get("position", 0),
                        "interview_id": interview_id,
                        "text": seg.get("text", "")[:100],
                        "timecode": seconds_to_timecode(start, fps),
                        "delivery_score": seg.get("composite_score", 0),
                        "delivery_class": get_delivery_class(seg.get("composite_score", 0)),
                        "audio_path": (
                            f"../{interview['audio_full_path']}#t={max(0, start - 2)}"
                            if interview.get("audio_full_path")
                            else None
                        ),
                    }
                )

        aligned_theme_ids = theme_alignment_map.get(msg_id, [])
        for theme_id in aligned_theme_ids:
            theme_segment_ids = theme_to_segments.get(theme_id, [])
            for theme_seg_id in theme_segment_ids:
                if theme_seg_id in segment_by_id:
                    seg = segment_by_id[theme_seg_id]
                    if not any(s["segment_id"] == theme_seg_id for s in strong_segments):
                        if not any(s["segment_id"] == theme_seg_id for s in weak_segments):
                            interview_id = seg.get("interview_id", "")
                            interview = interviews_map.get(interview_id, {})
                            fps = interview.get("frame_rate", 24)
                            start = seg.get("start", 0)
                            end = seg.get("end", 0)

                            weak_segments.append(
                                {
                                    "segment_id": theme_seg_id,
                                    "position": seg.get("position", 0),
                                    "interview_id": interview_id,
                                    "text": seg.get("text", "")[:100],
                                    "timecode": seconds_to_timecode(start, fps),
                                    "delivery_score": seg.get("composite_score", 0),
                                    "delivery_class": get_delivery_class(
                                        seg.get("composite_score", 0)
                                    ),
                                    "themes": seg.get("themes", []),
                                }
                            )

        strong_segments.sort(key=lambda s: s.get("delivery_score", 0), reverse=True)
        weak_segments.sort(key=lambda s: s.get("delivery_score", 0), reverse=True)

        if strong_segments:
            coverage_level = "strong"
            best_segment = strong_segments[0]
        elif weak_segments:
            coverage_level = "weak"
            best_segment = weak_segments[0]
        else:
            coverage_level = "gap"
            best_segment = None

        messages_data.append(
            {
                "id": msg_id,
                "text": msg_text,
                "coverage_level": coverage_level,
                "strong_segments": strong_segments,
                "weak_segments": weak_segments,
                "strong_count": len(strong_segments),
                "weak_count": len(weak_segments),
                "total_count": len(strong_segments) + len(weak_segments),
                "best_segment": best_segment,
                "aligned_themes": aligned_theme_ids,
            }
        )

    matrix_rows = []
    for msg_data in messages_data:
        row_cells = []
        msg_id = msg_data["id"]

        for col in matrix_columns:
            seg_id = col["segment_id"]
            seg = segment_by_id.get(seg_id, {})

            if seg.get("brief_message") == msg_id:
                cell_value = "strong"
            elif msg_id in msg_data.get("aligned_themes", []):
                seg_themes = seg.get("themes", [])
                aligned_themes = msg_data.get("aligned_themes", [])
                if any(t in aligned_themes for t in seg_themes):
                    cell_value = "weak"
                else:
                    cell_value = "none"
            else:
                cell_value = "none"

            row_cells.append(
                {
                    "segment_id": seg_id,
                    "value": cell_value,
                }
            )

        matrix_rows.append(
            {
                "message_id": msg_id,
                "message_text": msg_data["text"],
                "cells": row_cells,
            }
        )

    strong_count = sum(1 for m in messages_data if m["coverage_level"] == "strong")
    weak_count = sum(1 for m in messages_data if m["coverage_level"] == "weak")
    gap_count = sum(1 for m in messages_data if m["coverage_level"] == "gap")
    total_messages = len(messages_data)

    coverage_percent = (
        ((strong_count + weak_count) / total_messages * 100) if total_messages > 0 else 0
    )

    coverage_gaps = []
    if arc_data:
        coverage_gaps = arc_data.get("coverage_gaps", [])

    must_include_status = []
    must_include = brief_data.get("must_include_topics", [])
    for topic in must_include:
        found = False
        if synthesis_data:
            for theme in synthesis_data.get("unified_themes", []):
                if topic.lower() in theme.get("name", "").lower():
                    found = True
                    break
        must_include_status.append(
            {
                "topic": topic,
                "covered": found,
            }
        )

    return {
        "messages": messages_data,
        "matrix_rows": matrix_rows,
        "matrix_columns": matrix_columns,
        "total_messages": total_messages,
        "strong_count": strong_count,
        "weak_count": weak_count,
        "gap_count": gap_count,
        "coverage_percent": round(coverage_percent, 1),
        "coverage_gaps": coverage_gaps,
        "must_include_status": must_include_status,
    }


def generate_coverage(
    project_path: Path,
    manifest: dict[str, Any],
    output_path: Path | None = None,
    open_browser: bool = False,
) -> Path:
    """Generate the coverage matrix report.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        output_path: Optional output path
        open_browser: Whether to open in browser

    Returns:
        Path to generated report
    """
    if output_path is None:
        output_path = project_path / "reports" / "coverage.html"

    brief_path = project_path / "brief.json"
    if not brief_path.exists():
        raise FileNotFoundError("No brief attached. Use 'plotline brief <file>' to attach one.")

    selections_path = project_path / "data" / "selections.json"
    if not selections_path.exists():
        raise FileNotFoundError("No selections found. Run 'plotline arc' first.")

    brief_data = read_json(brief_path)
    selections_data = read_json(selections_path)

    synthesis_path = project_path / "data" / "synthesis.json"
    synthesis_data = None
    if synthesis_path.exists():
        synthesis_data = read_json(synthesis_path)

    arc_path = project_path / "data" / "arc.json"
    arc_data = None
    if arc_path.exists():
        arc_data = read_json(arc_path)

    interviews_map = {}
    for interview in manifest.get("interviews", []):
        interviews_map[interview.get("id", "")] = interview

    coverage_data = analyze_coverage(
        brief_data=brief_data,
        selections_data=selections_data,
        synthesis_data=synthesis_data,
        arc_data=arc_data,
        interviews_map=interviews_map,
    )

    data = {
        "project_name": manifest.get("project_name", "Plotline Project"),
        "brief_name": brief_data.get("name", "Creative Brief"),
        "total_messages": coverage_data["total_messages"],
        "strong_count": coverage_data["strong_count"],
        "weak_count": coverage_data["weak_count"],
        "gap_count": coverage_data["gap_count"],
        "coverage_percent": coverage_data["coverage_percent"],
        "messages": coverage_data["messages"],
        "matrix_rows": coverage_data["matrix_rows"],
        "matrix_columns": coverage_data["matrix_columns"],
        "coverage_gaps": coverage_data["coverage_gaps"],
        "has_gaps": len(coverage_data["coverage_gaps"]) > 0,
        "must_include_status": coverage_data["must_include_status"],
        "has_must_include": len(coverage_data["must_include_status"]) > 0,
        "total_segments": len(coverage_data["matrix_columns"]),
    }

    generator = ReportGenerator()
    result_path = generator.render("coverage.html", data, output_path)

    if open_browser:
        generator.open_in_browser(result_path)

    return result_path
