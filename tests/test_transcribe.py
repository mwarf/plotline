"""Tests for plotline.transcribe.engine module."""

from __future__ import annotations

from pathlib import Path

import pytest

from plotline.transcribe.engine import _parse_whisper_result, format_duration


class TestFormatDuration:
    def test_seconds_only(self) -> None:
        assert format_duration(45) == "0:45"

    def test_minutes_and_seconds(self) -> None:
        assert format_duration(125) == "2:05"

    def test_hours_minutes_seconds(self) -> None:
        assert format_duration(3725) == "1:02:05"

    def test_zero(self) -> None:
        assert format_duration(0) == "0:00"


class TestParseWhisperResult:
    def test_parse_empty_result(self) -> None:
        result = _parse_whisper_result({}, "medium", "en")
        assert result["model"] == "medium"
        assert result["language"] == "en"
        assert result["segments"] == []

    def test_parse_segments_with_words(self) -> None:
        whisper_result = {
            "language": "en",
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.5,
                    "text": "Hello world",
                    "avg_logprob": -0.3,
                    "words": [
                        {"word": "Hello", "start": 0.0, "end": 0.5, "probability": 0.9},
                        {"word": " world", "start": 0.6, "end": 1.0, "probability": 0.85},
                    ],
                }
            ],
        }

        result = _parse_whisper_result(whisper_result, "medium", None)

        assert len(result["segments"]) == 1
        assert result["segments"][0]["segment_id"] == "seg_001"
        assert result["segments"][0]["text"] == "Hello world"
        assert len(result["segments"][0]["words"]) == 2
        assert result["segments"][0]["words"][0]["word"] == "Hello"

    def test_segment_ids_increment(self) -> None:
        whisper_result = {
            "language": "en",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "First"},
                {"start": 1.0, "end": 2.0, "text": "Second"},
                {"start": 2.0, "end": 3.0, "text": "Third"},
            ],
        }

        result = _parse_whisper_result(whisper_result, "medium", None)

        assert result["segments"][0]["segment_id"] == "seg_001"
        assert result["segments"][1]["segment_id"] == "seg_002"
        assert result["segments"][2]["segment_id"] == "seg_003"


class TestTranscribeAudio:
    @pytest.mark.slow
    def test_transcribe_real_audio(self, tmp_path: Path) -> None:
        """Test transcription with real audio file."""
        pytest.skip("Requires real audio file - run manually")

    def test_transcribe_missing_file_raises(self, tmp_path: Path) -> None:
        """Test that missing audio file raises TranscriptionError."""
        from plotline.exceptions import TranscriptionError
        from plotline.transcribe.engine import transcribe_audio

        audio_path = tmp_path / "missing.wav"

        with pytest.raises(TranscriptionError):
            transcribe_audio(audio_path, model="medium")


class TestTranscribeAllInterviews:
    def test_empty_manifest(self, tmp_path: Path) -> None:
        """Test transcription with no interviews."""
        from plotline.transcribe.engine import transcribe_all_interviews

        manifest = {"interviews": []}
        results = transcribe_all_interviews(tmp_path, manifest)

        assert results["transcribed"] == 0
        assert results["skipped"] == 0
        assert results["failed"] == 0

    def test_not_extracted_skipped(self, tmp_path: Path) -> None:
        """Test that non-extracted interviews are skipped."""
        from plotline.transcribe.engine import transcribe_all_interviews

        manifest = {
            "interviews": [
                {
                    "id": "interview_001",
                    "stages": {"extracted": False, "transcribed": False},
                }
            ]
        }

        results = transcribe_all_interviews(tmp_path, manifest)

        assert results["transcribed"] == 0
        assert results["skipped"] == 1

    def test_already_transcribed_skipped(self, tmp_path: Path) -> None:
        """Test that already transcribed interviews are skipped."""
        from plotline.transcribe.engine import transcribe_all_interviews

        manifest = {
            "interviews": [
                {
                    "id": "interview_001",
                    "stages": {"extracted": True, "transcribed": True},
                }
            ]
        }

        results = transcribe_all_interviews(tmp_path, manifest, force=False)

        assert results["transcribed"] == 0
        assert results["skipped"] == 1
