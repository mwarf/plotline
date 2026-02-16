"""Tests for plotline.config module."""

from __future__ import annotations

from pathlib import Path

import pytest

from plotline.config import (
    DeliveryWeights,
    PlotlineConfig,
    create_default_config,
    load_config,
    load_profile,
    merge_config,
    write_config,
)


class TestDeliveryWeights:
    def test_default_weights_sum_to_one(self) -> None:
        weights = DeliveryWeights()
        total = (
            weights.energy
            + weights.pitch_variation
            + weights.speech_rate
            + weights.pause_weight
            + weights.spectral_brightness
            + weights.voice_texture
        )
        assert abs(total - 1.0) < 0.01

    def test_custom_weights(self) -> None:
        weights = DeliveryWeights(energy=0.5, pause_weight=0.5)
        assert weights.energy == 0.5
        assert weights.pause_weight == 0.5

    def test_invalid_weight_raises(self) -> None:
        with pytest.raises(ValueError):
            DeliveryWeights(energy=-0.1)


class TestPlotlineConfig:
    def test_default_config(self) -> None:
        config = PlotlineConfig()
        assert config.project_name == "untitled"
        assert config.project_profile == "documentary"
        assert config.privacy_mode == "local"

    def test_invalid_privacy_mode_raises(self) -> None:
        with pytest.raises(ValueError):
            PlotlineConfig(privacy_mode="invalid")

    def test_invalid_llm_backend_raises(self) -> None:
        with pytest.raises(ValueError):
            PlotlineConfig(llm_backend="invalid")

    def test_invalid_profile_raises(self) -> None:
        with pytest.raises(ValueError):
            PlotlineConfig(project_profile="invalid")


class TestLoadProfile:
    def test_load_documentary_profile(self) -> None:
        profile = load_profile("documentary")
        assert "delivery_weights" in profile
        assert profile["delivery_weights"]["pause_weight"] == 0.30

    def test_load_brand_profile(self) -> None:
        profile = load_profile("brand")
        assert profile["delivery_weights"]["energy"] == 0.30

    def test_load_nonexistent_profile_raises(self) -> None:
        with pytest.raises(ValueError):
            load_profile("nonexistent")


class TestMergeConfig:
    def test_merge_keeps_project_overrides(self) -> None:
        project = {"project_name": "my-project", "target_duration_seconds": 300}
        profile = {"target_duration_seconds": 600, "privacy_mode": "local"}
        merged = merge_config(project, profile)
        assert merged["project_name"] == "my-project"
        assert merged["target_duration_seconds"] == 300
        assert merged["privacy_mode"] == "local"

    def test_merge_delivery_weights(self) -> None:
        project = {"delivery_weights": {"energy": 0.5}}
        profile = {"delivery_weights": {"energy": 0.15, "pause_weight": 0.30}}
        merged = merge_config(project, profile)
        assert merged["delivery_weights"]["energy"] == 0.5
        assert merged["delivery_weights"]["pause_weight"] == 0.30


class TestCreateDefaultConfig:
    def test_create_documentary_config(self) -> None:
        config = create_default_config("test", "documentary")
        assert config["project_name"] == "test"
        assert config["project_profile"] == "documentary"

    def test_create_brand_config(self) -> None:
        config = create_default_config("test", "brand")
        assert config["project_profile"] == "brand"


class TestLoadConfig:
    def test_load_config_from_file(self, tmp_project: Path) -> None:
        config_data = create_default_config("test-project", "documentary")
        write_config(config_data, tmp_project / "plotline.yaml")
        config = load_config(tmp_project)
        assert config.project_name == "test-project"
        assert config.project_profile == "documentary"

    def test_load_missing_config_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path)
