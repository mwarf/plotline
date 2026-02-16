"""
plotline.config - YAML config loading, profile merging, validation.

Handles loading plotline.yaml from project directory, applying profile
defaults, and validating all parameters.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class DeliveryWeights(BaseModel):
    """Weights for composite delivery score calculation."""

    energy: float = Field(default=0.15, ge=0.0, le=1.0)
    pitch_variation: float = Field(default=0.15, ge=0.0, le=1.0)
    speech_rate: float = Field(default=0.25, ge=0.0, le=1.0)
    pause_weight: float = Field(default=0.30, ge=0.0, le=1.0)
    spectral_brightness: float = Field(default=0.10, ge=0.0, le=1.0)
    voice_texture: float = Field(default=0.05, ge=0.0, le=1.0)

    @field_validator(
        "energy",
        "pitch_variation",
        "speech_rate",
        "pause_weight",
        "spectral_brightness",
        "voice_texture",
    )
    @classmethod
    def validate_weight(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Weight must be between 0.0 and 1.0")
        return v


class PlotlineConfig(BaseModel):
    """Resolved configuration for a Plotline project."""

    project_name: str = "untitled"
    project_profile: str = "documentary"

    privacy_mode: str = "local"
    llm_backend: str = "ollama"
    llm_model: str = "llama3.1:70b-instruct-q4_K_M"

    whisper_backend: str = "mlx"
    whisper_model: str = "medium"
    whisper_language: str | None = None

    segment_min_duration: float = Field(default=3.0, gt=0.0)
    segment_max_duration: float = Field(default=90.0, gt=0.0)

    target_duration_seconds: int = Field(default=600, gt=0)
    handle_padding_frames: int = Field(default=12, ge=0)

    delivery_weights: DeliveryWeights = Field(default_factory=DeliveryWeights)

    cultural_flags: bool = False
    pitch_backend: str = "librosa"

    profile_config_path: Path | None = None

    @field_validator("privacy_mode")
    @classmethod
    def validate_privacy_mode(cls, v: str) -> str:
        valid = {"local", "hybrid"}
        if v not in valid:
            raise ValueError(f"privacy_mode must be one of: {valid}")
        return v

    @field_validator("llm_backend")
    @classmethod
    def validate_llm_backend(cls, v: str) -> str:
        valid = {"ollama", "lmstudio", "claude", "openai"}
        if v not in valid:
            raise ValueError(f"llm_backend must be one of: {valid}")
        return v

    @field_validator("whisper_backend")
    @classmethod
    def validate_whisper_backend(cls, v: str) -> str:
        valid = {"mlx", "cpp", "faster"}
        if v not in valid:
            raise ValueError(f"whisper_backend must be one of: {valid}")
        return v

    @field_validator("project_profile")
    @classmethod
    def validate_profile(cls, v: str) -> str:
        valid = {"documentary", "brand", "commercial-doc"}
        if v not in valid:
            raise ValueError(f"profile must be one of: {valid}")
        return v


BUILTIN_PROFILES: dict[str, dict[str, Any]] = {
    "documentary": {
        "delivery_weights": {
            "energy": 0.15,
            "pitch_variation": 0.15,
            "speech_rate": 0.25,
            "pause_weight": 0.30,
            "spectral_brightness": 0.10,
            "voice_texture": 0.05,
        },
        "target_duration_seconds": 600,
        "llm_model": "llama3.1:70b-instruct-q4_K_M",
        "cultural_flags": False,
    },
    "brand": {
        "delivery_weights": {
            "energy": 0.30,
            "pitch_variation": 0.10,
            "speech_rate": 0.15,
            "pause_weight": 0.10,
            "spectral_brightness": 0.20,
            "voice_texture": 0.15,
        },
        "target_duration_seconds": 180,
        "llm_model": "llama3.1:70b-instruct-q4_K_M",
        "cultural_flags": False,
    },
    "commercial-doc": {
        "delivery_weights": {
            "energy": 0.25,
            "pitch_variation": 0.12,
            "speech_rate": 0.20,
            "pause_weight": 0.20,
            "spectral_brightness": 0.15,
            "voice_texture": 0.08,
        },
        "target_duration_seconds": 300,
        "llm_model": "llama3.1:70b-instruct-q4_K_M",
        "cultural_flags": True,
    },
}


def load_profile(name: str, profiles_dir: Path | None = None) -> dict[str, Any]:
    """Load a profile by name, checking custom profiles first."""
    if profiles_dir and profiles_dir.exists():
        profile_file = profiles_dir / f"{name}.yaml"
        if profile_file.exists():
            with open(profile_file) as f:
                return yaml.safe_load(f)
    if name in BUILTIN_PROFILES:
        return BUILTIN_PROFILES[name].copy()
    raise ValueError(f"Unknown profile: {name}")


def merge_config(project_config: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Merge project config with profile defaults. Project config takes precedence."""
    merged = profile.copy()
    for key, value in project_config.items():
        if key == "delivery_weights" and isinstance(value, dict):
            merged.setdefault("delivery_weights", {})
            merged["delivery_weights"].update(value)
        elif value is not None:
            merged[key] = value
    return merged


def load_config(project_dir: Path) -> PlotlineConfig:
    """Load and validate configuration from a project directory."""
    config_file = project_dir / "plotline.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"No plotline.yaml found in {project_dir}")

    with open(config_file) as f:
        raw_config = yaml.safe_load(f) or {}

    profile_name = raw_config.get("project_profile", "documentary")
    profiles_dir = project_dir / "profiles"
    profile = load_profile(profile_name, profiles_dir if profiles_dir.exists() else None)

    if "inherits" in profile:
        parent = load_profile(profile["inherits"], profiles_dir if profiles_dir.exists() else None)
        profile = merge_config(profile, parent)

    merged = merge_config(raw_config, profile)
    merged["profile_config_path"] = config_file

    return PlotlineConfig(**merged)


def create_default_config(project_name: str, profile: str = "documentary") -> dict[str, Any]:
    """Create a default config for a new project."""
    defaults = {
        "project_name": project_name,
        "project_profile": profile,
        "privacy_mode": "local",
        "llm_backend": "ollama",
        "whisper_backend": "mlx",
        "whisper_model": "medium",
    }
    if profile in BUILTIN_PROFILES:
        defaults = merge_config(defaults, BUILTIN_PROFILES[profile])
    return defaults


def write_config(config: dict[str, Any], path: Path) -> None:
    """Write configuration to a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
