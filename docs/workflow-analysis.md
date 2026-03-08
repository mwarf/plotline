# Plotline Workflow: Stages, User Interactions, and EDL Opportunities

---

## Stage Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              PIPELINE FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   PREP        │  EXTRACT   │  ANALYZE   │    LLM PASSES    │  REVIEW  │ EXPORT  │
│   ──────      │  ───────   │  ───────   │    ──────────    │  ──────  │ ──────  │
│               │            │            │                   │          │         │
│   init        │  extract   │  analyze   │  themes (Pass 1)  │  review  │  export │
│   add         │  transcribe│  enrich    │  synthesize(Pass2)│  approve │         │
│   brief       │  diarize   │            │  arc (Pass 3)     │          │         │
│   doctor      │            │            │  flags (Pass 4)   │          │         │
│               │            │            │                   │          │         │
│   ════════════╪════════════╪════════════╪═══════════════════╪══════════╪═════════│
│                                                                                  │
│   EDL Impact:  NONE        INDIRECT    DIRECT SELECTION  FINAL      OUTPUT     │
│                           (scoring)    & ORDERING       FILTERING             │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage-by-Stage Analysis

## 1. PREP STAGE (No EDL Impact)

| Command | User Action | Output |
|---------|-------------|--------|
| `plotline init <name>` | Create project, choose profile | `plotline.yaml`, directory structure |
| `plotline add <videos>` | Add video files | `interviews.json` (metadata) |
| `plotline brief <file>` | Attach creative brief | `brief.json` (key messages, target duration) |
| `plotline doctor` | Verify dependencies | Console output only |

**User Interaction**: One-time setup
**EDL Opportunity**: None — no segment data yet

---

## 2. EXTRACT STAGE (No Direct EDL Impact)

| Command | User Action | Output |
|---------|-------------|--------|
| `plotline extract` | Extract audio from videos | `audio_16k.wav`, `audio_full.wav` |
| `plotline transcribe` | Run Whisper | `transcripts/{id}.json` |
| `plotline diarize` | (Optional) Identify speakers | Speaker labels in transcripts |

**User Interaction**: Run commands, wait for completion
**EDL Opportunity**: None — raw text only, no segment selection

**Critical Data Captured**:
- Timecodes (start/end per segment)
- Speaker IDs (if diarized)
- Word-level timestamps
- Frame rate metadata

---

## 2.5. SPEAKER FILTERING (New Feature)

After diarization, you pipeline automatically pauses to let you configure speakers before LLM analysis.

**Auto-Stop Behavior**:
```
plotline run

# Output:
# ✓ Extracted audio
# ✓ Transcribed 3 interviews
# ✓ Diarized 3 interviews (2 speakers detected)
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Diarization complete. Configure speakers before LLM analysis.
#
# Run 'plotline speakers --preview' to identify who is who
# Then run 'plotline run' to continue
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**User Interaction** (REQUIRED if diarization enabled):
1. Preview speakers with heuristics
2. Configure speaker roles (interviewer/subject)
3. Exclude interviewer from EDL
4. Continue pipeline

**Commands**:
```bash
# Preview with AI heuristics
plotline speakers --preview

# Configure speakers
plotline speakers SPEAKER_00 --name "Host" --role interviewer --exclude
plotline speakers SPEAKER_01 --name "Jane Doe" --role subject --include

# Continue pipeline (filtering applied at enrich)
plotline run
```

**Speaker Configuration** (`speakers.yaml`):
```yaml
speakers:
  SPEAKER_00:
    name: "Host"
    color: "#3B82F6"
    role: "interviewer"        # interviewer | subject | unknown
    include_in_edl: false      # Excluded from timeline
  SPEAKER_01:
    name: "Jane Doe"
    color: "#10B981"
    role: "subject"
    include_in_edl: true       # Included in timeline
```

**Filtering Location**: Enrich stage
- Segments from excluded speakers are filtered before LLM analysis
- Filtered segments never enter themes, synthesis, or or arc stages
- Saves LLM tokens and processing time

**EDL Impact**: **HIGH** — Excluded speakers never appear in final timeline

**Preview Heuristics**:
| Signal | Interviewer Heuristic | Subject Heuristic |
|--------|------------------------|-------------------|
| Question ratio | > 30% | < 10% |
| Avg segment duration | < 5 seconds | > 10 seconds |
| Total talk time | < 10 minutes | > 15 minutes |
| Segment count | Many short segments | Fewer long segments |

---

---

## 3. ANALYZE STAGE (Indirect EDL Impact — Scoring)

| Command | User Action | Output |
|---------|-------------|--------|
| `plotline analyze` | Extract delivery features | `delivery/{id}.json` |
| `plotline enrich` | Merge transcript + delivery | `segments/{id}.json` |

**User Interaction**: Run commands, no decisions
**EDL Opportunity**: **Indirect** — delivery scores influence LLM selection

**What Gets Scored** (per segment):

| Metric | Weight (Documentary) | Purpose |
|--------|---------------------|---------|
| Energy (RMS) | 15% | Intensity/volume |
| Pitch variation | 15% | Expressiveness |
| Speech rate | 25% | Pacing indicator |
| Pause patterns | 30% | Editorial markers |
| Spectral brightness | 10% | Voice quality |
| Voice texture | 5% | Timbre |

**Composite Score**: `0.0 - 1.0` — used by LLM to prioritize "good takes"

---

## 4. LLM PASSES (Direct EDL Construction)

### Pass 1: `plotline themes` — Per-Interview Theme Extraction

**User Interaction**: None (automatic)
**EDL Opportunity**: **Indirect** — identifies candidate segments per theme

**Output** (`themes/{id}.json`):
```json
{
  "themes": [
    {
      "theme_id": "theme_001",
      "name": "Connection to water",
      "segment_ids": ["interview_001_seg_001", "interview_001_seg_005"],
      "emotional_character": "reverent and grounding",
      "strength": 0.85
    }
  ]
}
```

**EDL Relevance**: Groups segments by topic for later selection

---

### Pass 2: `plotline synthesize` — Cross-Interview Synthesis

**User Interaction**: None (automatic)
**EDL Opportunity**: **Indirect** — ranks best takes across interviews

**Output** (`data/synthesis.json`):
```json
{
  "unified_themes": [...],
  "best_takes": [
    {
      "topic": "Connection to water",
      "candidates": [
        {"segment_id": "interview_001_seg_014", "rank": 1, "composite_score": 0.91},
        {"segment_id": "interview_003_seg_034", "rank": 2, "composite_score": 0.82}
      ]
    }
  ]
}
```

**EDL Relevance**:
- Identifies best segment per topic across interviews
- Creates candidate pool for arc construction

---

### Pass 3: `plotline arc` — Narrative Arc Construction (PRIMARY)

**User Interaction**:
- Set `target_duration_seconds` in config
- Optionally attach brief with key messages

**EDL Opportunity**: **PRIMARY** — This builds the actual EDL structure

**Output** (`data/selections.json`):
```json
{
  "segments": [
    {
      "position": 1,           // ORDER in timeline
      "segment_id": "...",
      "start": 2.34,           // TIMECODE source
      "end": 15.67,
      "role": "opening",       // Editorial function
      "themes": ["utheme_001"],
      "editorial_notes": "...",
      "pacing": "Hold the transition"
    }
  ],
  "coverage_gaps": [...],
  "alternate_candidates": [...]
}
```

**EDL Relevance**:
- `position` = clip order in timeline
- `start/end` = source timecodes
- `segment_id` = which interview/source file

**LLM Decisions Here**:
1. **Which segments** to include (selection)
2. **Order** of segments (structure)
3. **Role** of each segment (narrative function)
4. **Duration** targeting (fit to target)

---

### Pass 4: `plotline flags` — Cultural Sensitivity (Optional)

**User Interaction**: Enable in config (`cultural_flags: true`)
**EDL Opportunity**: **Indirect** — marks segments for review

**Output**: Updates `selections.json` with:
```json
{
  "segment_id": "...",
  "flagged": true,
  "flag_reason": "References cultural practice that may need community review"
}
```

---

## 5. REVIEW STAGE (EDL Filtering)

| Command | User Action | Output |
|---------|-------------|--------|
| `plotline review` | Open HTML report, approve/reject | `approvals.json` |
| `plotline approve <id>` | CLI approval | `approvals.json` |
| `plotline reject <id>` | CLI rejection | `approvals.json` |

**User Interaction**: **CRITICAL** — Manual curation
**EDL Opportunity**: **FINAL FILTER** — Only approved segments export

**What User Controls**:
- Approve/reject individual segments
- See delivery scores, themes, editorial notes
- Listen to audio previews
- Read cultural flags

---

## 6. EXPORT STAGE (EDL Output)

| Command | User Action | Output |
|---------|-------------|--------|
| `plotline export --format edl` | Generate CMX 3600 | `export/{name}.edl` |
| `plotline export --format fcpxml` | Generate FCPXML | `export/{name}.fcpxml` |

**User Interaction**: Choose format, handle padding
**EDL Opportunity**: **FINAL OUTPUT**

**What Gets Exported**:
```
- Only APPROVED segments
- Ordered by position from selections.json
- With handle padding (default 12 frames)
- Source timecodes converted to record timecodes
```

---

## Summary: Where EDL Decisions Happen

| Stage | EDL Impact | What's Decided |
|-------|------------|----------------|
| Prep | None | Project setup |
| Extract | None | Raw data |
| Analyze | Indirect | Scoring (influences selection) |
| **Themes** | Indirect | Groups candidates |
| **Synthesize** | Indirect | Ranks best takes |
| **Arc** | **PRIMARY** | Selection + Order + Role |
| Flags | Indirect | Marks for review |
| **Review** | **FINAL FILTER** | Approve/Reject |
| **Export** | **OUTPUT** | Generate file |

---

## User Touchpoints

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER DECISION POINTS                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. PROJECT SETUP                                                │
│     └─ Choose profile (documentary/brand/commercial-doc)        │
│     └─ Set target_duration_seconds                              │
│     └─ Attach brief with key_messages                           │
│                                                                  │
│  2. OPTIONAL CONFIG                                              │
│     └─ Enable diarization                                       │
│     └─ Enable cultural_flags                                    │
│     └─ Adjust delivery_weights                                  │
│                                                                  │
│  3. REVIEW (CRITICAL)                          ← MAIN TOUCHPOINT │
│     └─ Approve/reject segments                                  │
│     └─ Read editorial notes                                     │
│     └─ Listen to audio                                          │
│     └─ Check cultural flags                                     │
│                                                                  │
│  4. EXPORT                                                       │
│     └─ Choose format (EDL/FCPXML)                               │
│     └─ Set handle padding                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Opportunities for User to Influence EDL

### Current Implementation

| Opportunity | Where | How |
|-------------|-------|-----|
| **Target duration** | `plotline.yaml` | `target_duration_seconds` |
| **Key messages** | `brief.json` | LLM prioritizes coverage |
| **Delivery weights** | `plotline.yaml` | Adjust what "good delivery" means |
| **Approve/reject** | Review report | Manual filter |
| **Reorder segments** | Not available | Must edit selections.json manually |
| **Swap alternates** | Not available | Must edit selections.json manually |
| **Change segment boundaries** | Not available | Must re-transcribe |

### Missing User Controls (Potential Improvements)

1. **Manual reorder**: `plotline move <segment_id> --position 5`
2. **Swap with alternate**: `plotline swap <segment_id> --with <alternate_id>`
3. **Trim segment**: `plotline trim <segment_id> --start 5.0 --end 12.0`
4. **Split segment**: `plotline split <segment_id> --at 8.5`
5. **Merge segments**: `plotline merge <id1> <id2>`
6. **Force include**: `plotline include <segment_id>` (override LLM selection)
7. **Theme filter**: `plotline arc --theme "Connection to water"` (build arc from subset)

---

## Data Flow Diagram

```
VIDEO FILES
    │
    ▼
┌─────────────┐
│ 1. Extract   │──▶ audio_16k.wav, audio_full.wav
│   (FFmpeg)   │──▶ interviews.json (metadata)
└─────────────┘
    │
    ▼
┌─────────────┐
│ 2. Transcribe│──▶ transcripts/{id}.json
│ (Whisper)    │    (segments with timecodes)
└─────────────┘
    │
    ▼
┌─────────────┐
│ 3. Analyze   │──▶ delivery/{id}.json
│  (librosa)   │    (scores per segment)
└─────────────┘
    │
    ▼
┌─────────────┐
│ 4. Enrich    │──▶ segments/{id}.json
│  (merge)     │    (transcript + delivery)
└─────────────┘
    │
    ▼
┌─────────────┐
│ 5a. Themes   │──▶ themes/{id}.json
│   (LLM)      │    (per-interview themes)
└─────────────┘
    │
    ▼
┌─────────────┐
│ 5b. Synthesis│──▶ synthesis.json
│   (LLM)      │    (cross-interview, best_takes)
└─────────────┘
    │
    ▼
┌─────────────┐
│ 5c. Arc      │──▶ arc.json
│   (LLM)      │──▶ selections.json ◀── EDL STRUCTURE CREATED HERE
└─────────────┘
    │
    ▼
┌─────────────┐
│ 5d. Flags    │──▶ selections.json (updated)
│   (LLM)      │    (flagged fields)
└─────────────┘
    │
    ▼
┌─────────────┐
│ 6. Review    │──▶ approvals.json
│  (HTML/CLI)  │    (user decisions)
└─────────────┘
    │
    ▼
┌─────────────┐
│ 7. Export    │──▶ {name}.edl
│              │──▶ {name}.fcpxml
└─────────────┘
```

---

## Key Files for EDL Construction

| File | Stage | EDL Relevance |
|------|-------|---------------|
| `interviews.json` | Prep | Source file paths, frame rates, timecode offsets |
| `transcripts/{id}.json` | Extract | Segment boundaries, text, speaker IDs |
| `delivery/{id}.json` | Analyze | Composite scores (influences selection) |
| `segments/{id}.json` | Enrich | Unified segment data with scores |
| `themes/{id}.json` | LLM Pass 1 | Theme-to-segment mappings |
| `synthesis.json` | LLM Pass 2 | Best takes, unified themes |
| `selections.json` | LLM Pass 3 | **Selected segments, order, roles** |
| `approvals.json` | Review | User approvals/rejections |
| `export/*.edl` | Export | Final timeline |

---

## Role Types in Narrative Arc

| Role | Purpose | Typical Position |
|------|---------|------------------|
| `opening` | Establish world/character | Early |
| `deepening` | Expand on theme | Middle |
| `turning_point` | Shift in perspective | Middle-late |
| `climax` | Emotional peak | Late |
| `resolution` | Bring together threads | End |
| `coda` | Final thought/image | Very end |
| `bridge` | Connect disparate themes | Any |
