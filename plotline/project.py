"""
plotline.project - Project directory management.

Handles project creation, directory structure, and manifest management.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from plotline.config import create_default_config, write_config


class Project:
    """Represents a Plotline project directory."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.config_path = path / "plotline.yaml"
        self.manifest_path = path / "interviews.json"
        self.source_dir = path / "source"
        self.data_dir = path / "data"
        self.reports_dir = path / "reports"
        self.export_dir = path / "export"
        self.prompts_dir = path / "prompts"
        self.profiles_dir = path / "profiles"

    @property
    def transcripts_dir(self) -> Path:
        return self.data_dir / "transcripts"

    @property
    def delivery_dir(self) -> Path:
        return self.data_dir / "delivery"

    @property
    def segments_dir(self) -> Path:
        return self.data_dir / "segments"

    @property
    def themes_dir(self) -> Path:
        return self.data_dir / "themes"

    def exists(self) -> bool:
        return self.config_path.exists() and self.manifest_path.exists()

    def create(self, profile: str = "documentary") -> None:
        """Create the project directory structure."""
        self.path.mkdir(parents=True, exist_ok=True)
        self.source_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        self.transcripts_dir.mkdir(exist_ok=True)
        self.delivery_dir.mkdir(exist_ok=True)
        self.segments_dir.mkdir(exist_ok=True)
        self.themes_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        self.export_dir.mkdir(exist_ok=True)
        self.prompts_dir.mkdir(exist_ok=True)
        self.profiles_dir.mkdir(exist_ok=True)

        config = create_default_config(self.path.name, profile)
        write_config(config, self.config_path)

        manifest = {
            "project_name": self.path.name,
            "created": datetime.now().isoformat(timespec="seconds"),
            "profile": profile,
            "interviews": [],
        }
        write_json(self.manifest_path, manifest)

    def load_manifest(self) -> dict[str, Any]:
        """Load the project manifest."""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")
        return read_json(self.manifest_path)

    def save_manifest(self, manifest: dict[str, Any]) -> None:
        """Save the project manifest."""
        write_json(self.manifest_path, manifest)

    def get_interview(self, interview_id: str) -> dict[str, Any] | None:
        """Get an interview by ID from the manifest."""
        manifest = self.load_manifest()
        for interview in manifest.get("interviews", []):
            if interview.get("id") == interview_id:
                return interview
        return None


def compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def probe_video(path: Path) -> dict[str, Any]:
    """Probe video file for metadata using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {result.stderr}")

    data = json.loads(result.stdout)
    video_stream = None
    audio_stream = None
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and video_stream is None:
            video_stream = stream
        elif stream.get("codec_type") == "audio" and audio_stream is None:
            audio_stream = stream

    format_info = data.get("format", {})

    duration = float(format_info.get("duration", 0))
    frame_rate = None
    start_timecode = None
    resolution = None
    codec = None

    if video_stream:
        fps_str = video_stream.get("r_frame_rate", "24/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) > 0 else 24.0
        else:
            fps = float(fps_str)
        if abs(fps - 23.976) < 0.01:
            frame_rate = 23.976
        elif abs(fps - 29.97) < 0.01:
            frame_rate = 29.97
        else:
            frame_rate = round(fps, 3)
        width = video_stream.get("width")
        height = video_stream.get("height")
        resolution = f"{width}x{height}" if width and height else None
        codec = video_stream.get("codec_name")

        tags = video_stream.get("tags", {})
        start_timecode = tags.get("timecode")

    sample_rate = None
    if audio_stream:
        sample_rate = int(audio_stream.get("sample_rate", 48000))

    return {
        "duration_seconds": duration,
        "frame_rate": frame_rate,
        "start_timecode": start_timecode,
        "resolution": resolution,
        "codec": codec,
        "sample_rate": sample_rate,
    }


def read_json(path: Path) -> dict[str, Any]:
    """Read JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON file atomically with pretty formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp_path.rename(path)


def generate_interview_id(manifest: dict[str, Any]) -> str:
    """Generate a unique interview ID."""
    existing = {i.get("id", "") for i in manifest.get("interviews", [])}
    counter = 1
    while True:
        interview_id = f"interview_{counter:03d}"
        if interview_id not in existing:
            return interview_id
        counter += 1
