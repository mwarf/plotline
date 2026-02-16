"""
Test configuration and shared fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory with basic structure."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    (project_dir / "source").mkdir()
    (project_dir / "data").mkdir()
    (project_dir / "data" / "transcripts").mkdir()
    (project_dir / "data" / "delivery").mkdir()
    (project_dir / "data" / "segments").mkdir()
    (project_dir / "data" / "themes").mkdir()
    (project_dir / "reports").mkdir()
    (project_dir / "export").mkdir()
    (project_dir / "prompts").mkdir()

    config = {"project_name": "test_project", "project_profile": "documentary"}
    with open(project_dir / "plotline.yaml", "w") as f:
        yaml.dump(config, f)

    manifest = {"project_name": "test_project", "interviews": []}
    with open(project_dir / "interviews.json", "w") as f:
        import json

        json.dump(manifest, f)

    return project_dir


@pytest.fixture
def sample_config_dict() -> dict:
    """Return a sample configuration dictionary."""
    return {
        "project_name": "test-project",
        "project_profile": "documentary",
        "privacy_mode": "local",
        "llm_backend": "ollama",
        "llm_model": "llama3.1:70b-instruct-q4_K_M",
        "whisper_backend": "mlx",
        "whisper_model": "medium",
        "target_duration_seconds": 600,
        "handle_padding_frames": 12,
        "delivery_weights": {
            "energy": 0.15,
            "pitch_variation": 0.15,
            "speech_rate": 0.25,
            "pause_weight": 0.30,
            "spectral_brightness": 0.10,
            "voice_texture": 0.05,
        },
    }


@pytest.fixture
def sample_transcript() -> dict:
    """Return a sample transcript structure."""
    return {
        "interview_id": "interview_001",
        "model": "medium",
        "language": "en",
        "transcribed_at": "2026-02-15T12:00:00",
        "duration_seconds": 60.0,
        "segments": [
            {
                "segment_id": "interview_001_seg_001",
                "start": 0.0,
                "end": 5.5,
                "text": "When I was young, my grandmother would take us to the river.",
                "confidence": 0.94,
                "corrected": False,
                "words": [
                    {"word": "When", "start": 0.0, "end": 0.3},
                    {"word": "I", "start": 0.35, "end": 0.4},
                    {"word": "was", "start": 0.45, "end": 0.6},
                    {"word": "young,", "start": 0.65, "end": 1.1},
                ],
            }
        ],
    }


@pytest.fixture
def sample_delivery() -> dict:
    """Return a sample delivery analysis structure."""
    return {
        "interview_id": "interview_001",
        "analyzed_at": "2026-02-15T12:30:00",
        "segments": [
            {
                "segment_id": "interview_001_seg_001",
                "raw": {
                    "rms_energy": 0.0234,
                    "pitch_mean_hz": 185.4,
                    "pitch_std_hz": 42.1,
                    "speech_rate_wpm": 128.5,
                    "pause_before_sec": 0.0,
                    "pause_after_sec": 1.2,
                },
                "normalized": {
                    "energy": 0.45,
                    "pitch_variation": 0.72,
                    "speech_rate": 0.38,
                    "pause_weight": 0.15,
                },
                "composite_score": 0.62,
                "delivery_label": "moderate energy, varied pitch, measured pace",
            }
        ],
    }


@pytest.fixture
def sample_segments() -> dict:
    """Return a sample enriched segments structure."""
    return {
        "interview_id": "interview_001",
        "source_file": "test_video.mov",
        "duration_seconds": 60.0,
        "segment_count": 1,
        "enriched_at": "2026-02-15T13:00:00",
        "segments": [
            {
                "segment_id": "interview_001_seg_001",
                "start": 0.0,
                "end": 5.5,
                "text": "When I was young, my grandmother would take us to the river.",
                "words": [
                    {"word": "When", "start": 0.0, "end": 0.3},
                ],
                "confidence": 0.94,
                "corrected": False,
                "delivery": {
                    "energy": 0.45,
                    "pitch_variation": 0.72,
                    "speech_rate": 0.38,
                    "pause_weight": 0.15,
                    "composite_score": 0.62,
                    "delivery_label": "moderate energy, varied pitch, measured pace",
                },
            }
        ],
    }


@pytest.fixture
def sample_manifest() -> dict:
    """Return a sample project manifest."""
    return {
        "project_name": "test-project",
        "created": "2026-02-15T10:00:00",
        "profile": "documentary",
        "interviews": [
            {
                "id": "interview_001",
                "source_file": "/path/to/video.mov",
                "filename": "video.mov",
                "file_hash": "sha256:abc123",
                "duration_seconds": 60.0,
                "frame_rate": 23.976,
                "start_timecode": "01:00:00:00",
                "resolution": "1920x1080",
                "codec": "prores",
                "sample_rate": 48000,
                "stages": {
                    "extracted": True,
                    "transcribed": True,
                    "analyzed": False,
                    "enriched": False,
                    "themes": False,
                    "reviewed": False,
                },
            }
        ],
    }
