# Arc Command Enhancement Proposal

**Status:** Future exploration  
**Created:** 2026-03-08  
**Related:** `plotline/llm/arc.py`, `prompts/arc.txt`

---

## Current Implementation

### What `plotline arc` Does

1. Reads `synthesis.json` (unified themes, best takes)
2. Reads all segments with delivery scores
3. Sends to LLM with prompt including:
   - Target duration from `plotline.yaml`
   - Profile (documentary/brand/commercial-doc)
   - Creative brief (if attached)
   - All themes and top 100 segments by score
4. LLM returns ordered arc with roles, editorial notes, alternates
5. Creates `selections.json` for review

### Current CLI Options

```bash
plotline arc --force  # Re-run even if already done
```

**That's it.** No other user controls exist.

### Current User Controls (Indirect)

| Control | Where | Effect |
|---------|-------|--------|
| Creative Brief | `plotline brief brief.md` | LLM prioritizes segments matching key messages |
| Target Duration | `plotline.yaml: target_duration_seconds` | Controls how many segments selected |
| Profile | `init --profile` | Changes delivery scoring weights |
| Delivery Weights | `plotline.yaml: delivery_weights` | Fine-tunes "good delivery" criteria |
| Speaker Filtering | `speakers.yaml: include_in_edl: false` | Excludes speakers from selection pool |

---

## Proposed Enhancements

### Phase 1: Documentation

Create `docs/arc-guide.md` explaining:
- How arc construction works
- Current user controls
- Output structure (arc.json, selections.json)
- Role types (opening, deepening, turning_point, climax, resolution, coda, bridge)
- Workflow examples

### Phase 2: CLI Flags

| Flag | Purpose | Example |
|------|---------|---------|
| `--duration` | Override target duration | `--duration 180` (3 min) |
| `--theme` | Filter to specific themes | `--theme "water" --theme "community"` |
| `--min-score` | Minimum delivery score | `--min-score 0.6` |
| `--include` | Force include segments | `--include seg_001 --include seg_042` |
| `--exclude` | Force exclude segments | `--exclude seg_015` |
| `--max-per-speaker` | Speaker balance | `--max-per-speaker 5` |
| `--style` | Narrative structure style | `--style character-driven` |
| `--variations` | Generate multiple arcs | `--variations 3` |

### Phase 3: Config-Based Constraints

Persistent constraints in `plotline.yaml`:

```yaml
arc_constraints:
  must_include:
    - interview_001_seg_042
  never_include:
    - interview_002_seg_015
  max_per_speaker: 5
  required_themes:
    - "Connection to water"
  role_distribution:
    opening: 0.15
    deepening: 0.35
    climax: 0.20
    resolution: 0.30
```

### Phase 4: Arc Templates

Pre-built narrative structures:

```bash
plotline arc --template hero-journey
plotline arc --template problem-solution
plotline arc --template chronological
plotline arc --template three-act
plotline arc --template five-act
```

**Template definitions:**

| Template | Structure | Best For |
|----------|-----------|----------|
| `hero-journey` | Call → Trial → Transformation → Return | Character-driven docs |
| `problem-solution` | Problem → Context → Solution → Impact | Brand videos |
| `chronological` | Time-ordered | Historical docs |
| `three-act` | Setup → Confrontation → Resolution | Standard narrative |
| `five-act` | Exposition → Rising → Climax → Falling → Denouement | Complex narratives |

### Phase 5: Interactive Mode

```bash
plotline arc --interactive
```

Step-by-step guided arc building:
1. Show top themes, let user select focus
2. Show candidate segments for each role
3. User approves/rejects per position
4. Real-time duration tracking
5. Save final arc

### Phase 6: Multiple Arc Variations

```bash
plotline arc --variations 3
```

Generates `arc_1.json`, `arc_2.json`, `arc_3.json` with different approaches:
- Variation 1: Delivery-focused (highest scores)
- Variation 2: Theme-focused (thematic coherence)
- Variation 3: Speaker-balanced (equal representation)

User selects preferred in review report.

---

## Implementation Priority

| Phase | Priority | Effort | Impact | Dependencies |
|-------|----------|--------|--------|--------------|
| 1. Documentation | High | Low | High | None |
| 2. `--duration` flag | High | Low | High | None |
| 3. `--theme` filter | High | Low | High | None |
| 4. `--include`/`--exclude` | High | Medium | High | None |
| 5. Config constraints | Medium | Medium | High | Phase 2, 3, 4 |
| 6. `--min-score` filter | Medium | Low | Medium | None |
| 7. `--max-per-speaker` | Medium | Medium | Medium | None |
| 8. `--style` override | Low | Medium | Medium | Phase 4 |
| 9. `--variations` | Low | Medium | Medium | None |
| 10. Arc templates | Low | Medium | Medium | Phase 4 |
| 11. Interactive mode | Low | High | Medium | All above |

---

## Open Questions

### 1. Persistence of CLI Flags

**Question:** Should `--include`/`--exclude` be saved for future runs?

**Options:**
- A) One-time only (flag affects current run only)
- B) Save to config (persistent until removed)
- C) Both: `--include` is one-time, `--include-save` is persistent

**Recommendation:** Option A for simplicity. Users who want persistence can edit `plotline.yaml`.

### 2. Theme Matching

**Question:** How should `--theme` matching work?

**Options:**
- A) Exact match only (`--theme "Connection to water"`)
- B) Case-insensitive substring (`--theme water`)
- C) Fuzzy matching with similarity threshold

**Recommendation:** Option B. Case-insensitive substring is intuitive and covers most use cases.

### 3. Multiple Variations Storage

**Question:** If `--variations 3`, how should arcs be stored?

**Options:**
- A) `arc_1.json`, `arc_2.json`, `arc_3.json` (user picks, renames to `arc.json`)
- B) All in one `arc.json` with `variations` array
- C) `arc.json` + `arc_alternates.json` (primary + alternatives)

**Recommendation:** Option A. Simple, explicit, easy to compare in review report.

### 4. Template Customization

**Question:** Should users be able to define custom templates?

**Options:**
- A) No, only built-in templates
- B) Yes, via `prompts/arc_hero-journey.txt` files
- C) Yes, via config with role percentages

**Recommendation:** Option B for Phase 4, then Option C for Phase 5.

---

## Implementation Notes

### `--duration` Flag

```python
# In cli.py arc command
@app.command("arc")
def build_arc(
    force: bool = typer.Option(False, "--force", "-f"),
    duration: int | None = typer.Option(None, "--duration", "-d", help="Target duration in seconds"),
):
    config = load_config(project_dir)
    if duration:
        config.target_duration_seconds = duration
    # ... rest of arc construction
```

### `--theme` Filter

```python
# In arc.py build_narrative_arc()
def build_narrative_arc(
    # ... existing args
    theme_filter: list[str] | None = None,
):
    if theme_filter:
        # Filter segments to those with matching themes
        filtered_segments = [
            s for s in all_segments
            if any(
                theme.lower() in " ".join(s.get("themes", [])).lower()
                for theme in theme_filter
            )
        ]
        all_segments = filtered_segments or all_segments
```

### `--include`/`--exclude` Flags

```python
# In arc.py
def create_selections_from_arc(
    arc: dict[str, Any],
    all_segments: list[dict[str, Any]],
    project_name: str,
    force_include: list[str] | None = None,
    force_exclude: set[str] | None = None,
):
    force_exclude = force_exclude or set()
    
    # Add force-included segments not in arc
    if force_include:
        for seg_id in force_include:
            if seg_id not in {s["segment_id"] for s in arc.get("arc", [])}:
                # Add to arc with appropriate role
    
    # Remove excluded segments
    arc["arc"] = [s for s in arc.get("arc", []) if s["segment_id"] not in force_exclude]
```

---

## Success Metrics

| Feature | Success Metric |
|---------|----------------|
| `--duration` | Users can generate 30s, 60s, 3min cuts from same project |
| `--theme` | Users can create theme-focused sub-cuts |
| `--include`/`--exclude` | Users can force editorial decisions before LLM |
| Templates | 3+ templates available, users can create custom |
| Variations | Users can compare multiple approaches in review |

---

## Related Documentation

- `docs/workflow-analysis.md` - Pipeline stages
- `llm/ARCHITECTURE.md` - Data schemas
- `prompts/arc.txt` - Current prompt template
