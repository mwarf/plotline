"""
plotline.diarize.speakers - Speaker configuration management.

Handles loading, saving, and managing speaker name/color mappings.
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

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "color": self.color}

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "SpeakerInfo":
        return cls(name=data.get("name", "Unknown"), color=data.get("color", "#808080"))


@dataclass
class SpeakerConfig:
    """Configuration for speaker names and colors."""

    speakers: dict[str, dict[str, str]] = field(default_factory=dict)

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

    def set_speaker(self, speaker_id: str, name: str, color: str) -> None:
        """Set speaker info.

        Args:
            speaker_id: Speaker identifier
            name: Display name
            color: Hex color string
        """
        self.speakers[speaker_id] = {"name": name, "color": color}

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

    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    return SpeakerConfig.from_dict(data)


def save_speaker_config(config: SpeakerConfig, path: Path) -> None:
    """Save speaker configuration to a file.

    Args:
        config: SpeakerConfig instance
        path: Path to save to
    """
    with open(path, "w") as f:
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
                    }

    return speaker_config.speakers
