"""
plotline.export.fcpxml - FCPXML 1.11 generator.

Generates Final Cut Pro XML files for import into DaVinci Resolve
with markers, keywords, and metadata.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape


def _xa(value: str) -> str:
    """Escape a string for safe use in an XML attribute value (double-quoted).

    Escapes &, <, > and " so that the result can be safely embedded
    inside a double-quoted XML attribute without producing malformed markup.
    """
    return xml_escape(str(value), entities={'"': "&quot;"})


def seconds_to_fcpxml_time(seconds: float, fps: float) -> str:
    """Convert seconds to FCPXML rational time.

    Args:
        seconds: Time in seconds
        fps: Frames per second

    Returns:
        Time string like "2340/1000s"
    """
    frame_count = round(seconds * fps)

    if abs(fps - 23.976) < 0.01:
        numerator = frame_count * 1001
        denominator = 24000
    elif abs(fps - 29.97) < 0.01:
        numerator = frame_count * 1001
        denominator = 30000
    elif abs(fps - 24) < 0.01:
        numerator = frame_count * 100
        denominator = 2400
    elif abs(fps - 25) < 0.01:
        numerator = frame_count * 100
        denominator = 2500
    else:
        numerator = frame_count * 100
        denominator = int(fps * 100)

    return f"{numerator}/{denominator}s"


def get_fcpxml_format(fps: float, width: int = 1920, height: int = 1080) -> dict[str, str]:
    """Get FCPXML format attributes for a given frame rate.

    Args:
        fps: Frames per second
        width: Video width
        height: Video height

    Returns:
        Dict of format attributes
    """
    if abs(fps - 23.976) < 0.01:
        frame_duration = "1001/24000s"
        name = f"FFVideoFormat{height}p2398"
    elif abs(fps - 29.97) < 0.01:
        frame_duration = "1001/30000s"
        name = f"FFVideoFormat{height}p2997"
    elif abs(fps - 24) < 0.01:
        frame_duration = "100/2400s"
        name = f"FFVideoFormat{height}p24"
    elif abs(fps - 25) < 0.01:
        frame_duration = "100/2500s"
        name = f"FFVideoFormat{height}p25"
    else:
        frame_duration = f"100/{int(fps * 100)}s"
        name = f"FFVideoFormat{height}p{int(fps)}"

    return {
        "id": "r1",
        "name": name,
        "frameDuration": frame_duration,
        "width": str(width),
        "height": str(height),
    }


def path_to_file_url(path: Path) -> str:
    """Convert filesystem path to file:// URL.

    Args:
        path: Filesystem path

    Returns:
        file:// URL string (cross-platform, handles Windows drive letters)
    """
    return path.resolve().as_uri()


def generate_fcpxml(
    project_name: str,
    selections: list[dict[str, Any]],
    interviews: dict[str, dict[str, Any]],
    handle_frames: int = 12,
) -> str:
    """Generate FCPXML 1.11 from approved selections.

    Args:
        project_name: Project name
        selections: List of approved segment selections
        interviews: Dict mapping interview_id to interview metadata
        handle_frames: Extra frames before/after each clip

    Returns:
        FCPXML content as string
    """
    # Collect all frame rates, pick the most common for timeline format
    fps_counts: dict[float, int] = {}
    for sel in selections:
        interview = interviews.get(sel.get("interview_id", ""), {})
        sel_fps = interview.get("frame_rate", 24)
        fps_counts[sel_fps] = fps_counts.get(sel_fps, 0) + 1

    if fps_counts:
        fps = max(fps_counts, key=lambda f: fps_counts[f])
    else:
        fps = 24

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<!DOCTYPE fcpxml>",
        '<fcpxml version="1.11">',
        "    <resources>",
    ]

    format_attrs = get_fcpxml_format(fps)
    format_line = "        <format"
    for key, value in format_attrs.items():
        format_line += f' {key}="{value}"'
    format_line += "/>"
    lines.append(format_line)

    asset_id = 1
    asset_map = {}
    for sel in selections:
        interview_id = sel.get("interview_id", "")
        if interview_id not in asset_map:
            interview = interviews.get(interview_id, {})
            source_path = Path(interview.get("source_file", ""))
            duration = interview.get("duration_seconds", 0)

            lines.append(
                f'        <asset id="a{asset_id}" name="{_xa(source_path.stem)}" '
                f'src="{path_to_file_url(source_path)}" '
                f'start="0s" duration="{seconds_to_fcpxml_time(duration, fps)}" '
                f'hasVideo="1" hasAudio="1" format="r1" '
                f'audioSources="1" audioChannels="2"/>'
            )
            asset_map[interview_id] = f"a{asset_id}"
            asset_id += 1

    # Pre-compute clip data to determine actual total duration with handles
    clip_data = []
    cumulative_offset = 0.0

    for i, sel in enumerate(selections, 1):
        interview_id = sel.get("interview_id", "")
        interview = interviews.get(interview_id, {})
        interview_fps = interview.get("frame_rate", fps)

        src_start = sel.get("start", 0)
        src_end = sel.get("end", 0)

        default_handle_sec = handle_frames / interview_fps
        pause_before = sel.get("pause_before_sec", 0)
        pause_after = sel.get("pause_after_sec", 0)
        smart_handle_in = min(default_handle_sec, pause_before * 0.8) if pause_before > 0 else 0.0
        smart_handle_out = min(default_handle_sec, pause_after * 0.8) if pause_after > 0 else 0.0
        padded_start = max(0, src_start - smart_handle_in)
        interview_duration = interview.get("duration_seconds")
        padded_end = src_end + smart_handle_out
        if interview_duration is not None:
            padded_end = min(interview_duration, padded_end)

        clip_duration = padded_end - padded_start

        role = sel.get("role", "")
        speaker = sel.get("speaker")
        text = sel.get("text", "")[:50]

        if speaker and role:
            clip_name = f"{speaker} - {role.title()} - {text}..."
        elif role:
            clip_name = f"{role.title()} - {text}..."
        elif speaker:
            clip_name = f"{speaker} - {text}..."
        else:
            clip_name = f"Clip {i}"

        clip_data.append(
            {
                "sel": sel,
                "interview_id": interview_id,
                "padded_start": padded_start,
                "clip_duration": clip_duration,
                "clip_name": clip_name,
                "offset": cumulative_offset,
                "role": role,
                "speaker": speaker,
                "user_notes": sel.get("user_notes", ""),
            }
        )

        cumulative_offset += clip_duration

    total_duration_tc = seconds_to_fcpxml_time(cumulative_offset, fps)

    lines.extend(
        [
            "    </resources>",
            "    <library>",
            '        <event name="Plotline Selects">',
            f'            <project name="{_xa(project_name)}">',
            '                <sequence format="r1" tcStart="0s" tcFormat="NDF" '
            f'duration="{total_duration_tc}">',
            "                    <spine>",
        ]
    )

    for clip in clip_data:
        sel = clip["sel"]
        ref = asset_map.get(clip["interview_id"], "a1")
        clip_duration = clip["clip_duration"]

        clip_line = (
            f'                        <clip name="{_xa(clip["clip_name"])}" '
            f'ref="{ref}" '
            f'offset="{seconds_to_fcpxml_time(clip["offset"], fps)}" '
            f'start="{seconds_to_fcpxml_time(clip["padded_start"], fps)}" '
            f'duration="{seconds_to_fcpxml_time(clip_duration, fps)}">'
        )
        lines.append(clip_line)

        speaker = clip["speaker"]
        if speaker:
            lines.append(
                f'                            <keyword start="0s" '
                f'duration="{seconds_to_fcpxml_time(clip_duration, fps)}" '
                f'value="{_xa(f"Speaker: {speaker}")}"/>'
            )

        themes = sel.get("themes", [])
        if themes:
            theme_str = ", ".join(str(t) for t in themes)
            lines.append(
                f'                            <keyword start="0s" '
                f'duration="{seconds_to_fcpxml_time(clip_duration, fps)}" '
                f'value="{_xa(theme_str)}"/>'
            )

        delivery_label = sel.get("delivery_label", "")
        editorial_notes = sel.get("editorial_notes", "")
        user_notes = sel.get("user_notes", "")
        role = clip["role"]
        note_parts = [editorial_notes] if editorial_notes else []
        if user_notes:
            note_parts.append(f"Note: {user_notes}")
        combined_note = " | ".join(note_parts) if note_parts else ""
        if delivery_label or combined_note or role:
            marker_value = f"{role}: {delivery_label}" if role else delivery_label
            note_attr = f' note="{_xa(combined_note)}"' if combined_note else ""
            lines.append(
                f'                            <marker start="0s" duration="0s" '
                f'value="{_xa(marker_value)}"{note_attr}/>'
            )

        lines.append("                        </clip>")

    chapter_markers = []
    prev_role = None
    for clip in clip_data:
        role = clip.get("role", "")
        if role and role != prev_role:
            chapter_markers.append(
                {
                    "offset": clip["offset"],
                    "role": role,
                }
            )
            prev_role = role

    lines.extend(
        [
            "                    </spine>",
        ]
    )

    for marker in chapter_markers:
        role_title = marker["role"].replace("_", " ").title()
        lines.append(
            f'                    <chapter-marker start="{seconds_to_fcpxml_time(marker["offset"], fps)}" '
            f'value="{_xa(role_title)}"/>'
        )

    lines.extend(
        [
            "                </sequence>",
            "            </project>",
            "        </event>",
            "    </library>",
            "</fcpxml>",
        ]
    )

    return "\n".join(lines)


def generate_fcpxml_from_project(
    project_path: Path,
    manifest: dict[str, Any],
    handle_frames: int = 12,
    use_approvals: bool = True,
) -> str:
    """Generate FCPXML from project data.

    Args:
        project_path: Path to project directory
        manifest: Project manifest dict
        handle_frames: Handle padding in frames
        use_approvals: Whether to filter by approval status

    Returns:
        FCPXML content as string
    """
    from plotline.io import read_json

    data_dir = project_path / "data"
    selections_path = data_dir / "selections.json"
    approvals_path = project_path / "approvals.json"

    if not selections_path.exists():
        raise FileNotFoundError("No selections found. Run 'plotline arc' first.")

    selections_data = read_json(selections_path)
    all_selections = selections_data.get("segments", [])

    if use_approvals and approvals_path.exists():
        approvals = read_json(approvals_path)
        approved_ids = {
            s["segment_id"] for s in approvals.get("segments", []) if s.get("status") == "approved"
        }
        user_notes_by_id = {
            s["segment_id"]: s.get("user_notes")
            for s in approvals.get("segments", [])
            if s.get("segment_id") and s.get("user_notes")
        }
        selections = []
        for s in all_selections:
            if s["segment_id"] not in approved_ids:
                continue
            sel = dict(s)  # shallow copy — prevents mutating the parsed JSON dicts
            if sel.get("segment_id") in user_notes_by_id:
                sel["user_notes"] = user_notes_by_id[sel["segment_id"]]
            selections.append(sel)
    else:
        selections = list(all_selections)  # copy so sort below doesn't mutate source

    if not selections:
        raise ValueError("No approved selections to export")

    selections.sort(key=lambda s: s.get("position", 0))

    interviews = {}
    for interview in manifest.get("interviews", []):
        interviews[interview["id"]] = interview

    return generate_fcpxml(
        project_name=manifest.get("project_name", "plotline"),
        selections=selections,
        interviews=interviews,
        handle_frames=handle_frames,
    )
