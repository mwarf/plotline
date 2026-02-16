# Changelog

All notable changes to Plotline will be documented in this file.

## [0.1.0] - 2025-02-15

Initial release with complete pipeline functionality.

### Added

#### Core Pipeline

- Audio extraction from video files (FFmpeg)
- Whisper transcription with mlx-whisper and faster-whisper backends
- Emotional delivery analysis using librosa (energy, pitch, speech rate, pauses)
- Segment enrichment merging transcript + delivery data
- LLM theme extraction, synthesis, and narrative arc construction
- EDL and FCPXML export for DaVinci Resolve/Premiere Pro

#### CLI Commands

- `plotline init` — Create new project
- `plotline add` — Add video files
- `plotline extract` — Extract audio
- `plotline transcribe` — Transcribe audio
- `plotline analyze` — Analyze delivery
- `plotline enrich` — Merge data
- `plotline themes` — LLM theme extraction
- `plotline synthesize` — Cross-interview synthesis
- `plotline arc` — Build narrative arc
- `plotline run` — Run full pipeline
- `plotline export` — Export EDL/FCPXML
- `plotline status` — Pipeline dashboard
- `plotline review` — Selection review
- `plotline report` — Generate reports
- `plotline brief` — Attach creative brief
- `plotline doctor` — Check dependencies
- `plotline validate` — Validate data

#### Reports

- Dashboard report (pipeline status)
- Review report (approve/reject interface)
- Summary report (executive summary)

#### Configuration

- Three project profiles: documentary, brand, commercial-doc
- Customizable delivery weights
- LLM backend selection (Ollama, LM Studio, Claude, OpenAI)
- Privacy mode (local/hybrid)

#### Error Handling

- FFmpeg/FFprobe dependency checks
- Disk space validation
- No audio track detection
- Interview duration warnings
- LLM retry logic with backoff
- JSON parsing with repair strategies

### Technical Details

- 111 tests passing
- Python 3.11+ support
- Type hints throughout
- Atomic JSON writes
- Jinja2-based HTML reports
