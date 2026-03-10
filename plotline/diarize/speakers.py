"""
plotline.diarize.speakers - Speaker configuration management.

Handles loading, saving, and managing speaker name/color mappings,
role assignment, and filtering for EDL export.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_COLORS = [
    "#3B82F6",
    "#10B981",
    "#F59E0B",
    "#EF4444",
    "#8B5CF6",
    "#EC4899",
    "#06B6D4",
    "#84CC16",
    "#F97316",
    "#6366F1",
]


def generate_default_colors() -> list[str]:
    """Return the default color palette for speakers.

    Returns:
        List of hex color strings
    """
    return DEFAULT_COLORS.copy()


@dataclass
class SpeakerInfo:
    """Information about a single speaker."""

    name: str
    color: str
    role: str = "unknown"
    include_in_edl: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "color": self.color,
            "role": self.role,
            "include_in_edl": self.include_in_edl,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpeakerInfo":
        return cls(
            name=data.get("name", "Unknown"),
            color=data.get("color", "#808080"),
            role=data.get("role", "unknown"),
            include_in_edl=data.get("include_in_edl", True),
        )


@dataclass
class SpeakerConfig:
    """Configuration for speaker names, colors, roles, and filtering."""

    speakers: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_speaker_info(self, speaker_id: str) -> SpeakerInfo | None:
        """Get speaker info for a given speaker ID.

        Args:
            speaker_id: Speaker identifier (e.g., "SPEAKER_00")

        Returns:
            SpeakerInfo or None if not found
        """
        if speaker_id in self.speakers:
            return SpeakerInfo.from_dict(self.speakers[speaker_id])
        return None

    def get_speaker_name(self, speaker_id: str) -> str:
        """Get display name for a speaker.

        Args:
            speaker_id: Speaker identifier

        Returns:
            Speaker name or the ID itself if not configured
        """
        info = self.get_speaker_info(speaker_id)
        if info:
            return info.name
        return speaker_id

    def get_speaker_color(self, speaker_id: str) -> str:
        """Get color for a speaker.

        Args:
            speaker_id: Speaker identifier

        Returns:
            Hex color string
        """
        info = self.get_speaker_info(speaker_id)
        if info:
            return info.color

        idx = 0
        if speaker_id.startswith("SPEAKER_"):
            try:
                idx = int(speaker_id.split("_")[1])
            except (IndexError, ValueError):
                pass
        return DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]

    def set_speaker(
        self,
        speaker_id: str,
        name: str,
        color: str,
        role: str = "unknown",
        include_in_edl: bool = True,
    ) -> None:
        """Set speaker info.

        Args:
            speaker_id: Speaker identifier
            name: Display name
            color: Hex color string
            role: Speaker role (interviewer, subject, unknown)
            include_in_edl: Whether to include in EDL export
        """
        self.speakers[speaker_id] = {
            "name": name,
            "color": color,
            "role": role,
            "include_in_edl": include_in_edl,
        }

    def should_include_speaker(self, speaker_id: str) -> bool:
        """Check if a speaker should be included in EDL.

        Args:
            speaker_id: Speaker identifier

        Returns:
            True if speaker should be included, False otherwise
        """
        info = self.get_speaker_info(speaker_id)
        if info:
            return info.include_in_edl
        return True

    def get_speakers_by_role(self, role: str) -> list[str]:
        """Get all speaker IDs with a specific role.

        Args:
            role: Role to filter by (interviewer, subject, unknown)

        Returns:
            List of speaker IDs matching the role
        """
        result = []
        for speaker_id, data in self.speakers.items():
            if data.get("role") == role:
                result.append(speaker_id)
        return result

    def get_excluded_speakers(self) -> list[str]:
        """Get all speaker IDs that are excluded from EDL.

        Returns:
            List of excluded speaker IDs
        """
        result = []
        for speaker_id, data in self.speakers.items():
            if not data.get("include_in_edl", True):
                result.append(speaker_id)
        return result

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {"speakers": self.speakers.copy()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpeakerConfig":
        """Create from dictionary."""
        return cls(speakers=data.get("speakers", {}))


def load_speaker_config(project_path: Path) -> SpeakerConfig:
    """Load speaker configuration from a project.

    Args:
        project_path: Path to project directory

    Returns:
        SpeakerConfig instance
    """
    config_path = project_path / "speakers.yaml"
    if not config_path.exists():
        return SpeakerConfig()

    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return SpeakerConfig.from_dict(data)


def save_speaker_config(config: SpeakerConfig, path: Path) -> None:
    """Save speaker configuration to a file.

    Args:
        config: SpeakerConfig instance
        path: Path to save to
    """
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)


def get_all_speakers_from_project(project_path: Path) -> dict[str, dict[str, str]]:
    """Get all speakers detected across all interviews in a project.

    Scans diarization results to find all unique speaker IDs,
    then merges with speakers.yaml configuration.

    Args:
        project_path: Path to project directory

    Returns:
        Dict mapping speaker IDs to {name, color} dicts
    """
    from plotline.project import read_json

    speaker_config = load_speaker_config(project_path)

    diarization_dir = project_path / "data" / "diarization"
    if diarization_dir.exists():
        for diarization_file in diarization_dir.glob("*.json"):
            diarization = read_json(diarization_file)
            for speaker_id in diarization.get("speakers", []):
                if speaker_id not in speaker_config.speakers:
                    idx = 0
                    if speaker_id.startswith("SPEAKER_"):
                        try:
                            idx = int(speaker_id.split("_")[1])
                        except (IndexError, ValueError):
                            pass
                    speaker_config.speakers[speaker_id] = {
                        "name": f"Speaker {idx + 1}",
                        "color": DEFAULT_COLORS[idx % len(DEFAULT_COLORS)],
                        "role": "unknown",
                        "include_in_edl": True,
                    }

    return speaker_config.speakers


def get_speaker_statistics(project_path: Path, speaker_id: str) -> dict[str, Any]:
    """Get statistics about a speaker across all interviews.

    Args:
        project_path: Path to project directory
        speaker_id: Speaker identifier (e.g., "SPEAKER_00")

    Returns:
        Dict with segment_count, total_duration, question_count, avg_segment_duration
    """
    from plotline.project import read_json

    total_segments = 0
    total_duration = 0.0
    question_count = 0

    transcripts_dir = project_path / "data" / "transcripts"
    if transcripts_dir.exists():
        for transcript_file in transcripts_dir.glob("*.json"):
            transcript = read_json(transcript_file)
            for segment in transcript.get("segments", []):
                if segment.get("speaker") == speaker_id:
                    total_segments += 1
                    duration = segment.get("end", 0) - segment.get("start", 0)
                    total_duration += duration

                    text = segment.get("text", "").strip()
                    if text.endswith("?"):
                        question_count += 1

    avg_segment_duration = total_duration / total_segments if total_segments > 0 else 0.0

    return {
        "segment_count": total_segments,
        "total_duration": total_duration,
        "question_count": question_count,
        "avg_segment_duration": avg_segment_duration,
    }


def identify_speaker_role(stats: dict[str, Any]) -> dict[str, Any]:
    """Use heuristics to guess if speaker is interviewer or subject.

    Heuristics:
    - Interviewers ask more questions
    - Interviewers have shorter average segment duration
    - Interviewers speak less total time

    Args:
        stats: Speaker statistics from get_speaker_statistics()

    Returns:
        Dict with role_guess, reason, and suggest_exclude
    """
    segment_count = stats["segment_count"]
    question_count = stats["question_count"]
    avg_duration = stats["avg_segment_duration"]
    total_duration = stats["total_duration"]

    if segment_count == 0:
        return {
            "role_guess": "unknown",
            "reason": "No segments found",
            "suggest_exclude": False,
        }

    question_ratio = question_count / segment_count

    reasons = []
    suggest_exclude = False

    if question_ratio > 0.3:
        reasons.append("asks many questions")
        suggest_exclude = True

    if avg_duration < 5.0 and segment_count > 5:
        reasons.append("short segments")
        suggest_exclude = True

    if segment_count > 10 and total_duration < 600:
        reasons.append("less talk time")
        suggest_exclude = True

    if reasons:
        role_guess = "interviewer" if suggest_exclude else "subject"
        reason_str = f"Likely {role_guess.upper()} ({', '.join(reasons)})"
    else:
        role_guess = "subject"
        reason_str = "Likely SUBJECT"
        suggest_exclude = False

    return {
        "role_guess": role_guess,
        "reason": reason_str,
        "suggest_exclude": suggest_exclude,
    }


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "12.3 min" or "45 sec"
    """
    if seconds >= 60:
        minutes = seconds / 60
        return f"{minutes:.1f} min"
    else:
        return f"{int(seconds)} sec"
