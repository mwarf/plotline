# Changelog

All notable changes to Plotline will be documented in this file.

## [0.2.0] - 2026-02-17

Polish & Gaps release — cross-interview comparison, new reports, and cultural sensitivity flagging.

### Added

#### Cross-Interview Comparison (`plotline compare`)

- Side-by-side best-take comparison across interviews for the same theme/message
- Cross-interview score re-normalization (not per-interview min-max)
- Interactive HTML report with candidate cards, audio playback, sort/filter
- `plotline/compare.py` — core comparison logic
- `plotline/reports/compare.py` — report data builder
- `plotline/reports/templates/compare.html` — comparison report template

#### Transcript Report (`plotline report transcript`)

- Per-interview HTML report with delivery waveform timeline
- Sticky horizontal timeline header with scrolling segment cards
- Theme pills on segments, keyboard navigation, audio playback
- Per-segment delivery metrics (energy, pitch variation, speech rate, pause weight)
- `plotline/reports/transcript.py` — transcript report builder
- `plotline/reports/templates/transcript.html` — transcript report template

#### Coverage Matrix (`plotline report coverage`)

- Brief coverage analysis with three tiers: strong, weak, gap
- Message-by-theme grid visualization with per-message segment cards
- Progress bar and gap identification
- Auto-generated message IDs via `normalize_key_messages()` in `plotline/brief.py`
- `plotline/reports/coverage.py` — coverage analysis module
- `plotline/reports/templates/coverage.html` — coverage report template

#### Cultural Sensitivity Flagging (`plotline flags`)

- Optional LLM pass (Pass 4) to flag culturally sensitive content
- Flags segments referencing ceremonies, sacred places, spiritual teachings, naming/death protocols
- Updates `selections.json` in-place with `flagged`/`flag_reason` fields
- Auto-runs after arc in `plotline run` when `cultural_flags: true` in config
- `--force` flag to run even when disabled in config
- Clean slate reset on re-run (previous flags cleared before re-flagging)
- `plotline/llm/flags.py` — cultural flags LLM module

#### CLI Updates

- `plotline report transcript` — new report type
- `plotline report coverage` — new report type
- `plotline flags` — new standalone command
- `plotline run` — conditional flags step after arc when enabled
- `plotline compare` — fully implemented (was a stub)

### Technical Details

- 152 tests passing (up from 111)
- 16 tests for compare, 21 for transcript report, 22 for coverage matrix, 15 for cultural flags
- `commercial-doc` profile enables `cultural_flags` by default

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
