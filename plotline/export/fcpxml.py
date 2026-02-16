"""
plotline.export.fcpxml - FCPXML 1.11 generator.

Generates Final Cut Pro XML files for import into DaVinci Resolve
with markers, keywords, and metadata.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote


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
        file:// URL string
    """
    absolute = path.resolve()
    return f"file://{quote(str(absolute))}"


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
    all_fps = set()
    for sel in selections:
        interview = interviews.get(sel.get("interview_id", ""), {})
        fps = interview.get("frame_rate", 24)
        all_fps.add(fps)

    fps = all_fps.pop() if all_fps else 24

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
                f'        <asset id="a{asset_id}" name="{source_path.stem}" '
                f'src="{path_to_file_url(source_path)}" '
                f'start="0s" duration="{seconds_to_fcpxml_time(duration, fps)}" '
                f'hasVideo="1" hasAudio="1" format="r1" '
                f'audioSources="1" audioChannels="2"/>'
            )
            asset_map[interview_id] = f"a{asset_id}"
            asset_id += 1

    total_duration = sum(s.get("end", 0) - s.get("start", 0) for s in selections)
    total_duration_tc = seconds_to_fcpxml_time(total_duration, fps)

    lines.extend(
        [
            "    </resources>",
            "    <library>",
            '        <event name="Plotline Selects">',
            f'            <project name="{project_name}">',
            '                <sequence format="r1" tcStart="0s" tcFormat="NDF" '
            f'duration="{total_duration_tc}">',
            "                    <spine>",
        ]
    )

    cumulative_offset = 0.0

    for i, sel in enumerate(selections, 1):
        interview_id = sel.get("interview_id", "")
        interview = interviews.get(interview_id, {})
        interview_fps = interview.get("frame_rate", fps)

        src_start = sel.get("start", 0)
        src_end = sel.get("end", 0)

        handle_sec = handle_frames / interview_fps
        padded_start = max(0, src_start - handle_sec)
        interview_duration = interview.get("duration_seconds", src_end)
        padded_end = min(interview_duration, src_end + handle_sec)

        clip_duration = padded_end - padded_start

        role = sel.get("role", "")
        text = sel.get("text", "")[:50]
        clip_name = f"{role.title()} - {text}..." if role else f"Clip {i}"

        ref = asset_map.get(interview_id, "a1")

        clip_line = (
            f'                        <clip name="{clip_name}" '
            f'ref="{ref}" '
            f'offset="{seconds_to_fcpxml_time(cumulative_offset, fps)}" '
            f'start="{seconds_to_fcpxml_time(padded_start, fps)}" '
            f'duration="{seconds_to_fcpxml_time(clip_duration, fps)}">'
        )
        lines.append(clip_line)

        themes = sel.get("themes", [])
        if themes:
            theme_str = ", ".join(str(t) for t in themes[:3])
            lines.append(
                f'                            <keyword start="0s" '
                f'duration="{seconds_to_fcpxml_time(clip_duration, fps)}" '
                f'value="{theme_str}"/>'
            )

        delivery_label = sel.get("delivery_label", "")
        editorial_notes = sel.get("editorial_notes", "")
        if delivery_label or editorial_notes or role:
            marker_value = f"{role}: {delivery_label}" if role else delivery_label
            note_attr = f' note="{editorial_notes}"' if editorial_notes else ""
            lines.append(
                f'                            <marker start="0s" duration="0s" '
                f'value="{marker_value}"{note_attr}/>'
            )

        lines.append("                        </clip>")

        cumulative_offset += clip_duration

    lines.extend(
        [
            "                    </spine>",
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
    from plotline.project import read_json

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
        selections = [s for s in all_selections if s["segment_id"] in approved_ids]
    else:
        selections = all_selections

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
