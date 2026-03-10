"""
plotline.transcribe - Whisper transcription engine.

Pipeline Stage 2: Transcribe audio using faster-whisper (cross-platform default) or
mlx-whisper (Apple Silicon optional). Produces segment-level transcripts with
word-level timestamps.
"""

from __future__ import annotations
