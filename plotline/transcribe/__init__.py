"""
plotline.transcribe - Whisper transcription engine.

Pipeline Stage 2: Transcribe audio using mlx-whisper (primary) or
whisper.cpp (fallback). Produces segment-level transcripts with
word-level timestamps.
"""

from __future__ import annotations
