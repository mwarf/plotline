"""Tests for plotline.diarize module."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from plotline.diarize.align import (
    assign_speakers_to_transcript,
    assign_speakers_to_words,
    compute_segment_speaker,
    find_speaker_for_time,
)
from plotline.diarize.engine import get_device, get_hf_token
from plotline.diarize.speakers import (
    DEFAULT_COLORS,
    SpeakerConfig,
    SpeakerInfo,
    generate_default_colors,
    get_all_speakers_from_project,
    load_speaker_config,
    save_speaker_config,
)


def _make_diarization_segments() -> list[dict]:
    """Create sample diarization segments for testing."""
    return [
        {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
        {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_01"},
        {"start": 10.0, "end": 15.0, "speaker": "SPEAKER_00"},
    ]


def _make_words() -> list[dict]:
    """Create sample words for testing."""
    return [
        {"word": "Hello", "start": 0.0, "end": 0.5},
        {"word": "world", "start": 0.6, "end": 1.0},
        {"word": "this", "start": 5.5, "end": 5.8},
        {"word": "is", "start": 5.9, "end": 6.0},
        {"word": "test", "start": 20.0, "end": 20.5},
    ]


def _make_transcript() -> dict:
    """Create a sample transcript for testing."""
    return {
        "interview_id": "test_001",
        "segments": [
            {
                "segment_id": "seg_001",
                "start": 0.0,
                "end": 2.0,
                "text": "Hello world",
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 0.5},
                    {"word": "world", "start": 0.6, "end": 1.0},
                ],
            },
            {
                "segment_id": "seg_002",
                "start": 5.0,
                "end": 7.0,
                "text": "This is",
                "words": [
                    {"word": "This", "start": 5.0, "end": 5.3},
                    {"word": "is", "start": 5.4, "end": 5.6},
                ],
            },
        ],
    }


def _make_diarization() -> dict:
    """Create a sample diarization result for testing."""
    return {
        "model": "pyannote/speaker-diarization-3.1",
        "diarized_at": "2026-03-03T12:00:00",
        "num_speakers_detected": 2,
        "speakers": ["SPEAKER_00", "SPEAKER_01"],
        "segments": _make_diarization_segments(),
    }


class TestFindSpeakerForTime:
    def test_exact_match(self) -> None:
        segments = _make_diarization_segments()
        result = find_speaker_for_time(2.5, segments)
        assert result == "SPEAKER_00"

    def test_match_at_boundary(self) -> None:
        segments = _make_diarization_segments()
        result = find_speaker_for_time(2.5, segments)
        assert result == "SPEAKER_00"

    def test_no_match_returns_none(self) -> None:
        segments = _make_diarization_segments()
        result = find_speaker_for_time(20.0, segments)
        assert result is None

    def test_empty_segments_returns_none(self) -> None:
        result = find_speaker_for_time(2.5, [])
        assert result is None

    def test_longest_overlap_wins(self) -> None:
        segments = [
            {"start": 0.0, "end": 10.0, "speaker": "SPEAKER_00"},
            {"start": 8.0, "end": 15.0, "speaker": "SPEAKER_01"},
        ]
        result = find_speaker_for_time(9.0, segments)
        assert result == "SPEAKER_00"


class TestAssignSpeakersToWords:
    def test_assigns_speaker_to_each_word(self) -> None:
        words = _make_words()
        segments = _make_diarization_segments()
        result = assign_speakers_to_words(words, segments)

        assert len(result) == 5
        assert result[0]["speaker"] == "SPEAKER_00"
        assert result[1]["speaker"] == "SPEAKER_00"
        assert result[2]["speaker"] == "SPEAKER_01"
        assert result[3]["speaker"] == "SPEAKER_01"

    def test_gap_assigned_to_nearest_speaker(self) -> None:
        words = [{"word": "gap", "start": 17.0, "end": 17.5}]
        segments = _make_diarization_segments()
        result = assign_speakers_to_words(words, segments)

        assert result[0]["speaker"] == "SPEAKER_00"

    def test_empty_diarization_returns_unchanged(self) -> None:
        words = _make_words()
        result = assign_speakers_to_words(words, [])

        assert len(result) == 5
        assert "speaker" not in result[0]

    def test_preserves_word_fields(self) -> None:
        words = [{"word": "test", "start": 0.0, "end": 0.5, "confidence": 0.9}]
        segments = _make_diarization_segments()
        result = assign_speakers_to_words(words, segments)

        assert result[0]["word"] == "test"
        assert result[0]["confidence"] == 0.9
        assert result[0]["speaker"] == "SPEAKER_00"

    def test_returns_copy_not_original(self) -> None:
        words = _make_words()
        segments = _make_diarization_segments()
        result = assign_speakers_to_words(words, segments)

        assert "speaker" not in words[0]
        assert "speaker" in result[0]


class TestComputeSegmentSpeaker:
    def test_majority_vote(self) -> None:
        words = [
            {"word": "a", "speaker": "SPEAKER_00"},
            {"word": "b", "speaker": "SPEAKER_00"},
            {"word": "c", "speaker": "SPEAKER_01"},
        ]
        result = compute_segment_speaker(words)
        assert result == "SPEAKER_00"

    def test_empty_words_returns_none(self) -> None:
        result = compute_segment_speaker([])
        assert result is None

    def test_no_speaker_field_returns_none(self) -> None:
        words = [
            {"word": "a"},
            {"word": "b"},
        ]
        result = compute_segment_speaker(words)
        assert result is None

    def test_single_speaker(self) -> None:
        words = [
            {"word": "a", "speaker": "SPEAKER_01"},
            {"word": "b", "speaker": "SPEAKER_01"},
        ]
        result = compute_segment_speaker(words)
        assert result == "SPEAKER_01"


class TestAssignSpeakersToTranscript:
    def test_assigns_to_all_segments(self) -> None:
        transcript = _make_transcript()
        diarization = _make_diarization()
        result = assign_speakers_to_transcript(transcript, diarization)

        assert len(result["segments"]) == 2
        assert result["segments"][0]["speaker"] == "SPEAKER_00"
        assert result["segments"][1]["speaker"] == "SPEAKER_01"

    def test_adds_top_level_metadata(self) -> None:
        transcript = _make_transcript()
        diarization = _make_diarization()
        result = assign_speakers_to_transcript(transcript, diarization)

        assert result["diarized_at"] == "2026-03-03T12:00:00"
        assert result["diarization_model"] == "pyannote/speaker-diarization-3.1"
        assert result["num_speakers"] == 2

    def test_assigns_speaker_to_words(self) -> None:
        transcript = _make_transcript()
        diarization = _make_diarization()
        result = assign_speakers_to_transcript(transcript, diarization)

        for word in result["segments"][0]["words"]:
            assert word["speaker"] == "SPEAKER_00"

    def test_returns_copy_not_mutating_original(self) -> None:
        transcript = _make_transcript()
        diarization = _make_diarization()
        result = assign_speakers_to_transcript(transcript, diarization)

        assert "speaker" not in transcript["segments"][0]
        assert "speaker" in result["segments"][0]

    def test_handles_empty_transcript(self) -> None:
        transcript = {"interview_id": "empty", "segments": []}
        diarization = _make_diarization()
        result = assign_speakers_to_transcript(transcript, diarization)

        assert result["segments"] == []


class TestSpeakerInfo:
    def test_to_dict(self) -> None:
        info = SpeakerInfo(name="Alice", color="#3B82F6")
        result = info.to_dict()
        assert result == {
            "name": "Alice",
            "color": "#3B82F6",
            "role": "unknown",
            "include_in_edl": True,
        }

    def test_to_dict_with_role(self) -> None:
        info = SpeakerInfo(name="Bob", color="#10B981", role="interviewer", include_in_edl=False)
        result = info.to_dict()
        assert result == {
            "name": "Bob",
            "color": "#10B981",
            "role": "interviewer",
            "include_in_edl": False,
        }

    def test_from_dict(self) -> None:
        data = {"name": "Bob", "color": "#10B981"}
        result = SpeakerInfo.from_dict(data)
        assert result.name == "Bob"
        assert result.color == "#10B981"
        assert result.role == "unknown"
        assert result.include_in_edl is True

    def test_from_dict_with_role(self) -> None:
        data = {"name": "Carol", "color": "#F59E0B", "role": "subject", "include_in_edl": True}
        result = SpeakerInfo.from_dict(data)
        assert result.name == "Carol"
        assert result.color == "#F59E0B"
        assert result.role == "subject"
        assert result.include_in_edl is True

    def test_from_dict_defaults(self) -> None:
        result = SpeakerInfo.from_dict({})
        assert result.name == "Unknown"
        assert result.color == "#808080"
        assert result.role == "unknown"
        assert result.include_in_edl is True


class TestSpeakerConfig:
    def test_get_speaker_info_found(self) -> None:
        config = SpeakerConfig(
            speakers={
                "SPEAKER_00": {
                    "name": "Alice",
                    "color": "#3B82F6",
                    "role": "subject",
                    "include_in_edl": True,
                }
            }
        )
        result = config.get_speaker_info("SPEAKER_00")

        assert result is not None
        assert result.name == "Alice"
        assert result.color == "#3B82F6"
        assert result.role == "subject"
        assert result.include_in_edl is True

    def test_get_speaker_info_not_found(self) -> None:
        config = SpeakerConfig()
        result = config.get_speaker_info("SPEAKER_99")
        assert result is None

    def test_get_speaker_name_returns_configured(self) -> None:
        config = SpeakerConfig(
            speakers={
                "SPEAKER_00": {
                    "name": "Alice",
                    "color": "#3B82F6",
                    "role": "unknown",
                    "include_in_edl": True,
                }
            }
        )
        result = config.get_speaker_name("SPEAKER_00")
        assert result == "Alice"

    def test_get_speaker_name_returns_id_as_fallback(self) -> None:
        config = SpeakerConfig()
        result = config.get_speaker_name("SPEAKER_99")
        assert result == "SPEAKER_99"

    def test_get_speaker_color_returns_configured(self) -> None:
        config = SpeakerConfig(
            speakers={
                "SPEAKER_00": {
                    "name": "Alice",
                    "color": "#10B981",
                    "role": "unknown",
                    "include_in_edl": True,
                }
            }
        )
        result = config.get_speaker_color("SPEAKER_00")
        assert result == "#10B981"

    def test_get_speaker_color_derives_from_index(self) -> None:
        config = SpeakerConfig()
        result = config.get_speaker_color("SPEAKER_00")
        assert result == DEFAULT_COLORS[0]

    def test_get_speaker_color_derives_second_speaker(self) -> None:
        config = SpeakerConfig()
        result = config.get_speaker_color("SPEAKER_01")
        assert result == DEFAULT_COLORS[1]

    def test_get_speaker_color_wraps_around(self) -> None:
        config = SpeakerConfig()
        result = config.get_speaker_color("SPEAKER_10")
        assert result == DEFAULT_COLORS[0]

    def test_get_speaker_color_invalid_id_uses_zero(self) -> None:
        config = SpeakerConfig()
        result = config.get_speaker_color("unknown")
        assert result == DEFAULT_COLORS[0]

    def test_set_speaker(self) -> None:
        config = SpeakerConfig()
        config.set_speaker("SPEAKER_00", "Alice", "#3B82F6")

        assert "SPEAKER_00" in config.speakers
        assert config.speakers["SPEAKER_00"]["name"] == "Alice"
        assert config.speakers["SPEAKER_00"]["color"] == "#3B82F6"

    def test_to_dict(self) -> None:
        config = SpeakerConfig(speakers={"SPEAKER_00": {"name": "Alice", "color": "#3B82F6"}})
        result = config.to_dict()
        assert result == {"speakers": {"SPEAKER_00": {"name": "Alice", "color": "#3B82F6"}}}

    def test_from_dict(self) -> None:
        data = {"speakers": {"SPEAKER_01": {"name": "Bob", "color": "#10B981"}}}
        result = SpeakerConfig.from_dict(data)
        assert "SPEAKER_01" in result.speakers


class TestGenerateDefaultColors:
    def test_returns_list_of_colors(self) -> None:
        result = generate_default_colors()
        assert len(result) == 10
        assert result[0] == "#3B82F6"

    def test_returns_copy(self) -> None:
        result = generate_default_colors()
        result.append("#000000")
        assert len(DEFAULT_COLORS) == 10


class TestLoadSpeakerConfig:
    def test_loads_existing_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "speakers.yaml"
        config_file.write_text("speakers:\n  SPEAKER_00:\n    name: Alice\n    color: '#3B82F6'\n")

        result = load_speaker_config(tmp_path)
        assert "SPEAKER_00" in result.speakers
        assert result.speakers["SPEAKER_00"]["name"] == "Alice"

    def test_missing_file_returns_empty_config(self, tmp_path: Path) -> None:
        result = load_speaker_config(tmp_path)
        assert result.speakers == {}

    def test_empty_file_returns_empty_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "speakers.yaml"
        config_file.write_text("")

        result = load_speaker_config(tmp_path)
        assert result.speakers == {}


class TestSaveSpeakerConfig:
    def test_saves_to_yaml(self, tmp_path: Path) -> None:
        config = SpeakerConfig(speakers={"SPEAKER_00": {"name": "Alice", "color": "#3B82F6"}})
        config_path = tmp_path / "speakers.yaml"

        save_speaker_config(config, config_path)

        assert config_path.exists()
        content = config_path.read_text()
        assert "SPEAKER_00" in content
        assert "Alice" in content

    def test_round_trip(self, tmp_path: Path) -> None:
        original = SpeakerConfig(
            speakers={
                "SPEAKER_00": {"name": "Alice", "color": "#3B82F6"},
                "SPEAKER_01": {"name": "Bob", "color": "#10B981"},
            }
        )
        config_path = tmp_path / "speakers.yaml"

        save_speaker_config(original, config_path)
        loaded = load_speaker_config(tmp_path)

        assert loaded.speakers == original.speakers


class TestGetAllSpeakersFromProject:
    def test_scans_diarization_files(self, tmp_project: Path) -> None:
        diarization_dir = tmp_project / "data" / "diarization"
        diarization_dir.mkdir(parents=True, exist_ok=True)

        diarization_data = {
            "speakers": ["SPEAKER_00", "SPEAKER_01"],
            "segments": [],
        }
        diarization_file = diarization_dir / "interview_001.json"
        diarization_file.write_text(json.dumps(diarization_data))

        result = get_all_speakers_from_project(tmp_project)

        assert "SPEAKER_00" in result
        assert "SPEAKER_01" in result
        assert result["SPEAKER_00"]["name"] == "Speaker 1"
        assert result["SPEAKER_01"]["name"] == "Speaker 2"

    def test_merges_with_existing_config(self, tmp_project: Path) -> None:
        speakers_file = tmp_project / "speakers.yaml"
        speakers_file.write_text(
            "speakers:\n  SPEAKER_00:\n    name: Alice\n    color: '#3B82F6'\n"
        )

        diarization_dir = tmp_project / "data" / "diarization"
        diarization_dir.mkdir(parents=True, exist_ok=True)
        diarization_data = {"speakers": ["SPEAKER_00", "SPEAKER_01"], "segments": []}
        (diarization_dir / "interview_001.json").write_text(json.dumps(diarization_data))

        result = get_all_speakers_from_project(tmp_project)

        assert result["SPEAKER_00"]["name"] == "Alice"
        assert result["SPEAKER_01"]["name"] == "Speaker 2"

    def test_no_diarization_dir_returns_config_only(self, tmp_project: Path) -> None:
        speakers_file = tmp_project / "speakers.yaml"
        speakers_file.write_text(
            "speakers:\n  SPEAKER_00:\n    name: Alice\n    color: '#3B82F6'\n"
        )

        result = get_all_speakers_from_project(tmp_project)

        assert result == {"SPEAKER_00": {"name": "Alice", "color": "#3B82F6"}}


class TestGetHfToken:
    def test_env_var_precedence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HUGGINGFACE_TOKEN", "env_token")

        result = get_hf_token()
        assert result == "env_token"

    def test_cache_file_fallback(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.delenv("HUGGINGFACE_TOKEN", raising=False)

        cache_path = tmp_path / ".plotline" / "hf_token"
        cache_path.parent.mkdir(parents=True)
        cache_path.write_text("cache_token")

        with patch("plotline.diarize.engine.Path.home", return_value=tmp_path):
            result = get_hf_token()
            assert result == "cache_token"

    def test_raises_when_missing(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.delenv("HUGGINGFACE_TOKEN", raising=False)

        cache_file = tmp_path / ".plotline" / "hf_token"
        with patch("plotline.diarize.engine.Path.home", return_value=tmp_path):
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.unlink(missing_ok=True)
            with pytest.raises(ValueError, match="HuggingFace token required"):
                get_hf_token()


class TestGetDevice:
    def test_returns_mps_when_available(self) -> None:
        mock_torch = MagicMock()
        mock_torch.backends.mps.is_available.return_value = True

        with patch.dict("sys.modules", {"torch": mock_torch}):
            result = get_device()
            assert result == "mps"

    def test_returns_cuda_when_mps_unavailable(self) -> None:
        mock_torch = MagicMock()
        mock_torch.backends.mps.is_available.return_value = False
        mock_torch.cuda.is_available.return_value = True

        with patch.dict("sys.modules", {"torch": mock_torch}):
            result = get_device()
            assert result == "cuda"

    def test_returns_valid_device(self) -> None:
        """Test that get_device returns a valid device string."""
        result = get_device()
        assert result in ("mps", "cuda", "cpu")

    def test_returns_cpu_when_torch_unavailable(self) -> None:
        """Test that CPU is returned when torch import fails."""
        with patch.dict("sys.modules", {"torch": None}):
            pass
        result = get_device()
        assert result in ("mps", "cuda", "cpu")
