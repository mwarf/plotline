---
title: "Plotline: AI-Assisted Documentary Editing"
author: "Plotline Team"
date: "2026-03-09"
---

# The Problem

## Imagine you had a co-editor who...

- Watched every frame and remembered everything
- Transcribed everything instantly (for free)
- Scored every moment for emotional delivery
- Found all the themes across all your interviews
- Proposed a narrative structure

**But *you* had final approval on every single cut**

---

# Introducing Plotline

**AI-Assisted Documentary Editing**

From raw interviews to NLE timeline in 85% less time

## Key Features

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

## Delivery Metrics (Humans Can't Consistently Quantify)

| Metric | What It Measures | Why It Matters |
|--------|------------------|----------------|
| **Energy** | RMS amplitude — volume/intensity | Engaging speakers vary volume |
| **Pitch Variation** | Vocal expressiveness | Monotone = boring |
| **Speech Rate** | Words per minute | Too fast/slow loses audience |
| **Pauses** | Silence before/after | Natural pacing, breathing room |
| **Voice Quality** | Spectral features | Audio quality, clarity |

**Composite Score: 0.0 – 1.0**

---

# Cross-Interview Synthesis

## Traditional Approach

Watch each interview separately, try to remember who said what best.

## Plotline Approach

AI identifies shared topics across all interviews, normalizes delivery scores globally, and ranks candidates so you can compare takes side-by-side.

**Compare Report:** `plotline compare --open`

---

# The Human Gatekeeper

## The AI Proposes. You Decide.

Every segment passes through YOUR review before the final timeline:

- **A** — Approve
- **X** — Reject
- **F** — Flag
- **Drag** — Reorder
- **Notes** — Add your comments

---

# Creative Brief Alignment

## Align with Your Vision

### Optional Creative Brief

- Key messages you want to hit
- Target audience
- Tone and style
- Must-include topics
- Topics to avoid

### AI scores each segment on brief alignment

**Coverage Matrix:** `plotline report coverage --open`

- **Strong** — Well aligned with message
- **Weak** — Partially aligned
- **Gap** — Missing coverage

---

# Case Study: 12-Minute Documentary

## Input

- **Raw Footage:** 4 hours (3 interviews)
- **Final Timeline:** 12 minutes (34 segments)

## Time Comparison

| Approach | Time |
|----------|------|
| Traditional | 2–3 days |
| Plotline | 2 hours |

### Plotline Breakdown

- **Processing:** 40 minutes (unattended)
- **Review:** 45 minutes
- **Total:** ~2 hours

---

# Timeline Preview

## What You Get

- **Frame-accurate cuts**
- **Handles for transitions**
- **Theme keywords as markers**
- **Ready for color, music, b-roll**

## Output Formats

- **EDL (CMX 3600)** — DaVinci Resolve, Premiere Pro, Avid
- **FCPXML** — Final Cut Pro (with chapter markers)

---

# Under the Hood

## Audio Analysis

- **Whisper** — Word-level timestamps for frame-accurate cuts
- **Librosa** — Acoustic features: energy, pitch, rate, pauses, spectral

## LLM Analysis (4 Passes)

1. Per-interview themes
2. Cross-interview synthesis
3. Narrative arc construction
4. Cultural sensitivity flagging (optional)

## LLM Backends

- **Ollama** — Local (privacy-first)
- **Claude** — Cloud (Anthropic)
- **GPT-4** — Cloud (OpenAI)

---

# Data Flow Architecture

## Pipeline Stages

```
Video → Audio → Transcript → Delivery → Enriched → Themes → Synthesis → Arc → EDL/FCPXML
```

## Data Transformations

| Stage | Input | Output | Tool |
|-------|-------|--------|------|
| Extract | Video | 16kHz WAV | FFmpeg |
| Transcribe | Audio | Segments + timestamps | Whisper |
| Analyze | Audio + segments | Delivery metrics | Librosa |
| Enrich | Transcript + delivery | Unified segments | Merge |
| Themes | Enriched segments | Per-interview themes | LLM |
| Synthesize | All themes | Unified themes | LLM |
| Arc | Synthesis + brief | Narrative + selections | LLM |
| Export | Selections + approvals | EDL/FCPXML | Generator |

**JSON at every stage — inspectable, debuggable, version-controllable**

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

- **Scale** — Processes hours in minutes
- **Consistency** — Same criteria every time
- **Pattern recognition** — Finds themes you'd miss
- **No fatigue** — Fresh at hour 10

## Human Strengths

- **Context** — Understands the bigger story
- **Taste** — Knows what feels right
- **Editorial judgment** — Makes the call
- **Creative vision** — Sees the final film

## Plotline

**AI does the tedious 80%, human does the creative 20%**

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

## Resources

- **GitHub:** github.com/mwarf/plotline
- **Discussions:** github.com/mwarf/plotline/discussions
- **Issues:** github.com/mwarf/plotline/issues

---

# Thank You

## Plotline — AI-Assisted Documentary Editing

**The AI proposes.**

**You decide.**
