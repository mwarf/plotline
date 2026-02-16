"""Tests for plotline.analyze.delivery module."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from plotline.analyze.delivery import extract_segment_features
from plotline.analyze.scoring import (
    compute_composite_score,
    generate_delivery_label,
    normalize_metrics,
)


class TestExtractSegmentFeatures:
    def test_extract_features_basic(self) -> None:
        """Test basic feature extraction."""
        sr = 16000
        duration = 2.0
        audio = np.random.randn(int(sr * duration)).astype(np.float32) * 0.1

        features = extract_segment_features(
            audio=audio,
            sr=sr,
            start=0.0,
            end=duration,
        )

        assert "rms_energy" in features
        assert "pitch_mean_hz" in features
        assert "pitch_std_hz" in features
        assert "pause_before_sec" in features
        assert "pause_after_sec" in features
        assert features["pause_before_sec"] == 0.0
        assert features["pause_after_sec"] == 0.0

    def test_pause_calculation(self) -> None:
        """Test pause before/after calculation."""
        sr = 16000
        audio = np.random.randn(sr * 5).astype(np.float32) * 0.1

        features = extract_segment_features(
            audio=audio,
            sr=sr,
            start=2.0,
            end=3.0,
            prev_end=1.5,
            next_start=4.0,
        )

        assert features["pause_before_sec"] == 0.5
        assert features["pause_after_sec"] == 1.0

    def test_empty_segment(self) -> None:
        """Test handling of empty segment."""
        sr = 16000
        audio = np.random.randn(sr).astype(np.float32)

        features = extract_segment_features(
            audio=audio,
            sr=sr,
            start=10.0,
            end=11.0,
        )

        assert features["rms_energy"] == 0.0


class TestNormalizeMetrics:
    def test_normalize_single_value(self) -> None:
        """Test normalization with single value."""
        raw = [{"rms_energy": 0.5}]
        normalized = normalize_metrics(raw)
        assert normalized[0]["energy"] == 0.5

    def test_normalize_multiple_values(self) -> None:
        """Test min-max normalization."""
        raw = [
            {
                "rms_energy": 0.1,
                "pitch_std_hz": 10,
                "speech_rate_wpm": 100,
                "spectral_centroid_mean": 1000,
                "zero_crossing_rate": 0.1,
            },
            {
                "rms_energy": 0.5,
                "pitch_std_hz": 50,
                "speech_rate_wpm": 200,
                "spectral_centroid_mean": 3000,
                "zero_crossing_rate": 0.3,
            },
            {
                "rms_energy": 0.3,
                "pitch_std_hz": 30,
                "speech_rate_wpm": 150,
                "spectral_centroid_mean": 2000,
                "zero_crossing_rate": 0.2,
            },
        ]
        normalized = normalize_metrics(raw)

        assert normalized[0]["energy"] == 0.0
        assert normalized[1]["energy"] == 1.0
        assert normalized[2]["energy"] == 0.5

    def test_normalize_empty(self) -> None:
        """Test normalization with empty input."""
        normalized = normalize_metrics([])
        assert normalized == []


class TestComputeCompositeScore:
    def test_composite_score_basic(self) -> None:
        """Test basic composite score calculation."""
        normalized = {
            "energy": 0.5,
            "pitch_variation": 0.5,
            "speech_rate": 0.5,
            "pause_weight": 0.5,
            "spectral_brightness": 0.5,
            "voice_texture": 0.5,
        }
        weights = {
            "energy": 0.2,
            "pitch_variation": 0.1,
            "speech_rate": 0.2,
            "pause_weight": 0.3,
            "spectral_brightness": 0.1,
            "voice_texture": 0.1,
        }

        score = compute_composite_score(normalized, weights)
        assert 0.0 <= score <= 1.0

    def test_composite_score_weighted(self) -> None:
        """Test that weights affect the score."""
        normalized = {
            "energy": 1.0,
            "pitch_variation": 0.0,
            "speech_rate": 0.0,
            "pause_weight": 0.0,
            "spectral_brightness": 0.0,
            "voice_texture": 0.0,
        }

        weights_high_energy = {
            "energy": 1.0,
            "pitch_variation": 0.0,
            "speech_rate": 0.0,
            "pause_weight": 0.0,
            "spectral_brightness": 0.0,
            "voice_texture": 0.0,
        }
        score_high = compute_composite_score(normalized, weights_high_energy)

        assert score_high == 1.0


class TestGenerateDeliveryLabel:
    def test_quiet_label(self) -> None:
        """Test label for quiet segment."""
        normalized = {
            "energy": 0.1,
            "pitch_variation": 0.5,
            "speech_rate": 0.5,
            "pause_weight": 0.5,
        }
        raw = {"pause_before_sec": 0.5}
        label = generate_delivery_label(normalized, raw)
        assert "quiet" in label

    def test_energetic_label(self) -> None:
        """Test label for energetic segment."""
        normalized = {
            "energy": 0.9,
            "pitch_variation": 0.5,
            "speech_rate": 0.5,
            "pause_weight": 0.5,
        }
        raw = {"pause_before_sec": 0.0}
        label = generate_delivery_label(normalized, raw)
        assert "energetic" in label

    def test_long_pause_label(self) -> None:
        """Test label with long pause."""
        normalized = {
            "energy": 0.5,
            "pitch_variation": 0.5,
            "speech_rate": 0.5,
            "pause_weight": 0.5,
        }
        raw = {"pause_before_sec": 3.0}
        label = generate_delivery_label(normalized, raw)
        assert "3.0s pause" in label


class TestAnalyzeAllInterviews:
    def test_empty_manifest(self, tmp_path: Path) -> None:
        """Test analysis with no interviews."""
        from plotline.analyze.delivery import analyze_all_interviews

        manifest = {"interviews": []}
        results = analyze_all_interviews(tmp_path, manifest)

        assert results["analyzed"] == 0
        assert results["skipped"] == 0
        assert results["failed"] == 0

    def test_not_transcribed_skipped(self, tmp_path: Path) -> None:
        """Test that non-transcribed interviews are skipped."""
        from plotline.analyze.delivery import analyze_all_interviews

        manifest = {
            "interviews": [
                {
                    "id": "interview_001",
                    "stages": {"transcribed": False, "analyzed": False},
                }
            ]
        }

        results = analyze_all_interviews(tmp_path, manifest)

        assert results["analyzed"] == 0
        assert results["skipped"] == 1
