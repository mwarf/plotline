# Plotline: AI-Assisted Documentary Editing

From raw interviews to NLE timeline in 85% less time

---

# The Problem

## Imagine you had a co-editor who...

- Watched every frame and remembered everything
- Transcribed everything instantly (for free)
- Scored every moment for emotional delivery
- Found all the themes across all your interviews
- Proposed a narrative structure

### But **you** had final approval on every single cut

---

# Introducing Plotline

## AI-Assisted Documentary Editing

- **What:** AI-assisted documentary editing toolkit
- **Speed:** 85% less time on tedious work
- **Output:** Frame-accurate EDL/FCPXML for DaVinci, Premiere, FCP
- **Privacy:** Runs entirely local with Ollama

---

# How It Works

## 4-Phase Pipeline

1. **Ingest** — Add your footage
2. **Analyze** — AI transcribes, scores delivery, extracts themes
3. **Review** — You approve, reject, reorder
4. **Export** — Import directly to your NLE

---

# What the AI Measures

## Delivery Metrics

| Metric | What It Measures |
|--------|------------------|
| **Energy** | Volume/intensity (RMS) |
| **Pitch Variation** | Vocal expressiveness |
| **Speech Rate** | Words per minute |
| **Pause Patterns** | Natural breathing room |
| **Voice Quality** | Spectral features |

### Composite Score: 0.0 – 1.0

---

# Cross-Interview Synthesis

## Find the Best Takes

- AI identifies shared topics across all interviews
- Normalizes delivery scores globally
- Ranks candidates for each topic
- Compare takes side-by-side

**See:** `plotline compare --open`

---

# The Human Gatekeeper

## The AI Proposes. You Decide.

- Every segment passes through YOUR review
- **A** — Approve
- **X** — Reject
- **F** — Flag
- Drag to reorder
- Add your notes

---

# Creative Brief Alignment

## Align with Your Vision

### Optional Creative Brief:
- Key messages you want to hit
- Target audience
- Tone and style
- Must-include topics
- Topics to avoid

### AI scores each segment on brief alignment

**See:** `plotline report coverage --open`

---

# Case Study

## 12-Minute Documentary

| Metric | Value |
|--------|-------|
| Raw footage | 4 hours (3 interviews) |
| Final timeline | 12 minutes (34 segments) |

### Time Comparison:

| Approach | Time |
|----------|------|
| Traditional | 2–3 days |
| Plotline | 2 hours (40 min processing + 45 min review) |

---

# Timeline Preview

## What You Get

- Frame-accurate cuts
- Handles for transitions
- Theme keywords as markers
- Ready for color, music, b-roll

### Output Formats:
- EDL (CMX 3600) — DaVinci, Premiere, Avid
- FCPXML — Final Cut Pro

---

# Under the Hood

## Audio Analysis

**Whisper** — Word-level timestamps for frame-accurate cuts

**Librosa** — Acoustic features: energy, pitch, rate, pauses

## LLM Analysis (4 Passes)

1. Per-interview themes
2. Cross-interview synthesis
3. Narrative arc construction
4. Cultural sensitivity flagging (optional)

### LLM Backends:
- Ollama (local)
- Claude (cloud)
- GPT-4 (cloud)

---

# Data Flow Architecture

## Pipeline Stages

```
Video → Audio → Transcript → Delivery → Enriched
                                           ↓
                                    Themes (per-interview)
                                           ↓
                                    Synthesis (cross-interview)
                                           ↓
                                    Narrative Arc
                                           ↓
                                    Selections → EDL/FCPXML
```

### JSON at every stage — inspectable, debuggable, version-controllable

---

# Extensibility

## Built for Flexibility

- Python 3.11+, modular architecture
- Custom profiles (documentary, brand, commercial-doc)
- Pluggable LLM backends
- Adjustable delivery weights
- Multi-language support (auto-detected)

## Open Source

**github.com/mwarf/plotline**

MIT License — Contributions welcome

---

# AI + Human = Better Than Either Alone

## AI Strengths
- Scale — processes hours in minutes
- Consistency — same criteria every time
- Pattern recognition — finds themes you'd miss
- No fatigue — fresh at hour 10

## Human Strengths
- Context — understands the bigger story
- Taste — knows what feels right
- Editorial judgment — makes the call
- Creative vision — sees the final film

### Plotline: AI does the tedious 80%, human does the creative 20%

---

# What's Next

## Available Now
- ✅ Multi-language support (auto-detected)
- ✅ Speaker diarization
- ✅ Smart handles (auto-reduce on tight pauses)
- ✅ Chapter markers in FCPXML
- ✅ Alternates export

## Roadmap
- 🔮 Visual analysis (facial expressions)
- 🔮 Music/sound design suggestions
- 🔮 Real-time collaborative review
- 🔮 B-roll matching
- 🔮 Export to more NLEs

---

# Get Started in 5 Minutes

```bash
# Install (all platforms)
pip install plotline

# macOS Apple Silicon — add mlx-whisper for faster transcription
pip install plotline[macos]

# Create project
plotline init my-doc --profile documentary
cd my-doc

# Add footage
plotline add ~/Videos/interview1.mov

# Run pipeline
plotline run

# Review selections
plotline review --open

# Export timeline
plotline export --format edl
```

### Docs: github.com/mwarf/plotline

---

# Thank You

## Plotline — AI-Assisted Documentary Editing

### The AI proposes. You decide.

---

# Importing This Presentation

## Google Slides

1. Go to slides.google.com
2. File → Import slides
3. Upload this Markdown file
4. Select slides to import

## Keynote

1. Open Keynote
2. Copy text from each section
3. Paste into new slides

## PowerPoint

1. Use pandoc: `pandoc presentation.md -o presentation.pptx`
2. Or copy/paste section by section

---

# Screenshot Checklist

For a complete presentation, add screenshots of:

- [ ] Review interface (plotline review --open)
- [ ] Coverage matrix (plotline report coverage --open)
- [ ] Compare report (plotline compare --open)
- [ ] DaVinci Resolve with imported EDL
- [ ] Theme explorer (plotline report themes --open)
