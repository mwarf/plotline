# Changelog

All notable changes to Plotline will be documented in this file.

## [0.3.7] - 2026-03-09

Export pipeline and report template correctness fixes, plus full Windows/Linux PC compatibility.

### Changed

#### Cross-Platform Compatibility

- **faster-whisper is now the default Whisper backend** on all platforms. mlx-whisper has moved to an optional macOS extra: `pip install plotline[macos]`
- **Platform-specific backend auto-selection**: `mlx` on macOS Apple Silicon, `faster-whisper` on Linux and Windows
- **Windows editor fallback**: the config editor now falls back to `notepad` on Windows (previously only `nano` was tried as a fallback)
- **FFmpeg error messages** now include Windows install instructions (`winget install ffmpeg` / `choco install ffmpeg`)
- **Documentation**: added Windows/Linux setup instructions across `README.md`, `getting-started.md`, and `FAQ.md`

### Fixed

#### Export Pipeline (Audit Fixes 1-5)

- **merge.py**: Propagate `delivery.raw` into enriched segments so `pause_before_sec`/`pause_after_sec` flow through to selections.json — smart handles were dead code without this
- **fcpxml.py**: Add `_xa()` XML-escape helper and apply to all 8 dynamic attribute locations (theme names, speaker names, filenames, notes) — unescaped `&`, `"`, `<`, `>` produced malformed FCPXML
- **edl.py, fcpxml.py**: Copy selection dicts before mutating with `user_notes` to avoid in-place source mutation
- **edl.py, fcpxml.py**: Correct zero-pause handle logic — `pause==0` means contiguous speech with no gap, so handle must be `0.0` (was incorrectly falling through to default)
- **edl.py**: Raise `FileNotFoundError` when `segments_dir` is missing before globbing for alternates

#### Report Templates (Audit Fixes 1-6 + Performance)

- **compare.py**: Normalize `key_messages` to `list[str]` before template — prevents dict repr rendering when brief has `{id, text}` objects
- **summary.html**: Add `stat-card`/`stat-value`/`stat-label` CSS — cards were unstyled
- **review.html**: Replace `{{ project_name }}` in JS with `reportData.project_name` — prevents localStorage key corruption from HTML entity escaping
- **base.html**: Add `ml-1`, `ml-2`, `mr-1`, `mr-2` margin utility classes
- **coverage.html**: Fix `gap.get('description', gap)` fallback to `''` — prevents dict repr if neither key exists
- **review.html**: Move `focusSegment(0)` into `DOMContentLoaded` handler — prevents brief segment-0 highlight flash on deep-link navigation

### Performance

- **themes.py + themes.html**: Pass `segment_lookup` dict to template, replace O(n²) `selectattr` loop with O(1) dict lookup

### Tests

- **458 passed, 0 failed, 2 skipped** — 11 new tests (up from 447)
  - `test_compare_report.py`: 5 integration tests for `generate_compare_report()`
  - `test_themes_report.py`: 6 integration tests for `generate_themes_report()`

## [0.3.6] - 2026-03-08

Enhanced EDL/FCPXML export for professional NLE workflows.

### Added

#### Export Improvements

- **Smart Handles**: Handles now use `pause_before_sec` and `pause_after_sec` data to automatically reduce padding when natural pauses are short. A segment with 0.2s pause before gets a 0.16s handle instead of the default 0.5s, preventing dialogue overlap.
- **Chapter Markers**: FCPXML now includes chapter markers at role transitions (hook→body→climax→resolution), making it easy to navigate the narrative structure in Final Cut Pro.
- **Alternates Export**: New `--alternates` flag exports all alternate candidates as a secondary EDL timeline, allowing editors to compare takes directly in their NLE.
- **Full Theme Export**: FCPXML now exports all themes as keywords (previously truncated to 3).

#### Metadata Export

- **User Notes**: Notes added during review are now included in EDL COMMENT lines and FCPXML marker notes.
- **Pause Data Propagation**: `pause_before_sec` and `pause_after_sec` are now stored in selections.json for smart handle calculation at export time.

### Changed

- **arc.py**: `create_selections_from_arc()` now includes delivery raw metrics (pause_before_sec, pause_after_sec) in selections

### Tests

- **447 passed, 0 failed, 2 skipped** — 8 new tests for smart handles, user_notes export, chapter markers, and all-themes export

## [0.3.5] - 2026-03-08

Full pipeline audit — fixed bugs across all 5 stages (Prep, Extract, Transcribe, Analyze, Enrich, LLM, Reports, Export).

### Fixed

#### Stage 1: Prep & Config

- **config.py**: Fixed global profile mutation — `load_profile()` now uses `copy.deepcopy()` instead of shallow `.copy()` to prevent corruption of `BUILTIN_PROFILES`
- **brief.py**: Fixed markdown regex — `(?m)^#{1,3}\s+` now correctly matches headings on line 1
- **project.py**: Removed duplicate `read_json`/`write_json` functions, now imports from `plotline.io` (DRY)

#### Stage 2: Extract & Transcribe

- **engine.py**: Fixed confidence normalization formula — `max(0.0, min(1.0, 1 + confidence))` instead of misleading `(confidence + 1) / 1`
- **engine.py**: Fixed import to use `plotline.io.write_json` instead of `plotline.project`
- **audio.py**: Added cleanup on partial extraction failure — removes `audio_16k.wav` if `audio_full.wav` extraction fails
- **engine.py**: Simplified segment ID generation — already using enumerate correctly

#### Stage 3: Analyze & Enrich

- **delivery.py**: Fixed import to use `plotline.io`
- **scoring.py**: Fixed import to use `plotline.io`
- **merge.py**: Fixed import to use `plotline.io`
- **merge.py**: Added KeyError protection — segment dictionaries now filter for `segment_id` presence

#### Stage 4: LLM Passes

- **themes.py**: Fixed import to use `plotline.io`
- **synthesis.py**: Fixed import to use `plotline.io`
- **arc.py**: Fixed import to use `plotline.io`
- **arc.py**: Added KeyError protection in `build_narrative_arc()` and `create_selections_from_arc()`
- **flags.py**: Fixed import to use `plotline.io`
- **flags.py**: Added KeyError protection — `segment_by_id` now filters for valid segment IDs

#### Stage 5: Reports & Export

- **All 9 report/export modules**: Fixed imports to use `plotline.io` instead of `plotline.project`
  - `reports/compare.py`, `reports/coverage.py`, `reports/dashboard.py`, `reports/review.py`
  - `reports/summary.py`, `reports/themes.py`, `reports/transcript.py`
  - `export/edl.py`, `export/fcpxml.py`

#### Stage 6: HTML Templates

- **dashboard.py**: Removed stale `"reviewed"` from `stage_order` — this stage was removed from the pipeline in v0.3.4 but still rendered as a permanently-pending badge
- **dashboard.html**: Removed `'reviewed'` from JS `stageCommands`/`stageOrder`/`stageLabels` so the "Run Next Stage" button reaches the correct terminal state
- **review.py**: Guarded `s["segment_id"]` with `.get()` and `None` filter to prevent `KeyError` on corrupt approvals.json entries
- **review.py**: Removed `cultural_flag_count` from `reviewed_count` — cultural flags are AI annotations, not user review actions, and were double-counting flagged segments in progress bar
- **review.html**: Same double-count fix in `updateSummary()` JS function
- **themes.py**: Replaced hardcoded `strength: 0.8` with normalized `source_count / max_source_count` (floor 0.3) so the strength bar differentiates themes

### Architecture Improvements

- **DRY Compliance**: All modules now import I/O functions from central `plotline/io.py`
- **KeyError Protection**: All segment dictionary constructions now validate key existence
- **Atomic Writes**: Consistent use of `tempfile.NamedTemporaryFile` for crash-safe writes

### Test Results

- **439 passed, 0 failed, 2 skipped** — all tests continue to pass

## [0.3.4] - 2026-03-08

CLI audit — fixed 17 bugs identified in comprehensive cli.py review.

### Fixed

#### Pipeline Stage Logic

- **_suggest_next_stage**: Replaced buggy `f"{stage}ed"` string concatenation (produced "analyzeed") with explicit stage key mapping dictionary
- **_suggest_next_stage**: Fixed incorrect checks for project-level stages (synthesize, arc) — these don't have per-interview stage keys
- **_has_completed_llm_stages**: Removed check for non-existent `synthesized` key in interview stages
- **run_pipeline**: Added `diarize` to valid `--from` stages list (was missing, preventing resume from diarize)
- **interview stages**: Removed `reviewed` from default stages dict — it was never set to True, inflating progress percentages

#### Speaker Management

- **manage_speakers color generation**: Fixed near-black invisible colors (`f"#{idx % 10:06X}"` → `#000000`-`#000009`) by using `DEFAULT_COLORS` palette
- **manage_speakers variable shadowing**: Renamed loop variable `speaker_id` to `spk_id` to avoid shadowing function parameter
- **format_duration import shadowing**: Renamed to `format_speaker_duration` to avoid shadowing top-level utils function
- **Removed unused import**: `SpeakerConfig` was imported but never used

#### Brief Staleness Detection

- **_check_brief_staleness**: Fixed timezone mismatch — `datetime.fromtimestamp()` produces naive datetime but `fromisoformat()` may produce aware datetime
- **_check_brief_staleness**: Added `TypeError` catch in addition to `ValueError` for robustness

#### Approvals System

- **approve/reject/unapprove commands**: Added segment_id validation — commands now error if segment doesn't exist in selections
- **show_approvals**: Added KeyError protection for `s["segment_id"]` access in approval_map construction

#### Code Quality

- **extract_themes**: Removed unused `interview` and `all_interviews` parameters
- **run_pipeline**: Removed unused `excluded` variable after diarization
- **_build_status_json**: Now copies stages dict to avoid reference issues when modifying
- **diagnose_project**: Fixed `Path('')` truthy check — empty path string now properly checks if source_file exists
- **DRY violation**: Extracted `_generate_all_reports()` helper to eliminate duplicated report generation code in `report all` and `run_pipeline`

### Test Results

- **439 passed, 0 failed, 2 skipped** — all existing tests continue to pass

## [0.3.3] - 2026-03-07

Report audit — fixed 8 critical/high-impact bugs across all 7 report stages.

### Fixed

#### Cross-Report: Delivery Filter Mismatch
- **CRITICAL**: "High Score" / "High" delivery filter buttons never matched any segment — `get_delivery_class()` returns `"filled"` but filters checked for `"high"`. Fixed in transcript.html, review.html, and coverage.html CSS class `.score.high` → `.score.filled`

#### Coverage Report
- **CRITICAL**: Segment pill links used `seg.id` (undefined) instead of `seg.segment_id` — all "Strong matches" and "Theme-level matches" links navigated to empty anchors
- **CRITICAL**: Coverage matrix weak-cell detection compared `msg_id` against `aligned_themes` (theme IDs) — namespaces never overlap, so weak cells were never shown. Restructured guard to check segment theme intersection directly
- Fixed 2 pre-existing test failures: `test_missing_brief_raises` and `test_missing_selections_raises` expected `FileNotFoundError` but `generate_coverage()` now renders graceful fallback HTML. Tests updated to verify the rendered "No Brief Attached" / "No Selections Found" content

#### Compare Report
- **CRITICAL**: `message_filter` logic in `compare.py` used sequential `if/continue` (AND semantics) instead of OR — groups matching on `brief_message` but not `topic` were incorrectly dropped

#### Themes Report
- **CRITICAL**: Double-escaping via `| e` filter on top of Jinja2 autoescape broke theme sidebar selection and theme pill clicks for names containing `&`, `<`, `>`, `"`. Replaced inline string interpolation with `data-*` attribute reads (`this.dataset.theme`, `this.dataset.themeName`)

#### Review Report
- `interview_id` was omitted from segment data dict — EDL export derived it via fragile `segData.id.split('_seg_')`. Added explicit `interview_id` field; JS now uses it with split as fallback

#### Summary Report
- `{{ message }}` rendered dict repr (`{'id': 'msg_001', 'text': '...'}`) instead of message text. Fixed generator to extract `.text` from key message dicts before passing to template

### Test Results
- **437 passed, 0 failed, 2 skipped** — the 2 pre-existing failures are now fixed, bringing the suite to 100% green

## [0.3.2] - 2026-03-07

Client-side EDL generator audit — fixed 5 bugs to achieve parity with the Python EDL generator.

### Fixed

#### Client-Side EDL (review.html)

- `secondsToDFTimecode()` used `29.97` instead of exact `30000/1001` for frame counting — caused 1-frame drift at certain timecode boundaries
- Timecode offset parser used NDF math (`frames / fps`) for drop-frame timecodes — ported proper SMPTE `dfTimecodeToSeconds()` formula to JavaScript, matching the Python fix from v0.3.1
- `duration_seconds` fallback used JavaScript `||` (falsy check) instead of null check — handle padding was lost when `duration_seconds` was `0` or absent
- FPS selection took last interview's frame rate instead of most common — ported frequency-counting logic to match Python `generate_edl()`
- No mixed-FPS warning comment in client-side EDL export — added `* WARNING: Mixed frame rates detected (...)` parity with Python

### Added

- `dfTimecodeToSeconds()` and `timecodeToSeconds()` JavaScript functions in review.html for accurate timecode-to-seconds conversion
- 8 new EDL compliance tests in `TestEDLCompliance` class:
  - CMX 3600 field width validation (event number, reel, track, timecodes)
  - Mixed-FPS warning presence and absence
  - Duration clamping with and without `duration_seconds`
  - Drop-frame timecode offset round-trip accuracy
  - Record timecode contiguity between events
  - Most-common FPS selection for record track
- Total tests: 435 passed (up from 427)

## [0.3.1] - 2026-03-06

Multilingual support, timecode accuracy, and report UI fixes.

### Added

#### Language Support

- Automatic language detection from Whisper — detected language is stored on each interview in the manifest and carried through the entire pipeline
- Bilingual LLM prompt injection: English instructions with output in the detected language (Spanish, French, Portuguese, and 20 other languages)
- `build_language_instruction()` and `detect_project_language()` utilities in `plotline/llm/templates.py`
- All LLM pass functions (`themes`, `synthesize`, `arc`, `flags`) accept a `language` parameter; CLI commands auto-detect from the manifest
- All 5 prompt templates include conditional `{% if LANGUAGE_INSTRUCTION %}` blocks
- English projects incur zero overhead — no instruction is injected
- 24 new language support tests in `tests/test_language_support.py`

#### Export Timecode Tests

- Drop-frame round-trip tests at 1-hour and 2-hour boundaries
- Drop-frame 10-minute boundary test (where skip pattern matters)
- Source timecode offset accuracy test
- NDF 23.976fps frame-accuracy test
- 7 new tests in `tests/test_export.py` (420 total tests)

### Fixed

#### Export / Timecode

- **CRITICAL**: `df_timecode_to_seconds()` was 108 frames (3.6 seconds) off at timecodes >= 1 hour — rewrote with correct SMPTE formula using total minutes across all hours and `1001/30000` conversion
- `seconds_to_df_timecode()` used `29.97` instead of exact `30000/1001`, causing 1-frame drift at ~5 hours
- FCPXML sequence duration used raw segment durations without handles while spine clips used padded durations — restructured to use cumulative padded total
- Mixed FPS projects used non-deterministic `set.pop()` for record track fps — now uses most common fps via `max(fps_counts, key=...)`
- Missing `duration_seconds` in interview metadata silently dropped trailing handles — now only clamps when the field is actually present
- CLI exported to `exports/` (plural) but `Project.export_dir` is `export/` (singular) — fixed to use `export/`
- `probe_video()` only checked video stream timecode tags — now falls back to format-level tags (MXF, etc.)
- `test_generate_edl_multiple_selections` expected 2 event lines but EDL correctly produces V+A1+A2 per event — fixed test expectations

#### Report UI

- **Play buttons broken by apostrophes**: Inline `onclick` handlers with single-quoted JS string literals broke on any segment text containing `'` (extremely common in speech) — moved to `data-*` attributes with delegated click handlers
- **No play button on review page**: Audio was only accessible via undiscoverable spacebar shortcut — added visible "Play" button to segment action bar
- **Wrong audio after drag-drop**: `focusSegment()` indexed into the original `reportData.segments[]` array after DOM reorder — now reads audio path from the card's `data-audio` attribute
- **CSS class mismatch**: `transcript.html` used `.segment-score.high` but `get_delivery_class()` returns `"filled"` — changed to `.segment-score.filled` (matching `themes.html`)
- **Duplicate HTML in coverage template**: The `{% else %}` branch had a duplicate `header-meta`/`header-info` block with orphaned `</div>` tags — removed
- **Silent audio errors**: `audio.play().catch(() => {})` swallowed all errors — now displays error message in the player info bar
- **Always-truthy audio.src**: Review page spacebar handler checked `audio.src` which is always truthy after first use — replaced with explicit `hasAudioLoaded` boolean
- **Spacebar target**: Transcript page spacebar triggered the first `.btn` (could be any button) — now specifically targets `.play-btn`

#### Pipeline Plumbing

- `whisper_language` config field was dead code — `transcribe` CLI command now reads config and falls back to `config.whisper_language/model/backend`; `run` command passes config values through
- Detected language was dropped during enrichment — `merge.py` now preserves the `language` field

### Technical Details

- 33 new tests (24 language + 7 timecode + 2 test fixes), 420 total passing
- 2 pre-existing failures in `test_coverage_report.py` remain (unrelated)
- Zero regressions — all existing tests continue to pass

## [0.3.0] - 2026-03-03

Speaker Intelligence release — pyannote.audio diarization integration.

### Added

#### Speaker Diarization (`plotline diarize`)

- Identify and label different speakers within interview audio using pyannote.audio
- Word-level speaker assignment via midpoint overlap with diarization segments
- Segment-level speaker via majority vote across words
- Optional install: `pip install plotline[diarization]`
- HuggingFace token management (env var, cache file, interactive prompt)
- Automatic `speakers.yaml` generation with default names and colors
- `plotline speakers` command to list and manage speaker configurations
- Speaker labels propagate through entire pipeline:
  - Enriched segments include `speaker` field
  - LLM prompts include speaker context for better arc construction
  - Review and transcript reports show color-coded speaker badges
  - EDL exports include `* SPEAKER:` comments
  - FCPXML exports include speaker keywords and clip name prefixes

#### Configuration

- `diarization_enabled: bool` (default: false) — Enable diarization in `plotline run`
- `diarization_model: str` — pyannote model name (default: pyannote/speaker-diarization-3.1)
- `diarization_num_speakers: int | None` — Exact speaker count if known
- `diarization_min_speakers: int` — Minimum speakers (default: 2)
- `diarization_max_speakers: int` — Maximum speakers (default: 5)

#### CLI Commands

- `plotline diarize` — Run speaker diarization on transcribed interviews
- `plotline speakers` — List detected speakers and edit `speakers.yaml`

### Technical Details

- 67 new tests for diarization feature (387 total tests passing)
- `plotline/diarize/` module with engine, align, and speakers submodules
- Diarization is fully optional — not a pipeline gate
- Existing projects without diarization continue to work unchanged

## [0.2.1] - 2026-02-27

Reporting Polish & Theme Explorer released — interactive theme navigation and reporting suite bug fixes.

### Added

#### Theme Explorer Report (`plotline report themes`)

- Interactive sidebar for theme navigation with segment counts and strength indicators
- Automated multi-theme intersection detection with visual badges and notes
- Client-side sorting (Delivery Score, Chronological, Theme Count) and search
- Cross-interview unified theme views (via `synthesis.json`) or per-interview fallback
- `plotline/reports/themes.py` — generator module
- `plotline/reports/templates/themes.html` — interactive report template

### Fixed

- **Review Report**: Corrected approval/rejection counters and persistent state saving using `localStorage` (fixing `file://` protocol issues)
- **Compare Report**: Resolved uncaught `audio.play()` errors and fixed message filtering under the `file://` protocol
- **Summary Report**: Improved narrative arc visualization with expanded role mappings and distinct colors for 'climax' and 'resolution' segments
- **Dashboard**: Replaced hardcoded "Run Next Stage" button with dynamic logic based on actual pipeline progress per interview
- **General**: Improved audio playback robustness across all reporting templates

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
