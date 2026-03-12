# Export Guide

Plotline exports frame-accurate timelines for professional NLEs. This guide covers export formats, handles, NLE import workflows, and troubleshooting.

---

## Export Formats

### EDL (CMX 3600)

The industry-standard Edit Decision List format.

**Best for:** DaVinci Resolve, Adobe Premiere Pro, Avid Media Composer

**Features:**
- Source timecodes with frame accuracy
- Reel names derived from source filenames
- Comments with speaker, role, editorial notes, user notes
- Drop-frame and non-drop-frame timecode support
- Mixed frame rate warning

**Limitations:**
- Single video track
- No markers or keywords
- No chapter points

### FCPXML (Final Cut Pro XML 1.11)

Apple's native interchange format for Final Cut Pro.

**Best for:** Final Cut Pro

**Features:**
- Keywords for themes and speakers
- Chapter markers at narrative role transitions
- Marker notes with editorial guidance
- All metadata preserved
- Smart handles computed per-segment

**Limitations:**
- Final Cut Pro only

---

## Format Comparison

| Feature | EDL | FCPXML |
|---------|-----|--------|
| **DaVinci Resolve** | ✓ | ✗ |
| **Premiere Pro** | ✓ | ✗ |
| **Final Cut Pro** | ✓ | ✓ |
| **Avid Media Composer** | ✓ | ✗ |
| Keywords/Tags | ✗ | ✓ |
| Chapter Markers | ✗ | ✓ |
| Speaker Labels | Comment | Keyword |
| Theme Tags | Comment | Keyword |
| Editorial Notes | Comment | Marker Note |
| User Notes | Comment | Marker Note |
| Smart Handles | ✓ | ✓ |
| Drop-frame timecode | ✓ | ✓ |
| Alternates Export | ✓ | ✗ |

---

## Handles

### What Are Handles?

Handles are extra frames added before and after each clip, giving editors room for transitions and fine-tuning cuts. Without handles, every cut would be razor-tight with no flexibility.

**Example:** A segment from 00:10:00 to 00:20:00 with 12-frame handles at 24fps exports as 00:09:12 to 00:20:12.

### Default Handles

Default is 12 frames (0.5 seconds at 24fps). Adjust with `--handle`:

```bash
# Tight handles for fast-paced content
plotline export --handle 6

# Generous handles for documentary
plotline export --handle 24
```

### Smart Handles

Plotline automatically reduces handles when natural pauses are short. If a segment has only 0.2s of silence before it, the handle is reduced instead of cutting into the next speaker.

**How it works:**
- Pause data is captured during delivery analysis
- Handles are capped at 80% of available pause time
- Segments with generous pauses get full handles
- Segments with tight pauses get proportionally smaller handles

**Result:** No dialogue overlap in tight edits, without any manual adjustment.

---

## Export Options

### `--format`

Choose output format:

```bash
plotline export --format edl      # CMX 3600 EDL
plotline export --format fcpxml   # Final Cut Pro XML
```

### `--handle`

Set handle padding in frames:

```bash
plotline export --handle 12   # Default: 0.5s at 24fps
plotline export --handle 24   # 1s at 24fps
plotline export --handle 0    # No handles (tight cuts)
```

### `--output`

Custom output path:

```bash
plotline export --output ~/Desktop/my_timeline.edl
```

### `--all`

Export all segments, ignoring approval status:

```bash
plotline export --all
```

By default, only approved segments are exported.

### `--alternates`

Export alternate candidates as a secondary timeline:

```bash
plotline export --alternates
```

This generates `{project}_alternates.edl` containing all alternate takes, grouped by their proposed position. Use it to compare and swap takes directly in your NLE.

---

## Importing into NLEs

### DaVinci Resolve

1. Import your source video files into the Media Pool
2. Go to **File → Import Timeline → Import AAF/EDL/XML**
3. Select the `.edl` file
4. In the import dialog:
   - Set "Handle Frames" to 0 (handles already applied)
   - Enable "Link to Media"
5. Click OK

The timeline appears with all clips in the correct order with handles.

### Adobe Premiere Pro

1. Import source files into Project panel
2. Go to **File → Import**
3. Select the `.edl` file
4. Premiere creates a new sequence with clips

**Note:** Premiere may require manual relinking if source paths differ.

### Final Cut Pro

1. Import source files into your Library
2. Go to **File → Import → XML**
3. Select the `.fcpxml` file
4. FCP creates a new event and project

The timeline includes:
- Keywords for themes and speakers
- Chapter markers at role transitions
- Marker notes with editorial guidance

---

## Export Workflow

### Basic Workflow

```bash
# 1. Review and approve segments
plotline review --open

# 2. Export for your NLE
plotline export --format edl        # DaVinci/Premiere
plotline export --format fcpxml     # Final Cut Pro
```

### Compare Takes Workflow

```bash
# 1. Export main timeline
plotline export --format edl

# 2. Export alternates for comparison
plotline export --alternates

# 3. Import both into NLE
# Main timeline on V1, alternates on V2
# Compare and copy/paste between timelines
```

### Re-export After Changes

```bash
# 1. Make changes in review report
plotline review --open

# 2. Re-export (approvals are preserved)
plotline export --format edl
```

---

## Troubleshooting

### "No approved segments to export"

**Cause:** No segments have been approved in the review report.

**Solution:**
```bash
plotline review --open
# Approve segments with A key or Approve button
plotline export --format edl
```

Or export all segments regardless of approval:
```bash
plotline export --format edl --all
```

### Timecodes don't match my NLE

**Cause:** Frame rate mismatch between source and timeline.

**Solution:**
1. Check frame rate in `interviews.json`
2. Ensure your NLE project matches the source frame rate
3. EDL includes a warning comment if mixed frame rates detected

### Media shows as offline

**Cause:** Source files moved or renamed after EDL export.

**Solution:**
1. Keep source files in their original location
2. Or use "Relink Media" in your NLE
3. EDL includes source filename in comments for reference

### Handles are cutting off dialogue

**Cause:** Smart handles may not have enough pause to work with.

**Solution:**
1. Reduce handle size: `plotline export --handle 6`
2. Or disable handles: `plotline export --handle 0`
3. Fine-tune in your NLE

### EDL imports but clips are wrong length

**Cause:** Record timecode miscalculation.

**Solution:**
1. Verify frame rate is correct in your NLE project settings
2. Check if drop-frame vs non-drop-frame mismatch (29.97 DF vs NDF)
3. Re-export with explicit frame rate check

---

## Advanced Topics

### Chapter Markers (FCPXML only)

Chapter markers are automatically placed at narrative role transitions:
- Hook → Body
- Body → Climax  
- Climax → Resolution

Use them to navigate your story structure in Final Cut Pro.

### Metadata in Comments

EDL comments include all available metadata:
```
* COMMENT: [hook] Strong delivery of innovation message | Note: Double-check this fact
```

Format: `[role] editorial_notes | Note: user_notes`

### Multiple Export Formats

Export to both formats for flexibility:
```bash
plotline export --format edl
plotline export --format fcpxml
```

Both files go to `export/` directory.

### Custom Output Location

```bash
plotline export --format edl --output ~/Desktop/client_review.edl
```

---

## Related Documentation

- [Workflow Guide](workflow-guide.md) — End-to-end pipeline
- [Reports Guide](reports-guide.md) — Review report for approvals
- [README](../README.md) — Full CLI reference
