# RESOLVE.md — DaVinci Resolve Integration & Timeline Formats

## Overview

Plotline exports timelines in two formats:
- **EDL (CMX 3600)** — P0, universal, text-based, single track
- **FCPXML 1.11** — P1, XML-based, supports markers/keywords/metadata

Both are imported into DaVinci Resolve via **File → Import → Timeline**. The editor then has clips on a timeline at the correct timecodes, ready to trim and refine.

---

## Timecode Math

This is the most error-prone part of the export pipeline. Get this wrong and every clip is in the wrong place.

### Fundamentals

Timecode format: `HH:MM:SS:FF` (hours, minutes, seconds, frames)

```
01:23:45:12
│  │  │  └── Frame 12 (of 24 in a 24fps project)
│  │  └───── Second 45
│  └──────── Minute 23
└─────────── Hour 1
```

Timecode is a **frame count** represented as a clock. At 24fps, `00:00:01:00` = frame 24.

### Frame Rates You'll Encounter

| Source | Frame Rate | Timecode Type | Frames per Second |
|--------|-----------|---------------|-------------------|
| Cinema / ProRes | 23.976 | Non-drop | 24 (actually 23.976) |
| Cinema exact | 24.000 | Non-drop | 24 |
| PAL / European | 25.000 | Non-drop | 25 |
| NTSC / North American | 29.97 | Drop-frame | 30 (actually 29.97) |
| NTSC exact | 30.000 | Non-drop | 30 |

**Most Coalbanks Creative footage will be 23.976fps (ProRes from Blackmagic Cinema Camera 6K) or 29.97fps (from Sony A7III).**

### Non-Drop Frame (NDF)

At 24fps, timecodes count sequentially: every frame gets a number, no frames are skipped.

```
Total frames = (hours * 3600 + minutes * 60 + seconds) * fps + frames
```

Conversion from seconds:
```python
def seconds_to_ndf_timecode(seconds: float, fps: float) -> str:
    """Convert float seconds to non-drop-frame timecode string."""
    total_frames = round(seconds * fps)
    ff = total_frames % round(fps)
    total_seconds = total_frames // round(fps)
    ss = total_seconds % 60
    mm = (total_seconds // 60) % 60
    hh = total_seconds // 3600
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"
```

### Drop-Frame (DF) — 29.97fps Only

29.97fps creates a timing drift: timecode runs slower than real time. Drop-frame compensates by **skipping frame numbers** (not actual frames — no content is lost):

- Skip frames :00 and :01 at every minute mark
- EXCEPT every 10th minute (00, 10, 20, 30, 40, 50)

This keeps timecode synchronized with wall-clock time.

**Drop-frame uses semicolons:** `01:23:45;12` (note `;` before frames)
**Non-drop uses colons:** `01:23:45:12`

```python
def seconds_to_df_timecode(seconds: float) -> str:
    """Convert float seconds to 29.97 drop-frame timecode string."""
    fps = 29.97
    frame_count = round(seconds * fps)
    
    # Drop-frame calculation
    d = frame_count // 17982  # number of complete 10-minute chunks
    m = frame_count % 17982   # remaining frames
    
    if m < 2:
        # First two frames of a 10-minute chunk — no adjustment
        adjustment = 0
    else:
        adjustment = 2 * ((m - 2) // 1798)
    
    adjusted_frames = frame_count + 18 * d + adjustment
    
    ff = adjusted_frames % 30
    ss = (adjusted_frames // 30) % 60
    mm = (adjusted_frames // 1800) % 60
    hh = adjusted_frames // 108000
    
    return f"{hh:02d}:{mm:02d}:{ss:02d};{ff:02d}"
```

**Critical: detect whether the source is drop-frame or non-drop from the source metadata (ffprobe). Using the wrong mode shifts every clip by increasing amounts over the duration of the project.**

### Source Start Timecode

Cameras can embed a start timecode in the file. For example, a camera set to "time of day" timecode might start at `14:32:08:00`.

All Plotline timecodes (from Whisper, from librosa) are relative to the beginning of the audio file — i.e., they start at 0.0 seconds.

When generating EDL/FCPXML, you must **add the source start timecode offset**:

```python
source_start_tc = "01:00:00:00"  # Common camera default
segment_start = 125.4  # seconds from Plotline

# Convert source TC to seconds, add segment start, convert back
source_offset_seconds = timecode_to_seconds(source_start_tc, fps)
absolute_seconds = source_offset_seconds + segment_start
absolute_tc = seconds_to_timecode(absolute_seconds, fps)
```

If no start timecode is embedded (common with screen recordings, phone footage), assume `00:00:00:00`.

### Handle Padding

Plotline adds extra frames before and after each segment to give the editor room to trim. Default: 12 frames (configurable via `handle_padding_frames` in plotline.yaml).

```python
handle_seconds = handle_frames / fps  # e.g., 12 / 23.976 = 0.5005 seconds

padded_start = max(0, segment_start - handle_seconds)
padded_end = min(total_duration, segment_end + handle_seconds)
```

**Don't let handles extend beyond the source file bounds.** Clamp to 0 and total duration.

---

## EDL Format (CMX 3600)

### Structure

An EDL is a plain text file. Each clip is an "event" with a sequential number.

```
TITLE: Plotline Selects - Elder Series
FCM: NON-DROP FRAME

001  interview_001  V  C  01:00:02:08  01:00:15:16  01:00:00:00  01:00:13:08
* FROM CLIP NAME: Elder_Margaret.mov
* COMMENT: [opening] Establishes the world. Warm, personal.

002  interview_001  V  C  01:00:44:12  01:01:18:04  01:00:13:08  01:00:46:24
* FROM CLIP NAME: Elder_Margaret.mov
* COMMENT: [deepening] Moves from personal memory to cultural teaching.

003  interview_003  V  C  01:00:12:00  01:00:34:18  01:00:46:24  01:01:09:18
* FROM CLIP NAME: Elder_Thomas.mov
* COMMENT: [turning_point] Shift in perspective — the river today.
```

### Field Definitions

```
NNN  REEL      TRACK  TRANS  SRC_IN       SRC_OUT      REC_IN       REC_OUT
001  interview V      C      01:00:02:08  01:00:15:16  01:00:00:00  01:00:13:08
```

| Field | Description | Notes |
|-------|-------------|-------|
| `NNN` | Event number | Sequential, 001-999. Zero-padded 3 digits. |
| `REEL` | Source reel/file ID | Max 8 characters in classic EDL. Use interview ID. Map to filename in comments. |
| `TRACK` | Track type | `V` = video (includes audio). Use `V` for Plotline. |
| `TRANS` | Transition | `C` = cut. Always `C` for Plotline (no dissolves). |
| `SRC_IN` | Source in-point | Where the clip starts in the source file (with handle padding). |
| `SRC_OUT` | Source out-point | Where the clip ends in the source file (with handle padding). |
| `REC_IN` | Record in-point | Where the clip starts on the master timeline. |
| `REC_OUT` | Record out-point | Where the clip ends on the master timeline. |

### Record Timecode Calculation

Record timecodes are sequential — each clip starts where the previous one ended:

```python
rec_in = "01:00:00:00"  # Timeline starts at 1 hour (Resolve convention)

for event in events:
    clip_duration = src_out - src_in  # in frames
    rec_out = rec_in + clip_duration
    # Write event
    rec_in = rec_out  # Next clip starts where this one ends
```

### EDL Header

```
TITLE: Plotline Selects - {project_name}
FCM: NON-DROP FRAME
```

or for 29.97fps:

```
TITLE: Plotline Selects - {project_name}
FCM: DROP FRAME
```

**FCM (Frame Code Mode) must match the source timecode type.**

### EDL Comments

Comments start with `*` and appear on lines after the event. Use them for:

```
* FROM CLIP NAME: {original_filename}
* COMMENT: [{role}] {editorial_notes}
```

Resolve reads `FROM CLIP NAME` and uses it to match against media in the Media Pool. **The filename must exactly match the imported media filename.**

### Reel Name Mapping

Classic EDL limits reel names to 8 characters. Plotline should:

1. Use the interview ID as the reel name (e.g., `int_001`)
2. Include a `FROM CLIP NAME` comment with the full filename
3. Optionally, generate a reel-to-filename mapping comment block at the top of the EDL

```
TITLE: Plotline Selects - Elder Series
FCM: NON-DROP FRAME
* REEL MAPPING:
* int_001 = Elder_Margaret.mov
* int_002 = Elder_Robert.mov
* int_003 = Elder_Thomas.mov
```

### Complete EDL Generation Example

```python
def generate_edl(
    project_name: str,
    approved_segments: list[dict],
    interviews: dict,
    fps: float,
    handle_frames: int = 12,
    drop_frame: bool = False,
) -> str:
    """Generate a CMX 3600 EDL from approved selections."""
    
    lines = []
    fcm = "DROP FRAME" if drop_frame else "NON-DROP FRAME"
    lines.append(f"TITLE: Plotline Selects - {project_name}")
    lines.append(f"FCM: {fcm}")
    lines.append("")
    
    # Record timeline starts at 01:00:00:00
    rec_frame_counter = timecode_to_frames("01:00:00:00", fps)
    
    for i, seg in enumerate(approved_segments, 1):
        interview = interviews[seg["interview_id"]]
        reel = seg["interview_id"][:8]
        
        # Source timecodes (with handles)
        handle_sec = handle_frames / fps
        src_start = max(0, seg["start"] - handle_sec)
        src_end = min(interview["duration_seconds"], seg["end"] + handle_sec)
        
        # Add source start TC offset
        offset = timecode_to_seconds(interview.get("start_timecode", "00:00:00:00"), fps)
        src_in = seconds_to_timecode(offset + src_start, fps, drop_frame)
        src_out = seconds_to_timecode(offset + src_end, fps, drop_frame)
        
        # Record timecodes (sequential on master timeline)
        clip_frames = round((src_end - src_start) * fps)
        rec_in = frames_to_timecode(rec_frame_counter, fps, drop_frame)
        rec_out = frames_to_timecode(rec_frame_counter + clip_frames, fps, drop_frame)
        rec_frame_counter += clip_frames
        
        lines.append(f"{i:03d}  {reel:<8s} V     C    {src_in} {src_out} {rec_in} {rec_out}")
        lines.append(f"* FROM CLIP NAME: {interview['filename']}")
        
        role = seg.get("role", "")
        notes = seg.get("editorial_notes", "")
        if role or notes:
            lines.append(f"* COMMENT: [{role}] {notes}")
        lines.append("")
    
    return "\n".join(lines)
```

---

## FCPXML Format (v1.11)

### Structure

FCPXML is XML. It describes a library → event → project → sequence → spine → clips.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.11">
    <resources>
        <format id="r1" name="FFVideoFormat1080p2398" 
                frameDuration="1001/24000s" width="1920" height="1080"/>
        <asset id="a1" name="Elder_Margaret" src="file:///path/to/Elder_Margaret.mov"
               start="0s" duration="3420500/1000s" hasVideo="1" hasAudio="1"
               format="r1" audioSources="1" audioChannels="2"/>
    </resources>
    <library>
        <event name="Plotline Selects">
            <project name="Elder Series">
                <sequence format="r1" tcStart="0s" tcFormat="NDF" duration="695s">
                    <spine>
                        <clip name="Opening - River Memory" 
                              ref="a1" 
                              offset="0s" 
                              start="2340/1000s" 
                              duration="13330/1000s">
                            <keyword start="0s" duration="13330/1000s" value="water, memory"/>
                            <marker start="0s" duration="0s" value="Opening — Warm, personal"/>
                        </clip>
                    </spine>
                </sequence>
            </project>
        </event>
    </library>
</fcpxml>
```

### Time Values in FCPXML

FCPXML uses rational time (fractions), not timecodes:

```
23.976fps:  frameDuration = "1001/24000s"    (1 frame duration)
24fps:      frameDuration = "100/2400s"
25fps:      frameDuration = "100/2500s"
29.97fps:   frameDuration = "1001/30000s"
30fps:      frameDuration = "100/3000s"
```

Durations and offsets are expressed in seconds as fractions or decimals:
```
start="2340/1000s"    → 2.34 seconds
duration="13330/1000s" → 13.33 seconds
```

For frame-accurate values, express as frame counts × frame duration:
```python
def seconds_to_fcpxml_time(seconds: float, fps: float) -> str:
    """Convert seconds to FCPXML rational time."""
    frame_count = round(seconds * fps)
    if fps == 23.976:
        # 1001/24000 per frame
        numerator = frame_count * 1001
        denominator = 24000
    elif fps == 29.97:
        numerator = frame_count * 1001
        denominator = 30000
    elif fps == 24:
        numerator = frame_count * 100
        denominator = 2400
    elif fps == 25:
        numerator = frame_count * 100
        denominator = 2500
    else:
        numerator = frame_count * 100
        denominator = int(fps * 100)
    return f"{numerator}/{denominator}s"
```

### Key Elements

**`<resources>`** — defines formats and assets (source media files)

```xml
<format id="r1" name="FFVideoFormat1080p2398" 
        frameDuration="1001/24000s" width="1920" height="1080"/>

<asset id="a1" name="Elder_Margaret" 
       src="file:///Users/warfeous/Projects/Elder_Series/Elder_Margaret.mov"
       start="0s" duration="3420500/1000s" 
       hasVideo="1" hasAudio="1" format="r1"
       audioSources="1" audioChannels="2"/>
```

**`<clip>`** — a single clip on the timeline

| Attribute | Description |
|-----------|-------------|
| `name` | Clip name shown in timeline (use role + brief description) |
| `ref` | References an asset ID from resources |
| `offset` | Where the clip sits on the timeline (cumulative) |
| `start` | In-point within the source media |
| `duration` | Clip duration |

**`<keyword>`** — searchable tag on a clip (theme tags)

```xml
<keyword start="0s" duration="13330/1000s" value="water, memory, grandmother"/>
```

**`<marker>`** — visible marker on the timeline (editorial notes, delivery labels)

```xml
<marker start="0s" duration="0s" value="Opening — Establishes the world" note="Delivery: warm, measured pace. Don't trim the smile at the end."/>
```

**`<note>`** — clip note (pacing suggestions)

```xml
<note>Hold the pause before this segment. The silence is the transition.</note>
```

### What Plotline Exports as Metadata

| Plotline Data | FCPXML Element | Example |
|---------------|---------------|---------|
| Theme tags | `<keyword>` | `value="water, memory"` |
| Delivery label | `<marker>` | `value="quiet, deliberate, 2.8s pause"` |
| Role label | Clip name prefix | `name="Opening - River Memory"` |
| Editorial notes | `<marker>` note attribute | `note="Establishes the world..."` |
| Pacing suggestions | `<note>` | `Hold the pause before this segment.` |
| Cultural flags | `<marker>` with specific naming | `value="⚠ CULTURAL FLAG: ceremony reference"` |

### Asset Source Paths

FCPXML uses `file://` URLs for source media. The path must be absolute and URL-encoded:

```python
from pathlib import Path
from urllib.parse import quote

def path_to_file_url(path: Path) -> str:
    """Convert a filesystem path to a file:// URL for FCPXML."""
    absolute = path.resolve()
    return f"file://{quote(str(absolute))}"
```

**Critical:** Resolve will look for the media at this exact path. If the media has been moved since Plotline processed it, Resolve will show offline clips. Use the original source paths from interviews.json, not the extracted WAV paths.

### FCPXML tcFormat

```xml
<sequence format="r1" tcStart="0s" tcFormat="NDF" duration="695s">
```

- `tcFormat="NDF"` — non-drop frame (23.976, 24, 25fps)
- `tcFormat="DF"` — drop frame (29.97fps)

### Resolve Import Behavior

When importing FCPXML into Resolve:

1. Resolve creates a new timeline in the current bin
2. It looks for source media in the Media Pool first, then at the file paths in `<asset>`
3. If media isn't found, clips appear as "offline" (red) but retain their position
4. Keywords appear in the clip's keyword field in the Inspector
5. Markers appear on the timeline with their notes
6. Clip names appear in the timeline UI

### Tested Against

Plotline targets **DaVinci Resolve Studio 18.5+** and **DaVinci Resolve (free) 18.5+**.

Both free and Studio versions import EDL and FCPXML. The Studio version additionally supports:
- Python scripting API (P2 feature)
- More timeline tracks
- Advanced color/audio features (not relevant to Plotline)

---

## Resolve Scripting API (P2 — Future)

Not required for V1. Documented here for reference.

The DaVinci Resolve scripting API allows Python to control Resolve directly: create timelines, add clips, set markers, organize bins. This is more powerful than EDL/FCPXML import but requires Resolve Studio to be running.

### Access

```python
import sys
sys.path.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/")
import DaVinciResolveScript as dvr

resolve = dvr.scriptapp("Resolve")
project_manager = resolve.GetProjectManager()
project = project_manager.GetCurrentProject()
media_pool = project.GetMediaPool()
```

### What It Enables (P2)

- **Create bins** organized by interview or theme
- **Add markers** with custom colors per theme
- **Set clip color labels** based on delivery score
- **Create compound clips** for multi-segment sequences
- **Add timeline markers** at transition points with pacing notes

### Why It's P2

EDL/FCPXML import covers 95% of the workflow. The scripting API adds convenience (auto-organization, color coding) but requires:
- Resolve Studio license (not free version)
- Resolve to be running during export
- Platform-specific module path
- More brittle coupling (API changes between Resolve versions)

---

## Testing Export

### EDL Verification Checklist

1. Open EDL in a text editor — verify it's readable, timecodes look plausible
2. Import into Resolve: File → Import → Timeline → EDL
3. Verify clip count matches expected selection count
4. Spot-check 3 clips: scrub to the clip, verify it starts/ends at the expected interview moment
5. Verify first clip starts at the expected point (not offset by handles or timecode drift)
6. Verify last clip ends at approximately the expected total duration
7. Check that `FROM CLIP NAME` matches the media in your Media Pool

### FCPXML Verification Checklist

1. Validate XML: `xmllint --noout plotline_selects.fcpxml`
2. Import into Resolve: File → Import → Timeline → FCPXML
3. All EDL checks above, plus:
4. Verify keywords appear in clip Inspector panel
5. Verify markers appear on timeline with correct notes
6. Verify clip names show role labels

### Common Export Bugs

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| All clips start at 00:00:00:00 | Source start TC not applied | Add source TC offset from interviews.json |
| Clips drift increasingly off-position | Wrong frame rate | Verify fps from ffprobe matches EDL/FCPXML frame rate |
| Clips are ~0.5 seconds early or late | Handle padding math error | Check handle calculation at frame boundaries |
| Resolve shows "offline" clips | Asset paths don't match | Use original source file paths, not extracted WAVs |
| "Invalid EDL" on import | Malformed header or event lines | Check FCM line, column spacing, timecode format |
| Drop-frame timecodes in NDF project | Mixed timecode modes | Detect from source and set FCM/tcFormat accordingly |
| Clips from different interviews overlap | Record TC not advancing | Verify rec_in for event N = rec_out for event N-1 |
