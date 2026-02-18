# ARCHITECTURE.md — System Design & Data Schemas

## Pipeline Data Flow

```
VIDEO FILES
    │
    ▼
┌─────────────┐     ┌──────────────────┐
│ 1. Extract   │────▶│ audio_16k.wav    │  (16kHz mono for Whisper)
│   (FFmpeg)   │────▶│ audio_full.wav   │  (original SR for librosa)
│              │────▶│ interviews.json   │  (source metadata)
└─────────────┘     └──────────────────┘
    │
    ▼
┌─────────────┐     ┌──────────────────┐
│ 2. Transcribe│────▶│ transcript.json  │  (per interview)
│ (mlx-whisper)│     └──────────────────┘
└─────────────┘
    │
    ▼
┌─────────────┐     ┌──────────────────┐
│ 3. Analyze   │────▶│ delivery.json    │  (per interview)
│  (librosa)   │     └──────────────────┘
└─────────────┘
    │
    ▼
┌─────────────┐     ┌──────────────────┐
│ 4. Enrich    │────▶│ segments.json    │  (per interview — unified)
│  (merge)     │     └──────────────────┘
    │
    ▼
┌─────────────┐     ┌──────────────────┐
│ 5a. Themes   │────▶│ themes.json      │  (per interview)
│   (LLM)      │     └──────────────────┘
└─────────────┘
    │
    ▼
┌─────────────┐     ┌──────────────────┐
│ 5b. Synthesis│────▶│ synthesis.json   │  (project-wide)
│   (LLM)      │     └──────────────────┘
└─────────────┘
    │
    ▼
┌─────────────┐     ┌──────────────────┐
│ 5c. Arc      │────▶│ arc.json         │  (project-wide)
│   (LLM)      │────▶│ selections.json  │  (project-wide)
└─────────────┘     └──────────────────┘
    │
    ▼ (optional, if cultural_flags enabled)
┌─────────────┐     ┌──────────────────┐
│ 5d. Flags    │────▶│ selections.json  │  (updated in-place)
│   (LLM)      │     │  + flagged fields │
└─────────────┘     └──────────────────┘
    │
    ▼
┌─────────────┐     ┌──────────────────┐
│ 6. Review    │────▶│ approvals.json   │  (user decisions)
│  (HTML)      │     └──────────────────┘
└─────────────┘
    │
    ▼
┌─────────────┐     ┌──────────────────┐
│ 7. Export    │────▶│ selects.edl      │
│              │────▶│ selects.fcpxml   │
└─────────────┘     └──────────────────┘
```

## File Locations Within a Project

```
my-project/
├── plotline.yaml                          # Project config
├── interviews.json                        # Master manifest
├── brief.json                             # Parsed creative brief (if attached)
├── prompts/                               # Editable prompt templates
├── source/
│   ├── interview_001/
│   │   ├── audio_16k.wav
│   │   └── audio_full.wav
│   └── interview_002/
│       ├── audio_16k.wav
│       └── audio_full.wav
├── data/
│   ├── transcripts/
│   │   ├── interview_001.json
│   │   └── interview_002.json
│   ├── delivery/
│   │   ├── interview_001.json
│   │   └── interview_002.json
│   ├── segments/
│   │   ├── interview_001.json             # Enriched (transcript + delivery)
│   │   └── interview_002.json
│   ├── themes/
│   │   ├── interview_001.json
│   │   └── interview_002.json
│   ├── synthesis.json                     # Cross-interview (project-wide)
│   ├── arc.json                           # Narrative arc (project-wide)
│   └── selections.json                    # Selected segments (project-wide)
├── reports/
│   ├── dashboard.html
│   ├── transcript_001.html
│   ├── review.html
│   ├── summary.html
│   ├── compare.html
│   └── coverage.html
├── approvals.json                         # User review decisions
└── export/
    ├── plotline_selects.edl
    └── plotline_selects.fcpxml
```

---

## JSON Schemas

### interviews.json — Project Manifest

The master record of all interviews and their processing state.

```json
{
  "project_name": "elder-series",
  "created": "2026-02-15T10:30:00",
  "profile": "documentary",
  "interviews": [
    {
      "id": "interview_001",
      "source_file": "/path/to/original/Elder_Margaret.mov",
      "filename": "Elder_Margaret.mov",
      "file_hash": "sha256:abc123...",
      "duration_seconds": 3420.5,
      "frame_rate": 23.976,
      "start_timecode": "01:00:00:00",
      "resolution": "3840x2160",
      "codec": "prores",
      "sample_rate": 48000,
      "audio_16k_path": "source/interview_001/audio_16k.wav",
      "audio_full_path": "source/interview_001/audio_full.wav",
      "stages": {
        "extracted": true,
        "transcribed": true,
        "analyzed": false,
        "enriched": false,
        "themes": false,
        "reviewed": false
      }
    }
  ]
}
```

**Rules:**
- `id` is the canonical reference for this interview across all other files
- `file_hash` detects if source has changed since extraction
- `start_timecode` can be `null` if camera didn't embed one (default to `00:00:00:00`)
- `frame_rate` is critical for EDL/FCPXML export — must be exact (23.976, not 24)
- `stages` tracks pipeline completion — each stage checks this before running

---

### transcript.json — Per-Interview Transcript

```json
{
  "interview_id": "interview_001",
  "model": "medium",
  "language": "en",
  "transcribed_at": "2026-02-15T11:00:00",
  "duration_seconds": 3420.5,
  "segments": [
    {
      "segment_id": "interview_001_seg_001",
      "start": 2.34,
      "end": 15.67,
      "text": "When I was young, my grandmother would take us to the river every morning before the sun came up.",
      "confidence": 0.94,
      "corrected": false,
      "words": [
        { "word": "When", "start": 2.34, "end": 2.56 },
        { "word": "I", "start": 2.58, "end": 2.64 },
        { "word": "was", "start": 2.66, "end": 2.82 },
        { "word": "young,", "start": 2.84, "end": 3.21 }
      ]
    }
  ]
}
```

**Rules:**
- `segment_id` format: `{interview_id}_seg_{NNN}` — globally unique across the project
- `start` and `end` are float seconds from the beginning of the audio file
- `words[]` provides word-level timestamps for precise trim points in export
- `confidence` is Whisper's average confidence for the segment (0-1)
- `corrected` is set to `true` when user manually edits the text
- Segments must be sorted by `start` time
- Segments must not overlap
- Gap between consecutive segments represents silence/pause

---

### delivery.json — Per-Interview Delivery Analysis

```json
{
  "interview_id": "interview_001",
  "analyzed_at": "2026-02-15T11:15:00",
  "segments": [
    {
      "segment_id": "interview_001_seg_001",
      "raw": {
        "rms_energy": 0.0234,
        "pitch_mean_hz": 185.4,
        "pitch_std_hz": 42.1,
        "pitch_contour": [180.2, 183.5, 190.1, 178.3],
        "speech_rate_wpm": 128.5,
        "pause_before_sec": 0.0,
        "pause_after_sec": 1.2,
        "spectral_centroid_mean": 1842.3,
        "zero_crossing_rate": 0.067
      },
      "normalized": {
        "energy": 0.45,
        "pitch_variation": 0.72,
        "speech_rate": 0.38,
        "pause_weight": 0.15,
        "spectral_brightness": 0.56,
        "voice_texture": 0.34
      },
      "composite_score": 0.62,
      "delivery_label": "moderate energy, varied pitch, measured pace — engaged/conversational"
    }
  ]
}
```

**Rules:**
- `raw` values are absolute measurements from librosa
- `normalized` values are 0-1, normalized per-interview (min-max across all segments in this interview)
- `composite_score` is weighted sum of normalized values using weights from active profile
- `delivery_label` is a human-readable phrase generated from the metrics — this gets passed to the LLM
- `pitch_contour` is a downsampled array (not every frame — ~1 value per 0.5s of audio)
- `pause_before_sec` is time gap between previous segment's end and this segment's start

---

### segments.json — Per-Interview Enriched Manifest

This is the merge of transcript + delivery. It's the primary input for LLM analysis.

```json
{
  "interview_id": "interview_001",
  "source_file": "Elder_Margaret.mov",
  "duration_seconds": 3420.5,
  "segment_count": 87,
  "enriched_at": "2026-02-15T11:20:00",
  "segments": [
    {
      "segment_id": "interview_001_seg_001",
      "start": 2.34,
      "end": 15.67,
      "text": "When I was young, my grandmother would take us to the river every morning before the sun came up.",
      "words": [ ... ],
      "confidence": 0.94,
      "corrected": false,
      "delivery": {
        "energy": 0.45,
        "pitch_variation": 0.72,
        "speech_rate": 0.38,
        "pause_weight": 0.15,
        "composite_score": 0.62,
        "delivery_label": "moderate energy, varied pitch, measured pace — engaged/conversational"
      }
    }
  ]
}
```

**Rules:**
- This is the single-file-per-interview that LLM passes consume
- Contains everything needed to evaluate a segment: text, timing, delivery
- `words[]` array preserved from transcript for export precision
- No raw delivery values — only normalized + composite + label

---

### themes.json — Per-Interview Theme Map

```json
{
  "interview_id": "interview_001",
  "analyzed_at": "2026-02-15T12:00:00",
  "llm_model": "llama3.1:70b-instruct-q4_K_M",
  "themes": [
    {
      "theme_id": "theme_001",
      "name": "Connection to water/river",
      "description": "The river as a place of teaching, memory, and spiritual connection across generations.",
      "segment_ids": ["interview_001_seg_001", "interview_001_seg_005", "interview_001_seg_014"],
      "emotional_character": "reverent, grounding",
      "strength": 0.85,
      "brief_alignment": null
    }
  ],
  "intersections": [
    {
      "segment_id": "interview_001_seg_014",
      "themes": ["theme_001", "theme_003"],
      "note": "Water and loss converge — emotional center of the interview"
    }
  ]
}
```

**Rules:**
- `theme_id` is unique within the interview but NOT globally unique — synthesis creates global IDs
- `strength` is the LLM's assessment of how prominent this theme is (0-1)
- `brief_alignment` maps to a key message ID from brief.json (null if no brief or not applicable)
- `intersections` flag segments where multiple themes converge — these are high-value editorial moments
- `emotional_character` is a brief phrase describing the theme's emotional quality

---

### synthesis.json — Project-Wide Cross-Interview Synthesis

```json
{
  "project_name": "elder-series",
  "synthesized_at": "2026-02-15T12:30:00",
  "llm_model": "llama3.1:70b-instruct-q4_K_M",
  "unified_themes": [
    {
      "unified_theme_id": "utheme_001",
      "name": "Connection to water/river",
      "description": "Three Elders independently reference the river as a site of intergenerational teaching.",
      "source_themes": [
        { "interview_id": "interview_001", "theme_id": "theme_001" },
        { "interview_id": "interview_003", "theme_id": "theme_002" },
        { "interview_id": "interview_005", "theme_id": "theme_004" }
      ],
      "all_segment_ids": [
        "interview_001_seg_001", "interview_001_seg_005",
        "interview_003_seg_012", "interview_003_seg_034",
        "interview_005_seg_008"
      ],
      "perspectives": "Complementary — different aspects of the same relationship to water",
      "brief_alignment": null
    }
  ],
  "best_takes": [
    {
      "topic": "Connection to water/river",
      "candidates": [
        {
          "segment_id": "interview_001_seg_014",
          "interview_id": "interview_001",
          "text": "That was the last time I saw her at the river.",
          "composite_score": 0.91,
          "content_alignment": 0.88,
          "conciseness_score": 0.95,
          "rank": 1,
          "reasoning": "Highest delivery score, strong pause, emotionally weighted"
        },
        {
          "segment_id": "interview_003_seg_034",
          "interview_id": "interview_003",
          "text": "The water carries everything we taught it to carry.",
          "composite_score": 0.84,
          "content_alignment": 0.92,
          "conciseness_score": 0.88,
          "rank": 2,
          "reasoning": "Most direct thematic statement, slightly lower delivery"
        }
      ]
    }
  ]
}
```

**Rules:**
- `unified_theme_id` is globally unique — `utheme_NNN`
- `source_themes` links back to per-interview theme maps
- `all_segment_ids` is the flattened list of every segment across interviews for this theme
- `best_takes` only populated when multiple speakers address the same topic (common in brand projects)
- `best_takes.candidates` sorted by rank, max 3 per topic
- `perspectives` describes how different speakers relate to the theme (complementary, contradictory, expanding)

---

### arc.json — Narrative Arc

```json
{
  "project_name": "elder-series",
  "built_at": "2026-02-15T13:00:00",
  "llm_model": "llama3.1:70b-instruct-q4_K_M",
  "target_duration_seconds": 720,
  "estimated_duration_seconds": 695,
  "narrative_mode": "emergent",
  "arc": [
    {
      "position": 1,
      "segment_id": "interview_001_seg_001",
      "interview_id": "interview_001",
      "role": "opening",
      "themes": ["utheme_001"],
      "editorial_notes": "Establishes the world. Warm, personal. Let the full segment breathe.",
      "pacing": "Don't trim the smile at the end. Natural out-point.",
      "brief_message": null
    },
    {
      "position": 2,
      "segment_id": "interview_001_seg_012",
      "interview_id": "interview_001",
      "role": "deepening",
      "themes": ["utheme_001", "utheme_003"],
      "editorial_notes": "Moves from personal memory to cultural teaching. Speech rate slows significantly here — she's being precise.",
      "pacing": "Hold the transition. The slowdown IS the signal.",
      "brief_message": null
    }
  ]
}
```

**Rules:**
- `position` is the proposed order in the timeline (1-indexed)
- `role` values: `opening`, `deepening`, `turning_point`, `climax`, `resolution`, `coda`, `bridge`
- `themes` references unified theme IDs from synthesis.json
- `editorial_notes` is the LLM's reasoning for selecting this segment
- `pacing` is specific editorial guidance for the editor
- `brief_message` maps to a key message ID (brand/commercial profiles only)
- `estimated_duration_seconds` should be close to `target_duration_seconds`

---

### selections.json — Selected Segments for Export

Derived from arc.json — this is the "flat" version optimized for the review report and export.

```json
{
  "project_name": "elder-series",
  "selection_count": 18,
  "estimated_duration_seconds": 695,
  "flagged_at": "2026-02-17T14:30:00",
  "flags_model": "llama3.1:70b-instruct-q4_K_M",
  "segments": [
    {
      "segment_id": "interview_001_seg_001",
      "interview_id": "interview_001",
      "position": 1,
      "start": 2.34,
      "end": 15.67,
      "text": "When I was young, my grandmother would take us to the river...",
      "role": "opening",
      "themes": ["utheme_001"],
      "composite_score": 0.62,
      "delivery_label": "moderate energy, varied pitch, measured pace",
      "editorial_notes": "Establishes the world. Warm, personal.",
      "pacing": "Don't trim the smile at the end.",
      "status": "pending",
      "flagged": false,
      "flag_reason": null,
      "user_notes": null
    }
  ]
}
```

**Rules:**
- This is the file the review report reads from and approvals.json writes to
- `status`: `pending` | `approved` | `rejected`
- `flagged`: cultural content flag — set by `plotline flags` (LLM Pass 4)
- `flag_reason`: specific reason the segment was flagged (e.g., "References a specific ceremony by name")
- `flagged_at`: ISO timestamp of the last flagging run (top-level, added by flags pass)
- `flags_model`: LLM model used for flagging (top-level, added by flags pass)
- `user_notes`: editor's notes added during review
- Includes `start`/`end` times copied from enriched segments for quick access
- Export reads this file, filters to `status: approved`, and generates EDL/FCPXML
- Re-running `plotline flags` resets all segments to `flagged: false` before re-flagging (clean slate)

---

### approvals.json — User Review Decisions

Written by the review report HTML. Read by the export stage.

```json
{
  "reviewed_at": "2026-02-15T14:00:00",
  "total": 18,
  "approved": 14,
  "rejected": 3,
  "pending": 1,
  "segments": [
    {
      "segment_id": "interview_001_seg_001",
      "position": 1,
      "status": "approved",
      "user_notes": null,
      "flag_acknowledged": false
    },
    {
      "segment_id": "interview_003_seg_022",
      "position": 8,
      "status": "rejected",
      "user_notes": "Too similar to segment at position 5. Redundant.",
      "flag_acknowledged": false
    }
  ],
  "reordered": false,
  "custom_order": null
}
```

**Rules:**
- `custom_order` is an array of segment_ids representing the user's reordered sequence (null if not reordered)
- `flag_acknowledged` must be `true` for flagged segments before they can be approved
- Export uses this to filter and order segments — only `status: approved` segments appear in EDL/FCPXML
- If `reordered: true`, export uses `custom_order` instead of `position` from selections.json

---

### brief.json — Parsed Creative Brief

```json
{
  "source_file": "creative_brief.md",
  "parsed_at": "2026-02-15T10:45:00",
  "key_messages": [
    { "id": "msg_001", "text": "The company is investing in the next generation of workers" },
    { "id": "msg_002", "text": "Innovation comes from diverse perspectives" },
    { "id": "msg_003", "text": "Community roots drive global ambition" }
  ],
  "audience": "Prospective talent, age 22-35, considering relocation to Southern Alberta",
  "target_duration_seconds": 180,
  "tone_direction": "Warm, grounded, authentic — not corporate polish",
  "must_include": ["employee testimonials", "community involvement"],
  "avoid": ["salary figures", "competitor mentions"]
}
```

---

## Module Boundaries

Each pipeline stage is a self-contained module. Modules communicate exclusively through JSON files in the project directory. No module imports another module's internal functions — they read/write to the agreed schemas above.

**This means:**
- Changing the transcription engine doesn't affect delivery analysis (as long as transcript.json schema stays stable)
- Swapping LLM backends doesn't affect export (as long as selections.json schema stays stable)
- Each module can be tested in isolation with fixture JSON files

**The only shared code is:**
- `plotline/config.py` — config access
- `plotline/project.py` — project directory paths
- `plotline/io.py` — JSON read/write helpers
- `plotline/exceptions.py` — exception types
