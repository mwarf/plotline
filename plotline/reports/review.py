"""
plotline.reports.review - Selection review report.

Primary editorial interface for reviewing and approving selected segments.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from plotline.export.timecode import seconds_to_timecode
from plotline.project import read_json
from plotline.reports.generator import ReportGenerator
from plotline.utils import format_duration, get_delivery_class


def _build_theme_name_lookup(project_path: Path) -> dict[str, str]:
    """Build a mapping from theme ID to human-readable theme name.

    Reads synthesis.json to resolve unified_theme_id values (e.g. 'utheme_001')
    into their display names.

    Args:
        project_path: Path to project directory

    Returns:
        Dict mapping theme ID -> theme name
    """
    synthesis_path = project_path / "data" / "synthesis.json"
    if not synthesis_path.exists():
        return {}

    synthesis = read_json(synthesis_path)
    lookup: dict[str, str] = {}

    for theme in synthesis.get("unified_themes", []):
        theme_id = theme.get("unified_theme_id", "")
        name = theme.get("name", theme_id)
        if theme_id:
            lookup[theme_id] = name

    return lookup


def _load_speaker_config(project_path: Path) -> dict[str, dict[str, str]]:
    """Load speaker configuration for display names and colors.

    Args:
        project_path: Path to project directory

    Returns:
        Dict mapping speaker ID -> {name, color}
    """
    from plotline.diarize.speakers import get_all_speakers_from_project

    return get_all_speakers_from_project(project_path)


def generate_review(
    project_path: Path,
    manifest: dict[str, Any],
    output_path: Path | None = None,
    open_browser: bool = False,
) -> Path:
    """Generate the selection review report.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        output_path: Optional output path
        open_browser: Whether to open in browser

    Returns:
        Path to generated report
    """
    if output_path is None:
        output_path = project_path / "reports" / "review.html"

    selections_path = project_path / "data" / "selections.json"
    if not selections_path.exists():
        raise FileNotFoundError("No selections found. Run 'plotline arc' first.")

    selections_data = read_json(selections_path)
    all_segments = selections_data.get("segments", [])

    arc_path = project_path / "data" / "arc.json"
    arc_data = {}
    if arc_path.exists():
        arc_data = read_json(arc_path)

    alternates_by_position = {}
    for alt in arc_data.get("alternate_candidates", []):
        pos = alt.get("for_position")
        if pos:
            if pos not in alternates_by_position:
                alternates_by_position[pos] = []
            alternates_by_position[pos].append(alt)

    approvals_path = project_path / "approvals.json"
    approvals = {}
    if approvals_path.exists():
        approvals_data = read_json(approvals_path)
        approvals = {s["segment_id"]: s["status"] for s in approvals_data.get("segments", [])}

    interviews_map = {}
    for interview in manifest.get("interviews", []):
        interviews_map[interview["id"]] = interview

    # Resolve theme IDs to human-readable names
    theme_name_lookup = _build_theme_name_lookup(project_path)

    # Load speaker configuration for display names and colors
    speaker_config = _load_speaker_config(project_path)
    has_speakers = bool(speaker_config)

    segments_data = []
    total_duration = 0.0
    approved_count = 0
    rejected_count = 0
    flagged_count = 0
    cultural_flag_count = 0

    for segment in all_segments:
        segment_id = segment.get("segment_id", "")
        interview_id = segment.get("interview_id", "")
        interview = interviews_map.get(interview_id, {})
        fps = interview.get("frame_rate", 24)

        start = segment.get("start", 0)
        end = segment.get("end", 0)
        duration = end - start
        total_duration += duration

        status = approvals.get(segment_id, "pending")
        if status == "approved":
            approved_count += 1
        elif status == "rejected":
            rejected_count += 1
        elif status == "flagged":
            flagged_count += 1

        delivery_score = segment.get("composite_score", 0.5)

        audio_path = None
        if interview.get("audio_full_path"):
            audio_path = f"../{interview['audio_full_path']}#t={max(0, start - 2)}"

        # Cultural sensitivity flags from plotline flags
        is_culturally_flagged = segment.get("flagged", False)
        flag_reason = segment.get("flag_reason") or ""
        if is_culturally_flagged:
            cultural_flag_count += 1

        # Resolve theme IDs to display names
        raw_themes = segment.get("themes", [])
        resolved_themes = [theme_name_lookup.get(t, t) for t in raw_themes]

        # Resolve speaker info
        speaker_id = segment.get("speaker")
        speaker_info = speaker_config.get(speaker_id, {}) if speaker_id else None
        speaker_name = speaker_info.get("name", speaker_id) if speaker_info else None
        speaker_color = speaker_info.get("color", "#808080") if speaker_info else None

        pacing = segment.get("pacing", "")
        position = segment.get("position")
        alternates = alternates_by_position.get(position, []) if position else []

        segments_data.append(
            {
                "id": segment_id,
                "position": position,
                "role": segment.get("role", "body").title(),
                "text": segment.get("text", ""),
                "timecode": f"{seconds_to_timecode(start, fps)} - {seconds_to_timecode(end, fps)}",
                "start": start,
                "end": end,
                "duration": format_duration(duration),
                "themes": resolved_themes,
                "delivery_score": delivery_score,
                "delivery_class": get_delivery_class(delivery_score),
                "delivery_label": segment.get("delivery_label", ""),
                "editorial_notes": segment.get("editorial_notes", ""),
                "pacing": pacing,
                "alternate_candidates": alternates,
                "status": status,
                "audio_path": audio_path,
                "culturally_flagged": is_culturally_flagged,
                "flag_reason": flag_reason,
                "speaker_id": speaker_id,
                "speaker_name": speaker_name,
                "speaker_color": speaker_color,
            }
        )

    total_segments = len(segments_data)
    reviewed_count = approved_count + rejected_count + flagged_count
    progress_percent = (reviewed_count / total_segments * 100) if total_segments > 0 else 0

    interviews_data = {
        interview["id"]: {
            "id": interview["id"],
            "filename": interview["filename"],
            "frame_rate": interview.get("frame_rate", 24),
            "duration_seconds": interview.get("duration_seconds", 0),
            "start_timecode": interview.get("start_timecode"),
            "resolution": interview.get("resolution", "1920x1080"),
        }
        for interview in manifest.get("interviews", [])
    }

    data = {
        "project_name": manifest.get("project_name", "Plotline Project"),
        "total_segments": total_segments,
        "total_duration": format_duration(total_duration),
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "flagged_count": flagged_count,
        "cultural_flag_count": cultural_flag_count,
        "progress_percent": round(progress_percent, 1),
        "segments": segments_data,
        "has_speakers": has_speakers,
        "interviews": interviews_data,
    }

    generator = ReportGenerator()
    result_path = generator.render("review.html", data, output_path, manifest=manifest)

    if open_browser:
        generator.open_in_browser(result_path)

    return result_path
