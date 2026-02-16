"""
plotline.extract - Audio extraction from video files.

Pipeline Stage 1: Extract audio from video, producing two versions:
- 16kHz mono WAV for transcription (Whisper)
- Original sample rate WAV for delivery analysis (librosa)
"""

from __future__ import annotations
