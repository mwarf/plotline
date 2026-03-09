# Reports Guide

Plotline generates 7 interactive HTML reports for exploring your project. All reports work offline with `file://` protocol — no server required.

---

## Quick Reference

| Report | Purpose | When to Use |
|--------|---------|-------------|
| **Dashboard** | Pipeline status overview | Check processing progress |
| **Review** | Approve/reject segments | Make final editorial decisions |
| **Summary** | Project overview | Share with stakeholders |
| **Transcript** | Per-interview detail | Find specific quotes |
| **Themes** | Theme exploration | Understand story structure |
| **Coverage** | Brief alignment | Verify message delivery |
| **Compare** | Best takes | Choose between candidates |

---

## Opening Reports

```bash
# Dashboard (pipeline status)
plotline report dashboard --open

# Review (approvals)
plotline review --open

# Summary (project overview)
plotline report summary --open

# Transcript (per-interview)
plotline report transcript --open --interview interview_001

# Themes (theme explorer)
plotline report themes --open

# Coverage (brief alignment)
plotline report coverage --open

# Compare (best takes)
plotline compare --open
```

---

## Keyboard Shortcuts

### Review Report

| Key | Action |
|-----|--------|
| `A` | Approve current segment |
| `X` | Reject current segment |
| `F` | Flag for review |
| `Space` | Play/pause audio |
| `↑` `↓` | Navigate between segments |

### Transcript Report

| Key | Action |
|-----|--------|
| `Space` | Play/pause audio |
| `↑` `↓` or `j` `k` | Navigate segments |
| `Esc` | Close audio player |

### Themes Report

| Key | Action |
|-----|--------|
| `Esc` | Close audio player |

---

## Report Navigation

All reports share a common navigation bar:

```
Dashboard | Transcripts | Themes | Compare | Coverage | Summary | Review
```

Click any link to jump between views. The current report is highlighted.

---

## Individual Reports

### Dashboard

**Command:** `plotline report dashboard --open`

Shows pipeline processing status for all interviews.

**What you'll see:**
- Interview cards with duration and speaker count
- Stage completion badges (Extraction, Transcription, Analysis, etc.)
- "Run Next Stage" button with suggested command
- Creative brief summary (if attached)

**When to use:**
- Check if pipeline is complete before review
- Identify which interviews need processing
- See project overview at a glance

---

### Review Report

**Command:** `plotline review --open`

Your primary editorial workspace for approving segments.

**What you'll see:**
- Segment cards with text, speaker, delivery score
- Theme tags on each segment
- Editorial notes from the LLM
- Cultural sensitivity flags (if any)
- Audio player for each segment
- Approve/Reject/Flag buttons

**Features:**
- **Drag to reorder** — Change the sequence of segments
- **Batch actions** — Select multiple segments and approve/reject all
- **Search** — Filter by text, theme, or delivery score
- **Audio playback** — Preview before deciding
- **Notes** — Add your own editorial notes

**When to use:**
- Final editorial decisions before export
- Listen to segments before approving
- Reorder the proposed timeline
- Flag segments for later review

**Workflow:**
1. Read the LLM's editorial notes
2. Listen to the audio (Space to play)
3. Approve (A) or Reject (X)
4. Add your own notes if needed
5. Reorder segments by dragging
6. Click "Export" when done to download the EDL

---

### Summary Report

**Command:** `plotline report summary --open`

Executive overview of the entire project.

**What you'll see:**
- Interview contributions (duration, segment count)
- Theme map with segment counts
- Narrative arc overview
- Delivery highlights (highest-scoring segments)
- Project statistics

**When to use:**
- Share project status with stakeholders
- Get a bird's-eye view of content
- Identify which interviews contribute most
- See theme distribution

---

### Transcript Report

**Command:** `plotline report transcript --open --interview interview_001`

Detailed per-interview view with delivery timeline.

**What you'll see:**
- Waveform visualization of delivery scores
- Segment cards with text and metrics
- Theme pills on segments
- Energy/pacing timeline (sticky header)
- Audio player synced to segments

**Features:**
- **Delivery timeline** — Visual representation of energy and pacing
- **Theme pills** — See which themes each segment belongs to
- **Filter by score** — Show only high/medium/low delivery segments
- **Deep links** — Jump to specific segments via URL hash

**When to use:**
- Find specific quotes in an interview
- Analyze delivery patterns over time
- Identify high-energy moments
- Explore a single interview in depth

---

### Themes Report

**Command:** `plotline report themes --open`

Interactive explorer for reviewing content by theme.

**What you'll see:**
- Sidebar with all unified themes
- Segment count and strength indicator per theme
- Main panel with themed segments
- Theme description and emotional character
- Audio player per segment

**Features:**
- **Filter by theme** — Click a theme to see all related segments
- **Multi-theme badges** — Segments tagged with 2+ themes are highlighted
- **Sort options** — By delivery score, time, or interview
- **Group by interview** — See which interviews cover each theme
- **Search** — Filter segments by text

**When to use:**
- Understand thematic structure of your content
- Find all segments about a specific topic
- See theme intersections
- Identify gaps in theme coverage

---

### Coverage Report

**Command:** `plotline report coverage --open`

Matrix showing how well your selections cover the creative brief.

**What you'll see:**
- Key messages from your brief
- Theme alignment grid (strong/weak/gap)
- Per-message segment cards
- Progress bar for message coverage
- Coverage gaps highlighted

**Features:**
- **Coverage tiers** — Strong (green), Weak (yellow), Gap (red)
- **Click to drill down** — See segments for each message
- **Gap identification** — Messages with no coverage

**When to use:**
- Verify all key messages are addressed
- Identify gaps before finalizing
- Focus on weak coverage areas
- Share with stakeholders for approval

**Requires:** A creative brief to be attached (`plotline brief brief.md`)

---

### Compare Report

**Command:** `plotline compare --open`

Side-by-side comparison of best takes across interviews.

**What you'll see:**
- Candidate segments for the same topic
- Ranked by delivery score
- Audio player per candidate
- Score comparison (delivery, content alignment, conciseness)
- Interview source for each

**Features:**
- **Sort by score** — See best takes first
- **Filter by theme** — Compare within a specific topic
- **Audio comparison** — Listen to all candidates
- **Cross-interview normalization** — Scores adjusted for interview-level differences

**When to use:**
- Choose between multiple takes on the same topic
- Find the strongest version of a quote
- Compare delivery across speakers
- Select best content for key messages

---

## Tips & Workflows

### Daily Review Workflow

1. **Morning:** Open Dashboard to check status
   ```bash
   plotline report dashboard --open
   ```

2. **During review:** Use Review report with keyboard shortcuts
   ```bash
   plotline review --open
   # Use A/X/F keys, Space to play audio
   ```

3. **End of day:** Check Coverage to verify progress
   ```bash
   plotline report coverage --open
   ```

### Story Exploration Workflow

1. **Start with Themes** to understand structure
   ```bash
   plotline report themes --open
   ```

2. **Drill into Transcript** for detailed analysis
   ```bash
   plotline report transcript --open --interview interview_001
   ```

3. **Use Compare** to choose best takes
   ```bash
   plotline compare --open
   ```

4. **Finalize in Review**
   ```bash
   plotline review --open
   ```

### Stakeholder Presentation

1. **Open Summary** for high-level overview
   ```bash
   plotline report summary --open
   ```

2. **Show Themes** to demonstrate story structure
   ```bash
   plotline report themes --open
   ```

3. **Use Coverage** to show message alignment
   ```bash
   plotline report coverage --open
   ```

### Finding Specific Content

1. **Use Transcript search** for exact quotes
2. **Use Themes filter** for topical content
3. **Use Compare** for best versions of repeated content

---

## Troubleshooting

### "No segments to display"

**Cause:** Pipeline hasn't reached the arc stage yet.

**Solution:** Run `plotline run` to complete the pipeline.

### Audio not playing

**Cause:** Browser security blocking file:// audio.

**Solution:**
- Chrome: No fix needed (works by default)
- Safari: Disable "Local File Restrictions" in Develop menu
- Firefox: Use a local server: `python -m http.server 8000`

### Search not finding segments

**Cause:** Search is case-sensitive in some browsers.

**Solution:** Try lowercase search terms, or partial words.

### Coverage report shows "No brief attached"

**Cause:** No creative brief has been attached.

**Solution:**
```bash
plotline brief brief.md
plotline report coverage --open
```

---

## Related Documentation

- [Workflow Guide](workflow-guide.md) — End-to-end pipeline
- [Export Guide](export-guide.md) — Exporting after review
- [Creative Briefs](creative-brief.md) — Guide LLM analysis
