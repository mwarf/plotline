"""
plotline.diarize - Speaker diarization module.

Optional module for identifying speakers in interview audio using pyannote.audio.
"""

from __future__ import annotations

from plotline.diarize.align import assign_speakers_to_words
from plotline.diarize.engine import diarize_audio, diarize_all_interviews
from plotline.diarize.speakers import (
    SpeakerConfig,
    generate_default_colors,
    load_speaker_config,
    save_speaker_config,
)

__all__ = [
    "diarize_audio",
    "diarize_all_interviews",
    "assign_speakers_to_words",
    "SpeakerConfig",
    "load_speaker_config",
    "save_speaker_config",
    "generate_default_colors",
]
